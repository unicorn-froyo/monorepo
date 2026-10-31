package main

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"regexp"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgconn"
	widgets "github.com/unicorn-froyo/monorepo/src/data/example/widgets/go"
	"github.com/unicorn-froyo/monorepo/src/data/go/postgresql"
	"gorm.io/gorm"
)

const ownerID = "00000000-0000-0000-0000-000000000001"
const widgetID = "00000000-0000-0000-0000-000000000002"
const outboxID = "00000000-0000-0000-0000-000000000003"

func database(t *testing.T) *gorm.DB {
	t.Helper()
	db, err := postgresql.Open("")
	if err != nil {
		t.Fatal(err)
	}
	pool, err := db.DB()
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { pool.Close() })
	for _, table := range []string{"widgets.outbox", "widgets.widgets", "widgets.owners"} {
		if err := db.Exec("DELETE FROM " + table).Error; err != nil {
			t.Fatal(err)
		}
	}
	return db
}

func exampleWidget() widgets.Widget {
	return widgets.Widget{
		ID: widgetID, OwnerID: ownerID, Name: "雪☃", Version: 1<<60 + 1,
		Amount: "1234567890123456789012.12345678", Payload: []byte{0, 255}, Metadata: json.RawMessage(`{"unicode":"雪","present":false}`),
		CreatedAt: time.Date(2026, 10, 30, 12, 0, 0, 123456000, time.UTC),
	}
}

func insertExample(tx *gorm.DB) error {
	if err := tx.Create(&widgets.Owner{ID: ownerID, Name: "account"}).Error; err != nil {
		return err
	}
	widget := exampleWidget()
	if err := tx.Omit("Owner").Create(&widget).Error; err != nil {
		return err
	}
	return tx.Create(&widgets.Outbox{ID: outboxID, WidgetID: widgetID, EventType: "created"}).Error
}

func TestNativeTransactionsAndExactTypes(t *testing.T) {
	db := database(t)
	if err := db.Transaction(insertExample); err != nil {
		t.Fatal(err)
	}
	var stored widgets.Widget
	if err := db.Preload("Owner").First(&stored, "id = ?", widgetID).Error; err != nil {
		t.Fatal(err)
	}
	expected := exampleWidget()
	var metadata map[string]any
	if err := json.Unmarshal(stored.Metadata, &metadata); err != nil {
		t.Fatal(err)
	}
	if stored.Version != expected.Version || stored.Amount != expected.Amount || !reflect.DeepEqual(stored.Payload, expected.Payload) || !stored.CreatedAt.Equal(expected.CreatedAt) || stored.OptionalText != nil || metadata["unicode"] != "雪" || stored.Owner.Name != "account" {
		t.Fatalf("values changed: %+v", stored)
	}
	if metadata["present"] != false {
		t.Fatal("JSON boolean changed")
	}
	for _, model := range []any{&widgets.Owner{}, &widgets.Widget{}, &widgets.Outbox{}} {
		var count int64
		if err := db.Model(model).Count(&count).Error; err != nil || count != 1 {
			t.Fatalf("transaction did not commit: %d, %v", count, err)
		}
	}
	var owner widgets.Owner
	if err := db.Preload("Widgets").First(&owner, "id = ?", ownerID).Error; err != nil || len(owner.Widgets) != 1 {
		t.Fatalf("relationship: %+v, %v", owner, err)
	}
	conflict := db.Model(&widgets.Widget{}).Where("id = ? AND revision = ?", widgetID, expected.Version).Update("revision", expected.Version+1)
	if conflict.Error != nil || conflict.RowsAffected != 1 {
		t.Fatal("first conditional write failed", conflict.Error)
	}
	conflict = db.Model(&widgets.Widget{}).Where("id = ? AND revision = ?", widgetID, expected.Version).Update("revision", expected.Version+1)
	if conflict.Error != nil || conflict.RowsAffected != 0 {
		t.Fatal("stale version write succeeded", conflict.Error)
	}
	if err := db.Exec("DELETE FROM widgets.outbox; DELETE FROM widgets.widgets; DELETE FROM widgets.owners").Error; err != nil {
		t.Fatal(err)
	}
	rollback := errors.New("rollback")
	if err := db.Transaction(func(tx *gorm.DB) error {
		if err := insertExample(tx); err != nil {
			return err
		}
		return rollback
	}); !errors.Is(err, rollback) {
		t.Fatal(err)
	}
	for _, model := range []any{&widgets.Owner{}, &widgets.Widget{}, &widgets.Outbox{}} {
		var count int64
		if err := db.Model(model).Count(&count).Error; err != nil || count != 0 {
			t.Fatalf("partial transaction: %d, %v", count, err)
		}
	}
}

func TestDatabaseHTTPAndReadiness(t *testing.T) {
	db := database(t)
	handler := newHandler(widgets.NewStore(db))
	request := func(path string) *httptest.ResponseRecorder {
		t.Helper()
		response := httptest.NewRecorder()
		handler.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "https://example.com"+path, nil))
		return response
	}
	if got := request("/database/widgets"); got.Code != 200 || got.Body.String() != "[]" {
		t.Fatalf("empty result: %s", got.Body.String())
	}
	if err := db.Transaction(insertExample); err != nil {
		t.Fatal(err)
	}
	response := request("/database/widgets")
	var result []map[string]string
	if err := json.Unmarshal(response.Body.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if response.Code != 200 || len(result) != 1 || result[0]["id"] != widgetID || result[0]["owner"] != "account" {
		t.Fatalf("query response: %+v", result)
	}
	if response.Header().Get("Strict-Transport-Security") != "max-age=31536000" {
		t.Fatal("shared middleware missing")
	}
	if got := request("/readyz"); got.Code != 200 {
		t.Fatal("database not ready")
	}
	if got := request("/widgets"); got.Code != 202 || got.Body.String() != "[]" {
		t.Fatal("base endpoint changed")
	}
	pool, err := db.DB()
	if err != nil {
		t.Fatal(err)
	}
	if err := pool.Close(); err != nil {
		t.Fatal(err)
	}
	if got := request("/database/widgets"); got.Code != 500 {
		t.Fatal("query failure hidden")
	}
	if got := request("/readyz"); got.Code != 503 {
		t.Fatal("readiness failure hidden")
	}
	empty := newHandler(nil)
	for path, want := range map[string]int{"/readyz": 200, "/database/widgets": 503} {
		recorder := httptest.NewRecorder()
		empty.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, path, nil))
		if recorder.Code != want {
			t.Fatalf("%s: %d", path, recorder.Code)
		}
	}
}

func TestApplicationPermissionsAndConstraints(t *testing.T) {
	db := database(t)
	for _, command := range []string{"CREATE TABLE widgets.forbidden (id int)", "SELECT * FROM widgets.flyway_schema_history"} {
		var failure *pgconn.PgError
		if err := db.Exec(command).Error; !errors.As(err, &failure) || failure.Code != "42501" {
			t.Fatalf("DDL/history access allowed: %v", err)
		}
	}
	checks := []struct {
		sql   string
		state string
	}{
		{"INSERT INTO widgets.owners (id, display_name) VALUES ('" + ownerID + "', NULL)", "23502"},
		{"INSERT INTO widgets.outbox (id,widget_id,event_type) VALUES ('" + outboxID + "','" + widgetID + "','created')", "23503"},
	}
	for _, check := range checks {
		var failure *pgconn.PgError
		if err := db.Exec(check.sql).Error; !errors.As(err, &failure) || failure.Code != check.state {
			t.Fatalf("constraint: %v", err)
		}
	}
	if err := db.Create(&widgets.Owner{ID: ownerID, Name: "account"}).Error; err != nil {
		t.Fatal(err)
	}
	var failure *pgconn.PgError
	if err := db.Create(&widgets.Owner{ID: widgetID, Name: "account"}).Error; !errors.As(err, &failure) || failure.Code != "23505" {
		t.Fatalf("unique constraint: %v", err)
	}
	widget := exampleWidget()
	widget.Version = 0
	if err := db.Omit("Owner").Create(&widget).Error; !errors.As(err, &failure) || failure.Code != "23514" {
		t.Fatalf("version constraint: %v", err)
	}
}

func TestDatabaseMainUsesExistingServer(t *testing.T) {
	db := database(t)
	previousOpen, previousListen, previousFatal := openDatabase, listenAndServe, logFatal
	t.Cleanup(func() { openDatabase, listenAndServe, logFatal = previousOpen, previousListen, previousFatal })
	t.Setenv("POSTGRES_CONNECTION_FILE", "injected.json")
	want := errors.New("server stopped")
	logFatal = func(values ...any) {
		if len(values) != 1 || values[0] != want {
			t.Fatalf("unexpected failure: %v", values)
		}
	}
	openDatabase = func(path string) (*gorm.DB, error) {
		if path != "injected.json" {
			t.Fatal(path)
		}
		return db, nil
	}
	listenAndServe = func(server *http.Server) error {
		response := httptest.NewRecorder()
		server.Handler.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/readyz", nil))
		if response.Code != 200 {
			t.Fatal("database was not injected")
		}
		return want
	}
	main()
	openDatabase = func(string) (*gorm.DB, error) { return nil, want }
	main()
	openDatabase = func(string) (*gorm.DB, error) { return &gorm.DB{Config: &gorm.Config{}}, nil }
	logFatal = func(values ...any) {
		if len(values) != 1 || values[0] == nil {
			t.Fatalf("invalid pool not rejected: %v", values)
		}
	}
	main()
}

func TestPythonAppReadsGoORMRecords(t *testing.T) {
	db := database(t)
	if err := db.Transaction(insertExample); err != nil {
		t.Fatal(err)
	}
	server := filepath.Join(os.Getenv("TEST_SRCDIR"), os.Getenv("TEST_WORKSPACE"), "src/apis/examples/python/server")
	logPath := filepath.Join(t.TempDir(), "python-service.log")
	output, err := os.Create(logPath)
	if err != nil {
		t.Fatal(err)
	}
	defer output.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, server, "--port=0")
	command.Stdout, command.Stderr = output, output
	if err := command.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { cancel(); command.Wait() }()
	address := regexp.MustCompile(`http://0\.0\.0\.0:(\d+)`)
	client := http.Client{Timeout: time.Second}
	for ctx.Err() == nil {
		contents, err := os.ReadFile(logPath)
		if err != nil {
			t.Fatal(err)
		}
		match := address.FindSubmatch(contents)
		if len(match) > 1 {
			response, err := client.Get("http://127.0.0.1:" + string(match[1]) + "/database/widgets")
			if err == nil {
				var rows []map[string]string
				decodeError := json.NewDecoder(response.Body).Decode(&rows)
				response.Body.Close()
				if response.StatusCode != 200 || decodeError != nil || len(rows) != 1 || rows[0]["id"] != widgetID || rows[0]["owner"] != "account" {
					t.Fatalf("Python could not read Go ORM data: status=%d rows=%v error=%v", response.StatusCode, rows, decodeError)
				}
				return
			}
		}
		time.Sleep(50 * time.Millisecond)
	}
	contents, _ := os.ReadFile(logPath)
	t.Fatalf("Python service did not become ready: %s", contents)
}

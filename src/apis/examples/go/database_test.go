package main

import (
	"context"
	"encoding/json"
	"errors"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	widgets "github.com/unicorn-froyo/monorepo/src/data/example/widgets/go"
	"github.com/unicorn-froyo/monorepo/src/data/go/postgresql"
	"gorm.io/gorm"
)

const ownerID = "00000000-0000-0000-0000-000000000001"
const widgetID = "00000000-0000-0000-0000-000000000002"

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

// databaseWithWidgets seeds committed records before constructing an HTTP server.
func databaseWithWidgets(t *testing.T) *gorm.DB {
	t.Helper()
	db := database(t)
	if err := db.Transaction(func(tx *gorm.DB) error {
		if err := tx.Create(&widgets.Owner{ID: ownerID, Name: "account"}).Error; err != nil {
			return err
		}
		widget := widgets.Widget{
			ID: widgetID, OwnerID: ownerID, Name: "雪☃", Version: 1,
			Amount: "12.34000000", Payload: []byte{1}, Metadata: json.RawMessage(`{}`),
			CreatedAt: time.Date(2026, 10, 30, 12, 0, 0, 0, time.UTC),
		}
		return tx.Omit("Owner").Create(&widget).Error
	}); err != nil {
		t.Fatal(err)
	}
	return db
}

func TestDatabaseHTTPAndReadiness(t *testing.T) {
	db := databaseWithWidgets(t)
	handler := newHandler(widgets.NewStore(db))
	request := func(path string) *httptest.ResponseRecorder {
		t.Helper()
		response := httptest.NewRecorder()
		handler.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "https://example.com"+path, nil))
		return response
	}
	response := request("/widgets")
	var result []map[string]string
	if err := json.Unmarshal(response.Body.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	if response.Code != 200 || len(result) != 1 || result[0]["id"] != widgetID || result[0]["owner"] != "account" || result[0]["name"] != "雪☃" {
		t.Fatalf("query response: %+v", result)
	}
	if response.Header().Get("Strict-Transport-Security") != "max-age=31536000" {
		t.Fatal("shared middleware missing")
	}
	if got := request("/readyz"); got.Code != 200 {
		t.Fatal("database not ready")
	}
	if got := request("/database/widgets"); got.Code != http.StatusNotFound {
		t.Fatal("removed database-specific route is still registered")
	}
	pool, err := db.DB()
	if err != nil {
		t.Fatal(err)
	}
	if err := pool.Close(); err != nil {
		t.Fatal(err)
	}
	if got := request("/widgets"); got.Code != 500 {
		t.Fatal("query failure hidden")
	}
	if got := request("/readyz"); got.Code != 503 {
		t.Fatal("readiness failure hidden")
	}
	empty := newHandler(nil)
	for path, want := range map[string]int{"/readyz": 200, "/widgets": 503} {
		recorder := httptest.NewRecorder()
		empty.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, path, nil))
		if recorder.Code != want {
			t.Fatalf("%s: %d", path, recorder.Code)
		}
	}
}

func TestRunClosesDatabaseOnServerFailure(t *testing.T) {
	db := database(t)
	applicationName := "cleanup-" + t.Name()
	t.Setenv("PGAPPNAME", applicationName)
	count := func() int64 {
		t.Helper()
		var total int64
		if err := db.Raw("SELECT count(*) FROM pg_stat_activity WHERE application_name = ? AND datname = current_database()", applicationName).Scan(&total).Error; err != nil {
			t.Fatal(err)
		}
		return total
	}
	assertClosed := func() {
		t.Helper()
		deadline := time.Now().Add(2 * time.Second)
		for {
			remaining := count()
			if remaining == 0 {
				return
			}
			if time.Now().After(deadline) {
				t.Fatalf("run leaked %d database connections", remaining)
			}
			time.Sleep(10 * time.Millisecond)
		}
	}
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	if err := run(context.Background(), listener.Addr().String()); err == nil {
		t.Fatal("occupied HTTP address was accepted")
	}
	assertClosed()
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := run(ctx, "127.0.0.1:0"); err != nil {
		t.Fatal(err)
	}
	assertClosed()
	t.Setenv("POSTGRES_CONNECTION_FILE", filepath.Join(t.TempDir(), "missing.json"))
	if err := run(context.Background(), "127.0.0.1:0"); err == nil {
		t.Fatal("missing connection file not rejected")
	}
}

func TestGoServerProcessConnectsToPostgres(t *testing.T) {
	db := databaseWithWidgets(t)
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	address := listener.Addr().String()
	_, port, err := net.SplitHostPort(address)
	if err != nil {
		t.Fatal(err)
	}
	listener.Close()
	server := filepath.Join(os.Getenv("TEST_SRCDIR"), os.Getenv("TEST_WORKSPACE"), os.Getenv("GO_SERVER_PATH"))
	logPath := filepath.Join(os.Getenv("TEST_UNDECLARED_OUTPUTS_DIR"), "go-service.log")
	output, err := os.Create(logPath)
	if err != nil {
		t.Fatal(err)
	}
	defer output.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, server, "--port="+port)
	command.Stdout, command.Stderr = output, output
	if err := command.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() {
		command.Process.Signal(os.Interrupt)
		if err := command.Wait(); err != nil {
			t.Errorf("Go server did not exit cleanly: %v", err)
		}
		cancel()
	}()
	client := http.Client{Timeout: time.Second}
	for {
		response, err := client.Get("http://" + address + "/readyz")
		if err == nil {
			response.Body.Close()
			if response.StatusCode == http.StatusOK {
				break
			}
		}
		if ctx.Err() != nil {
			contents, _ := os.ReadFile(logPath)
			t.Fatalf("Go server did not become ready: %s", contents)
		}
		time.Sleep(50 * time.Millisecond)
	}
	// Change the shared database after startup to verify the server makes live queries.
	if err := db.Model(&widgets.Widget{}).Where("id = ?", widgetID).Update("display_name", "updated 雪").Error; err != nil {
		t.Fatal(err)
	}
	response, err := client.Get("http://" + address + "/widgets")
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	var rows []map[string]string
	if err := json.NewDecoder(response.Body).Decode(&rows); err != nil {
		t.Fatal(err)
	}
	if response.StatusCode != http.StatusOK || len(rows) != 1 || rows[0]["id"] != widgetID || rows[0]["name"] != "updated 雪" || rows[0]["owner"] != "account" {
		t.Fatalf("Go server did not read live PostgreSQL data: status=%d rows=%v", response.StatusCode, rows)
	}
}

func TestGoServerProcessRejectsMissingConnectionFile(t *testing.T) {
	t.Setenv("POSTGRES_CONNECTION_FILE", filepath.Join(t.TempDir(), "missing.json"))
	server := filepath.Join(os.Getenv("TEST_SRCDIR"), os.Getenv("TEST_WORKSPACE"), os.Getenv("GO_SERVER_PATH"))
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	output, err := exec.CommandContext(ctx, server, "--port=0").CombinedOutput()
	var failure *exec.ExitError
	if !errors.As(err, &failure) || failure.ExitCode() != 1 || !strings.Contains(string(output), "read PostgreSQL connection") {
		t.Fatalf("invalid database configuration did not fail startup: error=%v output=%s", err, output)
	}
}

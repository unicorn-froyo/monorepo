package widgets

import (
	"encoding/json"
	"errors"
	"reflect"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgconn"
	"github.com/unicorn-froyo/monorepo/src/data/go/postgresql"
	"gorm.io/gorm"
	"gorm.io/gorm/schema"
)

func TestMappingsUseFlywayTablesAndRelationships(t *testing.T) {
	for _, model := range []any{Owner{}, Widget{}, Outbox{}} {
		parsed, err := schema.Parse(model, &sync.Map{}, schema.NamingStrategy{})
		if err != nil {
			t.Fatal(err)
		}
		if parsed.Table != "widgets.owners" && parsed.Table != "widgets.widgets" && parsed.Table != "widgets.outbox" {
			t.Fatalf("wrong schema: %s", parsed.Table)
		}
		if parsed.PrimaryFields[0].DBName != "id" {
			t.Fatal("missing primary key mapping")
		}
	}
	parsed, err := schema.Parse(Widget{}, &sync.Map{}, schema.NamingStrategy{})
	if err != nil {
		t.Fatal(err)
	}
	if parsed.LookUpField("Version").DBName != "revision" || parsed.Relationships.Relations["Owner"] == nil {
		t.Fatal("incorrect column or relationship mapping")
	}
}

const ownerID = "00000000-0000-0000-0000-000000000001"
const widgetID = "00000000-0000-0000-0000-000000000002"
const outboxID = "00000000-0000-0000-0000-000000000003"

func testDatabase(t *testing.T) *gorm.DB {
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

func exampleWidget() Widget {
	return Widget{
		ID: widgetID, OwnerID: ownerID, Name: "雪☃", Version: 1<<60 + 1,
		Amount: "1234567890123456789012.12345678", Payload: []byte{0, 255}, Metadata: json.RawMessage(`{"unicode":"雪","present":false}`),
		CreatedAt: time.Date(2026, 10, 30, 12, 0, 0, 123456000, time.UTC),
	}
}

func insertExample(tx *gorm.DB) error {
	if err := tx.Create(&Owner{ID: ownerID, Name: "account"}).Error; err != nil {
		return err
	}
	widget := exampleWidget()
	if err := tx.Omit("Owner").Create(&widget).Error; err != nil {
		return err
	}
	return tx.Create(&Outbox{ID: outboxID, WidgetID: widgetID, EventType: "created"}).Error
}

func TestNativeTransactionsAndExactTypes(t *testing.T) {
	db := testDatabase(t)
	if err := db.Transaction(insertExample); err != nil {
		t.Fatal(err)
	}
	var stored Widget
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
	for _, model := range []any{&Owner{}, &Widget{}, &Outbox{}} {
		var count int64
		if err := db.Model(model).Count(&count).Error; err != nil || count != 1 {
			t.Fatalf("transaction did not commit: %d, %v", count, err)
		}
	}
	var owner Owner
	if err := db.Preload("Widgets").First(&owner, "id = ?", ownerID).Error; err != nil || len(owner.Widgets) != 1 {
		t.Fatalf("relationship: %+v, %v", owner, err)
	}
	conflict := db.Model(&Widget{}).Where("id = ? AND revision = ?", widgetID, expected.Version).Update("revision", expected.Version+1)
	if conflict.Error != nil || conflict.RowsAffected != 1 {
		t.Fatal("first conditional write failed", conflict.Error)
	}
	conflict = db.Model(&Widget{}).Where("id = ? AND revision = ?", widgetID, expected.Version).Update("revision", expected.Version+1)
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
	for _, model := range []any{&Owner{}, &Widget{}, &Outbox{}} {
		var count int64
		if err := db.Model(model).Count(&count).Error; err != nil || count != 0 {
			t.Fatalf("partial transaction: %d, %v", count, err)
		}
	}
}

func TestApplicationPermissionsAndConstraints(t *testing.T) {
	db := testDatabase(t)
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
	if err := db.Create(&Owner{ID: ownerID, Name: "account"}).Error; err != nil {
		t.Fatal(err)
	}
	var failure *pgconn.PgError
	if err := db.Create(&Owner{ID: widgetID, Name: "account"}).Error; !errors.As(err, &failure) || failure.Code != "23505" {
		t.Fatalf("unique constraint: %v", err)
	}
	widget := exampleWidget()
	widget.Version = 0
	if err := db.Omit("Owner").Create(&widget).Error; !errors.As(err, &failure) || failure.Code != "23514" {
		t.Fatalf("version constraint: %v", err)
	}
}

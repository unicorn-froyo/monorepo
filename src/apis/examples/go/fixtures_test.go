package main

import (
	"encoding/json"
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

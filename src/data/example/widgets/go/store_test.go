package widgets

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"
	"time"
)

func TestStoreQueriesAndCancellation(t *testing.T) {
	db := testDatabase(t)
	pool, err := db.DB()
	if err != nil {
		t.Fatal(err)
	}
	store := NewStore(db)
	ctx := context.Background()
	rows, err := store.List(ctx)
	if err != nil || len(rows) != 0 {
		t.Fatalf("empty database: %v, %v", rows, err)
	}
	owner := Owner{ID: "00000000-0000-0000-0000-000000000001", Name: "account"}
	if err := db.Create(&owner).Error; err != nil {
		t.Fatal(err)
	}
	// Insert in reverse order and exceed the old handler's implicit 100-row cap.
	for index := 101; index > 0; index-- {
		widget := Widget{
			ID: fmt.Sprintf("00000000-0000-0000-0001-%012d", index), OwnerID: owner.ID,
			Name: "雪", Version: 1, Amount: "1.00000000", Payload: []byte{0, 255},
			Metadata: json.RawMessage(`{}`), CreatedAt: time.Now().UTC(),
		}
		if err := db.Omit("Owner").Create(&widget).Error; err != nil {
			t.Fatal(err)
		}
	}
	rows, err = store.List(ctx)
	if err != nil || len(rows) != 101 {
		t.Fatalf("list truncated or failed: count=%d error=%v", len(rows), err)
	}
	for index, row := range rows {
		if row.ID != fmt.Sprintf("00000000-0000-0000-0001-%012d", index+1) || row.Owner.Name != owner.Name {
			t.Fatalf("order or owner changed: %+v", row)
		}
	}
	if err := store.Ready(ctx); err != nil {
		t.Fatal(err)
	}
	cancelled, cancel := context.WithCancel(ctx)
	cancel()
	if _, err := store.List(cancelled); err == nil {
		t.Fatal("list ignored request cancellation")
	}
	if err := store.Ready(cancelled); err == nil {
		t.Fatal("readiness ignored request cancellation")
	}
	if err := pool.Close(); err != nil {
		t.Fatal(err)
	}
	if _, err := store.List(ctx); err == nil {
		t.Fatal("closed database query succeeded")
	}
	if err := store.Ready(ctx); err == nil {
		t.Fatal("closed database is ready")
	}
}

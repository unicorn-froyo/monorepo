package widgets

import (
	"context"

	"gorm.io/gorm"
)

// Store queries widgets in the Flyway-managed schema using the startup-owned pool.
type Store struct {
	database *gorm.DB
}

// NewStore binds widget operations to an existing connection pool.
func NewStore(database *gorm.DB) *Store {
	return &Store{database: database}
}

// List loads widgets and their owners in stable ID order.
func (store *Store) List(ctx context.Context) ([]Widget, error) {
	var records []Widget
	err := store.database.WithContext(ctx).Preload("Owner").Order("id").Find(&records).Error
	return records, err
}

// Ready checks database connectivity using the caller's request context.
func (store *Store) Ready(ctx context.Context) error {
	return store.database.WithContext(ctx).Exec("SELECT 1").Error
}

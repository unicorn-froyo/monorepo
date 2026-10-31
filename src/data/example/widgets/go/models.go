// Package widgets maps GORM entities to the shared Flyway-owned example schema.
package widgets

import (
	"encoding/json"
	"time"
)

// Owner owns widgets; Flyway supplies unique and foreign-key constraints.
type Owner struct {
	ID      string   `gorm:"type:uuid;primaryKey"`
	Name    string   `gorm:"column:display_name"`
	Widgets []Widget `gorm:"foreignKey:OwnerID"`
}

func (Owner) TableName() string { return "widgets.owners" }

// Widget uses exact decimal text and int64 rather than floating-point conversions.
type Widget struct {
	ID           string          `gorm:"type:uuid;primaryKey"`
	OwnerID      string          `gorm:"type:uuid"`
	Name         string          `gorm:"column:display_name"`
	Version      int64           `gorm:"column:revision"`
	Amount       string          `gorm:"type:numeric(30,8)"`
	Payload      []byte          `gorm:"type:bytea"`
	Metadata     json.RawMessage `gorm:"type:jsonb"`
	CreatedAt    time.Time
	OptionalText *string
	Owner        Owner `gorm:"foreignKey:OwnerID"`
}

func (Widget) TableName() string { return "widgets.widgets" }

// Outbox events commit in the same native GORM transaction as domain changes.
type Outbox struct {
	ID        string `gorm:"type:uuid;primaryKey"`
	WidgetID  string `gorm:"type:uuid"`
	EventType string
}

func (Outbox) TableName() string { return "widgets.outbox" }

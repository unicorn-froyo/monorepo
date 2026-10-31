package widgets

import (
	"sync"
	"testing"

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

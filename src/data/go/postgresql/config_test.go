package postgresql

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"gorm.io/gorm"
)

func TestOpenConnectionContractAndPool(t *testing.T) {
	path := filepath.Join(t.TempDir(), "connection.json")
	settings := connection{FormatVersion: 1, Host: "localhost", Port: 5432, Database: "testdb", User: "app", Password: "p@:/?#", SSLMode: "disable"}
	write := func(value any) {
		t.Helper()
		data, err := json.Marshal(value)
		if err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, data, 0600); err != nil {
			t.Fatal(err)
		}
	}
	write(settings)
	t.Setenv("POSTGRES_CONNECTION_FILE", path)
	database, err := Open("")
	if err != nil {
		t.Fatal(err)
	}
	pool, err := database.DB()
	if err != nil {
		t.Fatal(err)
	}
	defer pool.Close()
	if pool.Stats().MaxOpenConnections != 5 {
		t.Fatal("pool is not bounded")
	}
	if _, err := Open(path + ".missing"); err == nil {
		t.Fatal("missing file accepted")
	}
	if err := os.WriteFile(path, []byte("{"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := Open(path); err == nil {
		t.Fatal("malformed JSON accepted")
	}
	for _, mutate := range []func(*connection){
		func(c *connection) { c.FormatVersion = 2 }, func(c *connection) { c.Port = 0 }, func(c *connection) { c.Port = 65536 },
		func(c *connection) { c.Host = "" }, func(c *connection) { c.Database = "" }, func(c *connection) { c.User = "" }, func(c *connection) { c.SSLMode = "prefer" },
	} {
		invalid := settings
		mutate(&invalid)
		write(invalid)
		if _, err := Open(path); err == nil {
			t.Fatalf("invalid settings accepted: %+v", invalid)
		}
	}
	write(settings)
	original := openDatabase
	t.Cleanup(func() { openDatabase = original })
	want := errors.New("dialector failed")
	openDatabase = func(gorm.Dialector, ...gorm.Option) (*gorm.DB, error) { return nil, want }
	if _, err := Open(path); !errors.Is(err, want) {
		t.Fatalf("got %v, want %v", err, want)
	}
	openDatabase = func(gorm.Dialector, ...gorm.Option) (*gorm.DB, error) { return &gorm.DB{Config: &gorm.Config{}}, nil }
	if _, err := Open(path); err == nil {
		t.Fatal("invalid GORM pool accepted")
	}
}

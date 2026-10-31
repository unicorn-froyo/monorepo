package postgresql

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestOpenConnectionContractAndPool(t *testing.T) {
	path := filepath.Join(t.TempDir(), "connection.json")
	data, err := os.ReadFile(os.Getenv("POSTGRES_CONNECTION_FILE"))
	if err != nil {
		t.Fatal(err)
	}
	var settings connection
	if err := json.Unmarshal(data, &settings); err != nil {
		t.Fatal(err)
	}
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
	var currentDatabase, currentUser string
	if err := pool.QueryRow("SELECT current_database(), current_user").Scan(&currentDatabase, &currentUser); err != nil {
		t.Fatal(err)
	}
	if currentDatabase != settings.Database || currentUser != settings.User {
		t.Fatal("did not connect to the fixture database as the application role")
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
	invalid := settings
	invalid.Password += "-incorrect"
	write(invalid)
	if _, err := Open(path); err == nil {
		t.Fatal("PostgreSQL accepted incorrect credentials")
	}
	invalid = settings
	invalid.SSLMode = "verify-full"
	write(invalid)
	t.Setenv("PGSSLROOTCERT", filepath.Join(t.TempDir(), "missing-ca.pem"))
	if _, err := Open(path); err == nil {
		t.Fatal("missing TLS trust root accepted")
	}
}

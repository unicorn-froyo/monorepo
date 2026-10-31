// Package postgresql opens bounded GORM pools using the shared runtime fixture contract.
package postgresql

import (
	"encoding/json"
	"fmt"
	"net"
	"net/url"
	"os"
	"strconv"
	"time"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

var openDatabase = gorm.Open

type connection struct {
	FormatVersion int    `json:"format_version"`
	Host          string `json:"host"`
	Port          int    `json:"port"`
	Database      string `json:"database"`
	User          string `json:"user"`
	Password      string `json:"password"`
	SSLMode       string `json:"sslmode"`
}

// Open reads the private connection file and configures a pool without migrating tables.
// An empty path reads POSTGRES_CONNECTION_FILE. Connections are established lazily;
// callers use GORM's WithContext for query deadlines and transactions.
func Open(path string) (*gorm.DB, error) {
	if path == "" {
		path = os.Getenv("POSTGRES_CONNECTION_FILE")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read PostgreSQL connection: %w", err)
	}
	var settings connection
	if err := json.Unmarshal(data, &settings); err != nil {
		return nil, fmt.Errorf("decode PostgreSQL connection: %w", err)
	}
	if settings.FormatVersion != 1 || settings.Port < 1 || settings.Port > 65535 || settings.Host == "" || settings.Database == "" || settings.User == "" {
		return nil, fmt.Errorf("invalid PostgreSQL connection settings")
	}
	switch settings.SSLMode {
	case "disable", "require", "verify-ca", "verify-full":
	default:
		return nil, fmt.Errorf("unsupported PostgreSQL TLS policy")
	}
	address := url.URL{Scheme: "postgres", User: url.UserPassword(settings.User, settings.Password), Host: net.JoinHostPort(settings.Host, strconv.Itoa(settings.Port)), Path: "/" + settings.Database}
	query := address.Query()
	query.Set("sslmode", settings.SSLMode)
	query.Set("connect_timeout", "5")
	address.RawQuery = query.Encode()
	database, err := openDatabase(postgres.Open(address.String()), &gorm.Config{DisableAutomaticPing: true, Logger: logger.Default.LogMode(logger.Silent)})
	if err != nil {
		return nil, err
	}
	pool, err := database.DB()
	if err != nil {
		return nil, err
	}
	pool.SetMaxOpenConns(5)
	pool.SetMaxIdleConns(5)
	pool.SetConnMaxLifetime(30 * time.Minute)
	return database, nil
}

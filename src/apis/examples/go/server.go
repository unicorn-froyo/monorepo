package main

import (
	"log"
	"net/http"
	"os"

	widgets "github.com/unicorn-froyo/monorepo/src/data/example/widgets/go"
	"github.com/unicorn-froyo/monorepo/src/data/go/postgresql"
	"gorm.io/gorm"
)

// Keep process-level effects replaceable so main's wiring can be tested
// without opening a production port or terminating the test process.
var listenAndServe = (*http.Server).ListenAndServe
var logFatal = log.Fatal
var openDatabase = postgresql.Open

func newServer(store widgetStore) *http.Server {
	return &http.Server{
		Addr:    ":8080",
		Handler: newHandler(store),
	}
}

func main() {
	var database *gorm.DB
	var store widgetStore
	if path := os.Getenv("POSTGRES_CONNECTION_FILE"); path != "" {
		var err error
		database, err = openDatabase(path)
		if err != nil {
			logFatal(err)
			return
		}
		pool, err := database.DB()
		if err != nil {
			logFatal(err)
			return
		}
		defer pool.Close()
		store = widgets.NewStore(database)
	}
	logFatal(listenAndServe(newServer(store)))
}

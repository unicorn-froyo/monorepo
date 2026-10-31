package main

import (
	"flag"
	"log"
	"net/http"
	"os"
	"strconv"

	widgets "github.com/unicorn-froyo/monorepo/src/data/example/widgets/go"
	"github.com/unicorn-froyo/monorepo/src/data/go/postgresql"
)

// Keep process-level effects replaceable so main's wiring can be tested
// without opening a production port or terminating the test process.
var listenAndServe = (*http.Server).ListenAndServe
var logFatal = log.Fatal
var port = flag.Int("port", 8080, "HTTP listen port")

func newServer(store widgetStore) *http.Server {
	return &http.Server{
		Addr:    ":8080",
		Handler: newHandler(store),
	}
}

func main() {
	flag.Parse()
	var store widgetStore
	if path := os.Getenv("POSTGRES_CONNECTION_FILE"); path != "" {
		database, err := postgresql.Open(path)
		if err != nil {
			logFatal(err)
			return
		}
		// Open supplies a concrete database/sql pool, never a transaction handle.
		pool, _ := database.DB()
		defer pool.Close()
		store = widgets.NewStore(database)
	}
	server := newServer(store)
	server.Addr = ":" + strconv.Itoa(*port)
	logFatal(listenAndServe(server))
}

package main

import (
	"context"
	"os"

	"github.com/unicorn-froyo/monorepo/src/apis/go/server"
	widgets "github.com/unicorn-froyo/monorepo/src/data/example/widgets/go"
	"github.com/unicorn-froyo/monorepo/src/data/go/postgresql"
)

// run owns application dependencies until the HTTP server has stopped.
func run(ctx context.Context, address string) error {
	var store widgetStore
	if path := os.Getenv("POSTGRES_CONNECTION_FILE"); path != "" {
		database, err := postgresql.Open(path)
		if err != nil {
			return err
		}
		// Open supplies a concrete database/sql pool, never a transaction handle.
		pool, _ := database.DB()
		defer pool.Close()
		store = widgets.NewStore(database)
	}
	return server.Serve(ctx, server.New(address, newHandler(store)))
}

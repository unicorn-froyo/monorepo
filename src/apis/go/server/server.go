// Package server constructs and runs HTTP servers for the shared Go API base.
package server

import (
	"context"
	"errors"
	"net/http"
)

// New constructs an HTTP server with an explicit address and application handler.
func New(address string, handler http.Handler) *http.Server {
	return &http.Server{Addr: address, Handler: handler}
}

// Serve runs the server until cancellation or a listener failure.
func Serve(ctx context.Context, server *http.Server) error {
	stop := context.AfterFunc(ctx, func() { server.Close() })
	defer stop()
	err := server.ListenAndServe()
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}

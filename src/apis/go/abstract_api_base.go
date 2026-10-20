// Package api provides the shared HTTP API foundation.
package api

import "net/http"

// API owns the request multiplexer used by an HTTP service.
type API struct {
	mux *http.ServeMux
}

// New creates an API with an empty route table.
func New() *API {
	return &API{mux: http.NewServeMux()}
}

// Handle registers a handler for an HTTP method and path.
func (a *API) Handle(method, path string, handler http.HandlerFunc) {
	a.mux.HandleFunc(method+" "+path, handler)
}

// Handler returns the API's HTTP handler.
func (a *API) Handler() http.Handler {
	return a.mux
}

// Package api provides the shared HTTP API foundation.
package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// API owns the Gin engine used by an HTTP service.
type API struct {
	engine *gin.Engine
}

// New creates an API with an empty route table.
func New() *API {
	return &API{engine: gin.New()}
}

// Handle registers a handler for an HTTP method and path.
func (a *API) Handle(method, path string, handler gin.HandlerFunc) {
	a.engine.Handle(method, path, handler)
}

// Handler returns the API's HTTP handler.
func (a *API) Handler() http.Handler {
	return a.engine
}

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

// New creates an API with an empty route table and response hardening.
func New() *API {
	engine := gin.New()
	engine.Use(securityHeaders)
	return &API{engine: engine}
}

// Handle registers a handler for an HTTP method and path.
func (a *API) Handle(method, path string, handler gin.HandlerFunc) {
	a.engine.Handle(method, path, handler)
}

func securityHeaders(context *gin.Context) {
	headers := context.Writer.Header()
	headers.Set("X-Content-Type-Options", "nosniff")
	headers.Set("X-Frame-Options", "DENY")
	headers.Set("Referrer-Policy", "no-referrer")
	headers.Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
	if context.Request.TLS != nil {
		headers.Set("Strict-Transport-Security", "max-age=31536000")
	}
	context.Next()
}

// Handler returns the API's HTTP handler.
func (a *API) Handler() http.Handler {
	return a.engine
}

package api

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestAPIRegistersRoute(t *testing.T) {
	gin.SetMode(gin.TestMode)
	service := New()
	service.Handle(http.MethodGet, "/health", func(context *gin.Context) {
		context.Status(http.StatusNoContent)
	})

	request := httptest.NewRequest(http.MethodGet, "/health", nil)
	response := httptest.NewRecorder()
	service.Handler().ServeHTTP(response, request)

	if response.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusNoContent)
	}
}

func TestSecurityHeaders(t *testing.T) {
	gin.SetMode(gin.TestMode)
	service := New()
	service.Handle(http.MethodGet, "/health", func(context *gin.Context) {
		context.Status(http.StatusNoContent)
	})
	for _, path := range []string{"/health", "/missing"} {
		for _, scheme := range []string{"http", "https"} {
			t.Run(scheme+path, func(t *testing.T) {
				request := httptest.NewRequest(http.MethodGet, scheme+"://example.com"+path, nil)
				response := httptest.NewRecorder()
				service.Handler().ServeHTTP(response, request)
				for name, want := range map[string]string{
					"X-Content-Type-Options": "nosniff",
					"X-Frame-Options":        "DENY",
					"Referrer-Policy":        "no-referrer",
					"Permissions-Policy":     "camera=(), microphone=(), geolocation=()",
				} {
					if got := response.Header().Get(name); got != want {
						t.Errorf("%s = %q, want %q", name, got, want)
					}
				}
				wantHSTS := ""
				if scheme == "https" {
					wantHSTS = "max-age=31536000"
				}
				if got := response.Header().Get("Strict-Transport-Security"); got != wantHSTS {
					t.Errorf("HSTS = %q, want %q", got, wantHSTS)
				}
			})
		}
	}
}

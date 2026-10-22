package main

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func TestMainEntrypoint(t *testing.T) {
	originalListen, originalFatal := listenAndServe, logFatal
	t.Cleanup(func() {
		listenAndServe, logFatal = originalListen, originalFatal
	})
	want := errors.New("server stopped")
	started, logged := false, false
	listenAndServe = func(server *http.Server) error {
		started = true
		if server.Addr != ":8080" || server.Handler == nil {
			t.Fatalf("unexpected server configuration: %+v", server)
		}
		return want
	}
	logFatal = func(values ...any) {
		logged = true
		if len(values) != 1 || values[0] != want {
			t.Fatalf("logged %v, want server error", values)
		}
	}
	main()
	if !started || !logged {
		t.Fatalf("main did not start server and report its error: started=%v logged=%v", started, logged)
	}
}

func TestHTTPSHeaders(t *testing.T) {
	for _, path := range []string{"/widgets", "/missing"} {
		request := httptest.NewRequest(http.MethodGet, "https://example.com"+path, nil)
		response := httptest.NewRecorder()
		newHandler().ServeHTTP(response, request)
		for header, want := range map[string]string{
			"Strict-Transport-Security": "max-age=31536000",
			"X-Content-Type-Options": "nosniff",
			"X-Frame-Options": "DENY",
			"Referrer-Policy": "no-referrer",
			"Permissions-Policy": "camera=(), microphone=(), geolocation=()",
		} {
			if got := response.Header().Get(header); got != want {
				t.Errorf("%s on %s = %q, want %q", header, path, got, want)
			}
		}
	}
}

func TestServerConfiguration(t *testing.T) {
	server := newServer()
	if server.Addr != ":8080" {
		t.Fatalf("server address = %q, want :8080", server.Addr)
	}
	response := httptest.NewRecorder()
	server.Handler.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/widgets", nil))
	if response.Code != http.StatusAccepted {
		t.Fatalf("server status = %d, want %d", response.Code, http.StatusAccepted)
	}
}

func TestGetWidgets(t *testing.T) {
	gin.SetMode(gin.TestMode)
	request := httptest.NewRequest(http.MethodGet, "/widgets", nil)
	response := httptest.NewRecorder()
	newHandler().ServeHTTP(response, request)

	if response.Code != http.StatusAccepted {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusAccepted)
	}
	if got := response.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Fatalf("X-Content-Type-Options = %q, want nosniff", got)
	}
	if response.Body.String() != "[]" {
		t.Fatalf("body = %q, want %q", response.Body.String(), "[]")
	}
	if contentType := response.Header().Get("Content-Type"); contentType != "application/json; charset=utf-8" {
		t.Fatalf("Content-Type = %q, want application/json; charset=utf-8", contentType)
	}
}

package api

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestAPIRegistersRoute(t *testing.T) {
	service := New()
	service.Handle(http.MethodGet, "/health", func(writer http.ResponseWriter, _ *http.Request) {
		writer.WriteHeader(http.StatusNoContent)
	})

	request := httptest.NewRequest(http.MethodGet, "/health", nil)
	response := httptest.NewRecorder()
	service.Handler().ServeHTTP(response, request)

	if response.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusNoContent)
	}
}

package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestGetWidgets(t *testing.T) {
	request := httptest.NewRequest(http.MethodGet, "/widgets", nil)
	response := httptest.NewRecorder()
	newHandler().ServeHTTP(response, request)

	if response.Code != http.StatusAccepted {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusAccepted)
	}
	if response.Body.String() != "[]" {
		t.Fatalf("body = %q, want %q", response.Body.String(), "[]")
	}
	if contentType := response.Header().Get("Content-Type"); contentType != "application/json" {
		t.Fatalf("Content-Type = %q, want application/json", contentType)
	}
}

package server

import (
	"context"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestNewUsesAddressAndHandler(t *testing.T) {
	server := New("127.0.0.1:8080", http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusAccepted)
	}))
	if server.Addr != "127.0.0.1:8080" {
		t.Fatal(server.Addr)
	}
	response := httptest.NewRecorder()
	server.Handler.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/", nil))
	if response.Code != http.StatusAccepted {
		t.Fatal(response.Code)
	}
}

func TestServeStopsOnCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := Serve(ctx, New("127.0.0.1:0", http.NotFoundHandler())); err != nil {
		t.Fatal(err)
	}
}

func TestServeReturnsListenerFailure(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	if err := Serve(context.Background(), New(listener.Addr().String(), http.NotFoundHandler())); err == nil {
		t.Fatal("occupied address was accepted")
	}
}

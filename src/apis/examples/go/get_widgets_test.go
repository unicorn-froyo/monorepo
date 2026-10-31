package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	"github.com/gin-gonic/gin"
	widgets "github.com/unicorn-froyo/monorepo/src/data/example/widgets/go"
)

func TestRunWithoutDatabase(t *testing.T) {
	t.Setenv("POSTGRES_CONNECTION_FILE", "")
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := run(ctx, "127.0.0.1:0"); err != nil {
		t.Fatal(err)
	}
}

func TestHeaders(t *testing.T) {
	handler := newHandler(widgets.NewStore(databaseWithWidgets(t)))
	for _, scheme := range []string{"http", "https"} {
		for _, path := range []string{"/widgets", "/missing"} {
			t.Run(scheme+path, func(t *testing.T) {
				request := httptest.NewRequest(http.MethodGet, scheme+"://example.com"+path, nil)
				response := httptest.NewRecorder()
				handler.ServeHTTP(response, request)
				wantStatus := http.StatusOK
				if path == "/missing" {
					wantStatus = http.StatusNotFound
				}
				if response.Code != wantStatus {
					t.Fatalf("status = %d, want %d", response.Code, wantStatus)
				}
				for header, want := range map[string]string{
					"X-Content-Type-Options": "nosniff",
					"X-Frame-Options":        "DENY",
					"Referrer-Policy":        "no-referrer",
					"Permissions-Policy":     "camera=(), microphone=(), geolocation=()",
				} {
					if got := response.Header().Get(header); got != want {
						t.Errorf("%s = %q, want %q", header, got, want)
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

func TestGetWidgets(t *testing.T) {
	gin.SetMode(gin.TestMode)
	request := httptest.NewRequest(http.MethodGet, "/widgets", nil)
	response := httptest.NewRecorder()
	newHandler(widgets.NewStore(databaseWithWidgets(t))).ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusOK)
	}
	if got := response.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Fatalf("X-Content-Type-Options = %q, want nosniff", got)
	}
	var got []map[string]string
	if err := json.Unmarshal(response.Body.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	want := []map[string]string{{"id": widgetID, "name": "雪☃", "owner": "account"}}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("widgets = %v, want seeded database records %v", got, want)
	}
	if contentType := response.Header().Get("Content-Type"); contentType != "application/json; charset=utf-8" {
		t.Fatalf("Content-Type = %q, want application/json; charset=utf-8", contentType)
	}
}

func TestGetWidgetsWithEmptyDatabase(t *testing.T) {
	response := httptest.NewRecorder()
	newHandler(widgets.NewStore(database(t))).ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/widgets", nil))
	if response.Code != http.StatusOK || response.Body.String() != "[]" {
		t.Fatalf("empty database: status=%d body=%s", response.Code, response.Body.String())
	}
}

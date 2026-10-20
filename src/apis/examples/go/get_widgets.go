package main

import (
	"net/http"

	api "github.com/unicorn-froyo/monorepo/src/apis/go"
)

func newHandler() http.Handler {
	service := api.New()
	service.Handle(http.MethodGet, "/widgets", func(writer http.ResponseWriter, _ *http.Request) {
		writer.Header().Set("Content-Type", "application/json")
		writer.WriteHeader(http.StatusAccepted)
		_, _ = writer.Write([]byte("[]"))
	})
	return service.Handler()
}

package main

import (
	"log"
	"net/http"
)

func newServer() *http.Server {
	return &http.Server{
		Addr:    ":8080",
		Handler: newHandler(),
	}
}

func main() {
	log.Fatal(newServer().ListenAndServe())
}

package main

import (
	"log"
	"net/http"
)

// Keep process-level effects replaceable so main's wiring can be tested
// without opening a production port or terminating the test process.
var listenAndServe = (*http.Server).ListenAndServe
var logFatal = log.Fatal

func newServer() *http.Server {
	return &http.Server{
		Addr:    ":8080",
		Handler: newHandler(),
	}
}

func main() {
	logFatal(listenAndServe(newServer()))
}

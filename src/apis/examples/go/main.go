package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"strconv"
	"syscall"
)

func main() {
	port := flag.Int("port", 8080, "HTTP listen port")
	flag.Parse()
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	if err := run(ctx, ":"+strconv.Itoa(*port)); err != nil {
		log.Print(err)
		os.Exit(1)
	}
}

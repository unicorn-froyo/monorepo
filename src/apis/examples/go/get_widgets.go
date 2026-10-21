package main

import (
	"net/http"

	"github.com/gin-gonic/gin"
	api "github.com/unicorn-froyo/monorepo/src/apis/go"
)

func newHandler() http.Handler {
	service := api.New()
	service.Handle(http.MethodGet, "/widgets", func(context *gin.Context) {
		context.JSON(http.StatusAccepted, []any{})
	})
	return service.Handler()
}

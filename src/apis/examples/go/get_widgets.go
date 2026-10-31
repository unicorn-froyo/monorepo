package main

import (
	"context"
	"net/http"

	"github.com/gin-gonic/gin"
	api "github.com/unicorn-froyo/monorepo/src/apis/go"
	widgets "github.com/unicorn-froyo/monorepo/src/data/example/widgets/go"
)

type widgetStore interface {
	List(context.Context) ([]widgets.Widget, error)
	Ready(context.Context) error
}

func newHandler(store widgetStore) http.Handler {
	service := api.New()
	service.Handle(http.MethodGet, "/widgets", func(context *gin.Context) {
		if store == nil {
			context.JSON(http.StatusServiceUnavailable, gin.H{"detail": "Database is not configured"})
			return
		}
		records, err := store.List(context.Request.Context())
		if err != nil {
			context.JSON(http.StatusInternalServerError, gin.H{"detail": "Database query failed"})
			return
		}
		result := make([]map[string]string, 0, len(records))
		for _, widget := range records {
			result = append(result, map[string]string{"id": widget.ID, "name": widget.Name, "owner": widget.Owner.Name})
		}
		context.JSON(http.StatusOK, result)
	})
	service.Handle(http.MethodGet, "/readyz", func(context *gin.Context) {
		if store != nil {
			if err := store.Ready(context.Request.Context()); err != nil {
				context.JSON(http.StatusServiceUnavailable, gin.H{"ready": false})
				return
			}
		}
		context.JSON(http.StatusOK, gin.H{"ready": true})
	})
	return service.Handler()
}

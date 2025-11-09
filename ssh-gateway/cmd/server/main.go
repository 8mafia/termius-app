package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"github.com/parssh/ssh-gateway/internal/config"
	"github.com/parssh/ssh-gateway/internal/websocket"
	"github.com/parssh/ssh-gateway/pkg/logger"
)

func main() {
	// Initialize logger
	logger.Init()

	// Load configuration
	cfg := config.Load()

	// Set Gin mode
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Create Gin router
	router := gin.New()

	// Add middleware
	router.Use(gin.Logger())
	router.Use(gin.Recovery())
	router.Use(corsMiddleware(cfg))

	// WebSocket upgrader
	upgrader := &websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			// Allow connections from allowed origins
			origin := r.Header.Get("Origin")
			for _, allowedOrigin := range cfg.CORSOrigins {
				if origin == allowedOrigin {
					return true
				}
			}
			return cfg.Environment != "production"
		},
		ReadBufferSize:  1024,
		WriteBufferSize: 1024,
	}

	// Create WebSocket hub
	hub := websocket.NewHub(cfg)
	go hub.Run()

	// Setup routes
	setupRoutes(router, hub, upgrader, cfg)

	// Create HTTP server
	server := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.Port),
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
	}

	// Start server in a goroutine
	go func() {
		log.Info().
			Str("port", fmt.Sprintf("%d", cfg.Port)).
			Msg("Starting SSH Gateway server")

		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("Failed to start server")
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info().Msg("Shutting down server...")

	// Graceful shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Fatal().Err(err).Msg("Server forced to shutdown")
	}

	log.Info().Msg("Server exited")
}

func setupRoutes(router *gin.Engine, hub *websocket.Hub, upgrader *websocket.Upgrader, cfg *config.Config) {
	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status":    "ok",
			"timestamp": time.Now().Unix(),
			"version":   "1.0.0",
		})
	})

	// Metrics endpoint
	if cfg.PrometheusEnabled {
		router.GET("/metrics", gin.WrapH(hub.GetMetricsHandler()))
	}

	// WebSocket endpoint
	router.GET("/ws", func(c *gin.Context) {
		websocket.HandleWebSocket(hub, upgrader, c.Writer, c.Request)
	})

	// API endpoints
	api := router.Group("/api/v1")
	{
		api.GET("/sessions", websocket.HandleGetSessions(hub))
		api.DELETE("/sessions/:id", websocket.HandleDeleteSession(hub))
		api.POST("/sessions/:id/share", websocket.HandleShareSession(hub))
	}
}

func corsMiddleware(cfg *config.Config) gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.Request.Header.Get("Origin")

		// Check if origin is allowed
		allowed := false
		for _, allowedOrigin := range cfg.CORSOrigins {
			if origin == allowedOrigin {
				allowed = true
				break
			}
		}

		if allowed {
			c.Header("Access-Control-Allow-Origin", origin)
		}

		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Authorization")
		c.Header("Access-Control-Allow-Credentials", "true")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}
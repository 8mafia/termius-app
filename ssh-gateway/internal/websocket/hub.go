package websocket

import (
	"net/http"
	"sync"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/gorilla/websocket"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog/log"

	"github.com/parssh/ssh-gateway/internal/config"
	"github.com/parssh/ssh-gateway/internal/models"
)

type Hub struct {
	// Configuration
	config *config.Config

	// Redis client
	redis *redis.Client

	// WebSocket connections
	clients    map[*Client]bool
	clientsMux sync.RWMutex

	// Active SSH sessions
	sessions    map[string]*models.Session
	sessionsMux sync.RWMutex

	// Metrics
	connectionsTotal   prometheus.Counter
	activeConnections  prometheus.Gauge
	sessionsTotal      prometheus.Counter
	activeSessions     prometheus.Gauge
	messagesTotal      prometheus.Counter
	errorsTotal        prometheus.Counter
}

func NewHub(cfg *config.Config) *Hub {
	// Initialize Redis client
	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.RedisURL,
		Password: cfg.RedisPassword,
		DB:       cfg.RedisDB,
	})

	hub := &Hub{
		config:  cfg,
		redis:   rdb,
		clients: make(map[*Client]bool),
		sessions: make(map[string]*models.Session),
	}

	// Initialize metrics
	hub.initMetrics()

	return hub
}

func (h *Hub) initMetrics() {
	h.connectionsTotal = prometheus.NewCounter(prometheus.CounterOpts{
		Name: "ssh_gateway_connections_total",
		Help: "Total number of WebSocket connections",
	})

	h.activeConnections = prometheus.NewGauge(prometheus.GaugeOpts{
		Name: "ssh_gateway_active_connections",
		Help: "Number of active WebSocket connections",
	})

	h.sessionsTotal = prometheus.NewCounter(prometheus.CounterOpts{
		Name: "ssh_gateway_sessions_total",
		Help: "Total number of SSH sessions",
	})

	h.activeSessions = prometheus.NewGauge(prometheus.GaugeOpts{
		Name: "ssh_gateway_active_sessions",
		Help: "Number of active SSH sessions",
	})

	h.messagesTotal = prometheus.NewCounter(prometheus.CounterOpts{
		Name: "ssh_gateway_messages_total",
		Help: "Total number of messages processed",
	})

	h.errorsTotal = prometheus.NewCounter(prometheus.CounterOpts{
		Name: "ssh_gateway_errors_total",
		Help: "Total number of errors",
	})

	// Register metrics
	prometheus.MustRegister(
		h.connectionsTotal,
		h.activeConnections,
		h.sessionsTotal,
		h.activeSessions,
		h.messagesTotal,
		h.errorsTotal,
	)
}

func (h *Hub) GetMetricsHandler() http.Handler {
	return promhttp.Handler()
}

func (h *Hub) Run() {
	// Cleanup ticker
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			h.cleanup()
		}
	}
}

func (h *Hub) RegisterClient(client *Client) {
	h.clientsMux.Lock()
	defer h.clientsMux.Unlock()

	h.clients[client] = true
	h.activeConnections.Inc()
	h.connectionsTotal.Inc()

	log.Info().
		Str("client_id", client.ID).
		Str("user_id", client.UserID).
		Msg("Client connected")
}

func (h *Hub) UnregisterClient(client *Client) {
	h.clientsMux.Lock()
	defer h.clientsMux.Unlock()

	if _, ok := h.clients[client]; ok {
		delete(h.clients, client)
		h.activeConnections.Dec()
		close(client.send)
	}

	log.Info().
		Str("client_id", client.ID).
		Str("user_id", client.UserID).
		Msg("Client disconnected")
}

func (h *Hub) RegisterSession(session *models.Session) {
	h.sessionsMux.Lock()
	defer h.sessionsMux.Unlock()

	h.sessions[session.ID] = session
	h.activeSessions.Inc()
	h.sessionsTotal.Inc()

	log.Info().
		Str("session_id", session.ID).
		Str("user_id", session.UserID).
		Str("host_id", session.HostID).
		Msg("SSH session started")
}

func (h *Hub) UnregisterSession(sessionID string) {
	h.sessionsMux.Lock()
	defer h.sessionsMux.Unlock()

	if session, ok := h.sessions[sessionID]; ok {
		// Close SSH connection
		if session.SSHClient != nil {
			session.SSHClient.Close()
		}

		delete(h.sessions, sessionID)
		h.activeSessions.Dec()
	}

	log.Info().
		Str("session_id", sessionID).
		Msg("SSH session ended")
}

func (h *Hub) GetSession(sessionID string) (*models.Session, bool) {
	h.sessionsMux.RLock()
	defer h.sessionsMux.RUnlock()

	session, ok := h.sessions[sessionID]
	return session, ok
}

func (h *Hub) BroadcastToSession(sessionID string, message []byte) {
	h.clientsMux.RLock()
	defer h.clientsMux.RUnlock()

	for client := range h.clients {
		if client.SessionID == sessionID {
			select {
			case client.send <- message:
				h.messagesTotal.Inc()
			default:
				// Channel is full, close client
				close(client.send)
				delete(h.clients, client)
				h.activeConnections.Dec()
			}
		}
	}
}

func (h *Hub) SendToClient(clientID string, message []byte) {
	h.clientsMux.RLock()
	defer h.clientsMux.RUnlock()

	for client := range h.clients {
		if client.ID == clientID {
			select {
			case client.send <- message:
				h.messagesTotal.Inc()
			default:
				// Channel is full, close client
				close(client.send)
				delete(h.clients, client)
				h.activeConnections.Dec()
			}
			break
		}
	}
}

func (h *Hub) GetClientSessions(userID string) []*models.Session {
	h.sessionsMux.RLock()
	defer h.sessionsMux.RUnlock()

	var sessions []*models.Session
	for _, session := range h.sessions {
		if session.UserID == userID {
			sessions = append(sessions, session)
		}
	}

	return sessions
}

func (h *Hub) cleanup() {
	// Clean up stale sessions
	h.sessionsMux.Lock()
	defer h.sessionsMux.Unlock()

	now := time.Now()
	for sessionID, session := range h.sessions {
		if session.LastActivity.Add(h.config.IdleTimeout).Before(now) {
			log.Info().
				Str("session_id", sessionID).
				Time("last_activity", session.LastActivity).
				Msg("Cleaning up idle session")

			if session.SSHClient != nil {
				session.SSHClient.Close()
			}
			delete(h.sessions, sessionID)
			h.activeSessions.Dec()
		}
	}

	// Clean up disconnected clients
	h.clientsMux.Lock()
	defer h.clientsMux.Unlock()

	for client := range h.clients {
		if client.LastPing.Add(h.config.PongWait).Before(now) {
			log.Info().
				Str("client_id", client.ID).
				Time("last_ping", client.LastPing).
				Msg("Cleaning up stale client")

			close(client.send)
			delete(h.clients, client)
			h.activeConnections.Dec()
		}
	}
}

func (h *Hub) GetStats() map[string]interface{} {
	h.clientsMux.RLock()
	h.sessionsMux.RLock()
	defer h.clientsMux.RUnlock()
	defer h.sessionsMux.RUnlock()

	return map[string]interface{}{
		"active_connections": len(h.clients),
		"active_sessions":    len(h.sessions),
		"max_connections":    h.config.MaxConnections,
		"uptime_seconds":     time.Since(time.Now()).Seconds(), // This would need to be tracked
	}
}
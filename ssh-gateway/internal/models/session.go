package models

import (
	"time"

	"github.com/gorilla/websocket"
)

type Session struct {
	// Session information
	ID    string `json:"id"`
	UserID string `json:"user_id"`
	HostID string `json:"host_id"`

	// WebSocket client
	Client interface {
		ID        string
		SessionID string
		IPAddress string
		UserAgent string
	}

	// SSH connection
	SSHClient interface {
		Close() error
	}

	// Terminal configuration
	Terminal TerminalConfig `json:"terminal"`

	// Timestamps
	CreatedAt     time.Time `json:"created_at"`
	LastActivity  time.Time `json:"last_activity"`
	DisconnectedAt time.Time `json:"disconnected_at,omitempty"`

	// Statistics
	BytesSent        int64 `json:"bytes_sent"`
	BytesReceived    int64 `json:"bytes_received"`
	CommandsRun      int   `json:"commands_run"`

	// Sharing
	IsShared     bool                 `json:"is_shared"`
	SharedUsers  map[string]User      `json:"shared_users"`
	Permissions  map[string][]string  `json:"permissions"`

	// Status
	Status string `json:"status"` // connecting, connected, disconnected, error
}

type TerminalConfig struct {
	Rows int    `json:"rows"`
	Cols int    `json:"cols"`
	Term string `json:"term"`
}

type User struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Email    string `json:"email"`
	IsActive bool   `json:"is_active"`
}

type Message struct {
	Type      string      `json:"type"`
	SessionID string      `json:"session_id,omitempty"`
	Data      interface{} `json:"data,omitempty"`
	Timestamp int64       `json:"timestamp"`
}

type ConnectData struct {
	HostID     string                 `json:"host_id"`
	AuthMethod string                 `json:"auth_method"`
	AuthData   map[string]string      `json:"auth_data"`
	Terminal   TerminalConfig         `json:"terminal"`
	ClientInfo map[string]interface{} `json:"client_info"`
}

type DataData struct {
	Data []byte `json:"data"`
}

type ResizeData struct {
	Rows int `json:"rows"`
	Cols int `json:"cols"`
}

type ErrorData struct {
	Message string `json:"message"`
	Code    string `json:"code,omitempty"`
}

type SessionStats struct {
	TotalSessions    int           `json:"total_sessions"`
	ActiveSessions   int           `json:"active_sessions"`
	SharedSessions   int           `json:"shared_sessions"`
	AverageDuration  time.Duration `json:"average_duration"`
	TotalBytesSent   int64         `json:"total_bytes_sent"`
	TotalBytesRecv   int64         `json:"total_bytes_received"`
}
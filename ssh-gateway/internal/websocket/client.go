package websocket

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/gorilla/websocket"
	"github.com/rs/zerolog/log"

	"github.com/parssh/ssh-gateway/internal/models"
)

type Client struct {
	// Hub reference
	hub *Hub

	// WebSocket connection
	conn *websocket.Conn

	// Client information
	ID        string
	UserID    string
	SessionID string
	IPAddress string
	UserAgent string

	// Channels
	send chan []byte

	// Timing
	LastPing time.Time
	LastRead time.Time
}

type Message struct {
	Type    string      `json:"type"`
	Session string      `json:"session,omitempty"`
	Data    interface{} `json:"data,omitempty"`
	Time    int64       `json:"time"`
}

type ConnectMessage struct {
	HostID     string                 `json:"host_id"`
	AuthMethod string                 `json:"auth_method"`
	AuthData   map[string]string      `json:"auth_data"`
	Terminal   models.TerminalConfig  `json:"terminal"`
}

type DataMessage struct {
	Data []byte `json:"data"`
}

type ResizeMessage struct {
	Rows int `json:"rows"`
	Cols int `json:"cols"`
}

func HandleWebSocket(hub *Hub, upgrader *websocket.Upgrader, w http.ResponseWriter, r *http.Request) {
	// Upgrade HTTP connection to WebSocket
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Error().Err(err).Msg("Failed to upgrade WebSocket connection")
		return
	}

	// Create client
	client := &Client{
		hub:        hub,
		conn:       conn,
		ID:         generateClientID(),
		IPAddress:  r.RemoteAddr,
		UserAgent:  r.Header.Get("User-Agent"),
		send:       make(chan []byte, 256),
		LastPing:   time.Now(),
		LastRead:   time.Now(),
	}

	// Register client with hub
	hub.RegisterClient(client)

	// Start goroutines
	go client.writePump()
	go client.readPump()
}

func (c *Client) readPump() {
	defer func() {
		c.hub.UnregisterClient(c)
		c.conn.Close()
	}()

	// Set read deadline
	c.conn.SetReadDeadline(time.Now().Add(c.hub.config.PongWait))
	c.conn.SetPongHandler(func(string) error {
		c.conn.SetReadDeadline(time.Now().Add(c.hub.config.PongWait))
		c.LastPing = time.Now()
		return nil
	})

	for {
		// Read message
		var message Message
		err := c.conn.ReadJSON(&message)
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Error().Err(err).
					Str("client_id", c.ID).
					Msg("WebSocket error")
			}
			break
		}

		c.LastRead = time.Now()
		c.handleMessage(message)
	}
}

func (c *Client) writePump() {
	ticker := time.NewTicker(c.hub.config.PingInterval)
	defer func() {
		ticker.Stop()
		c.conn.Close()
	}()

	for {
		select {
		case message, ok := <-c.send:
			c.conn.SetWriteDeadline(time.Now().Add(c.hub.config.WriteWait))
			if !ok {
				// Hub closed channel
				c.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			if err := c.conn.WriteMessage(websocket.TextMessage, message); err != nil {
				log.Error().Err(err).
					Str("client_id", c.ID).
					Msg("Failed to write WebSocket message")
				return
			}

		case <-ticker.C:
			c.conn.SetWriteDeadline(time.Now().Add(c.hub.config.WriteWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

func (c *Client) handleMessage(message Message) {
	log.Info().
		Str("client_id", c.ID).
		Str("type", message.Type).
		Msg("Received message")

	switch message.Type {
	case "connect":
		c.handleConnect(message)
	case "data":
		c.handleData(message)
	case "resize":
		c.handleResize(message)
	case "disconnect":
		c.handleDisconnect(message)
	case "ping":
		c.handlePing()
	default:
		log.Warn().
			Str("type", message.Type).
			Msg("Unknown message type")
	}
}

func (c *Client) handleConnect(message Message) {
	// Parse connect message
	var connectMsg ConnectMessage
	if err := json.Unmarshal(messageToBytes(message.Data), &connectMsg); err != nil {
		log.Error().Err(err).Msg("Failed to parse connect message")
		c.sendError("Invalid connect message")
		return
	}

	// TODO: Validate JWT token and get user ID
	// For now, we'll use a placeholder
	c.UserID = "user-123"

	// Create SSH session
	session := &models.Session{
		ID:        generateSessionID(),
		UserID:    c.UserID,
		HostID:    connectMsg.HostID,
		Client:    c,
		CreatedAt: time.Now(),
		LastActivity: time.Now(),
		Terminal: connectMsg.Terminal,
	}

	// TODO: Establish SSH connection
	// For now, we'll simulate connection
	go c.simulateSSHConnection(session)

	// Register session
	c.SessionID = session.ID
	c.hub.RegisterSession(session)

	// Send connected response
	c.sendMessage(Message{
		Type: "connected",
		Data: map[string]interface{}{
			"session_id": session.ID,
			"message":    "Connected successfully",
		},
	})
}

func (c *Client) handleData(message Message) {
	if c.SessionID == "" {
		c.sendError("No active session")
		return
	}

	// Parse data message
	var dataMsg DataMessage
	if err := json.Unmarshal(messageToBytes(message.Data), &dataMsg); err != nil {
		log.Error().Err(err).Msg("Failed to parse data message")
		return
	}

	// Get session
	session, exists := c.hub.GetSession(c.SessionID)
	if !exists {
		c.sendError("Session not found")
		return
	}

	// TODO: Send data to SSH connection
	// For now, we'll echo back the data
	session.LastActivity = time.Now()

	// Broadcast to all clients in the session
	response := Message{
		Type: "data",
		Data: dataMsg.Data,
	}
	responseBytes, _ := json.Marshal(response)
	c.hub.BroadcastToSession(c.SessionID, responseBytes)
}

func (c *Client) handleResize(message Message) {
	if c.SessionID == "" {
		c.sendError("No active session")
		return
	}

	// Parse resize message
	var resizeMsg ResizeMessage
	if err := json.Unmarshal(messageToBytes(message.Data), &resizeMsg); err != nil {
		log.Error().Err(err).Msg("Failed to parse resize message")
		return
	}

	// Get session
	session, exists := c.hub.GetSession(c.SessionID)
	if !exists {
		c.sendError("Session not found")
		return
	}

	// Update terminal size
	session.Terminal.Rows = resizeMsg.Rows
	session.Terminal.Cols = resizeMsg.Cols
	session.LastActivity = time.Now()

	// TODO: Send resize signal to SSH connection
	log.Info().
		Str("session_id", c.SessionID).
		Int("rows", resizeMsg.Rows).
		Int("cols", resizeMsg.Cols).
		Msg("Terminal resized")
}

func (c *Client) handleDisconnect(message Message) {
	if c.SessionID != "" {
		c.hub.UnregisterSession(c.SessionID)
		c.SessionID = ""
	}
}

func (c *Client) handlePing() {
	c.sendMessage(Message{
		Type: "pong",
	})
}

func (c *Client) sendMessage(message Message) {
	messageBytes, err := json.Marshal(message)
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal message")
		return
	}

	select {
	case c.send <- messageBytes:
	default:
		log.Warn().Str("client_id", c.ID).Msg("Send channel full")
	}
}

func (c *Client) sendError(errorMsg string) {
	c.sendMessage(Message{
		Type: "error",
		Data: map[string]interface{}{
			"message": errorMsg,
		},
	})
}

func (c *Client) simulateSSHConnection(session *models.Session) {
	// Simulate SSH connection for demo purposes
	// In production, this would establish a real SSH connection

	log.Info().
		Str("session_id", session.ID).
		Str("host_id", session.HostID).
		Msg("Simulating SSH connection")

	// Simulate welcome message
	welcome := "Welcome to Ubuntu 22.04 LTS (GNU/Linux 5.15.0-91-generic x86_64)\r\n" +
		" * Documentation:  https://help.ubuntu.com\r\n" +
		" * Management:     https://landscape.canonical.com\r\n" +
		" * Support:        https://ubuntu.com/pro\r\n\r\n" +
		"Last login: Mon Jan 01 12:00:00 2024 from 192.168.1.100\r\n" +
		"user@ubuntu:~$ "

	response := Message{
		Type: "data",
		Data: []byte(welcome),
	}
	responseBytes, _ := json.Marshal(response)
	c.hub.BroadcastToSession(session.ID, responseBytes)
}

func generateClientID() string {
	return "client-" + time.Now().Format("20060102150405") + "-" + randomString(8)
}

func generateSessionID() string {
	return "session-" + time.Now().Format("20060102150405") + "-" + randomString(8)
}

func messageToBytes(data interface{}) []byte {
	if bytes, ok := data.([]byte); ok {
		return bytes
	}
	if str, ok := data.(string); ok {
		return []byte(str)
	}
	if bytes, err := json.Marshal(data); err == nil {
		return bytes
	}
	return []byte{}
}

func randomString(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[time.Now().UnixNano()%int64(len(charset))]
	}
	return string(b)
}
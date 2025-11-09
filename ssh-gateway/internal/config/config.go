package config

import (
	"os"
	"strconv"
	"time"

	"github.com/rs/zerolog/log"
)

type Config struct {
	// Server settings
	Port            int           `json:"port"`
	Environment     string        `json:"environment"`
	Debug           bool          `json:"debug"`
	ReadTimeout     time.Duration `json:"read_timeout"`
	WriteTimeout    time.Duration `json:"write_timeout"`
	PingInterval    time.Duration `json:"ping_interval"`
	PongWait        time.Duration `json:"pong_wait"`
	WriteWait       time.Duration `json:"write_wait"`
	MaxMessageSize  int64         `json:"max_message_size"`

	// Redis settings
	RedisURL        string        `json:"redis_url"`
	RedisPassword   string        `json:"redis_password"`
	RedisDB         int           `json:"redis_db"`

	// JWT settings
	JWTSecret       string        `json:"jwt_secret"`
	JWTAlgorithm    string        `json:"jwt_algorithm"`

	// SSH settings
	MaxConnections  int           `json:"max_connections"`
	IdleTimeout     time.Duration `json:"idle_timeout"`
	ConnectionTimeout time.Duration `json:"connection_timeout"`

	// CORS settings
	CORSOrigins     []string      `json:"cors_origins"`

	// Monitoring
	PrometheusEnabled bool         `json:"prometheus_enabled"`
	MetricsPort      int           `json:"metrics_port"`

	// Security
	TrustedProxies  []string      `json:"trusted_proxies"`
}

func Load() *Config {
	cfg := &Config{
		Port:               getEnvInt("SSH_GATEWAY_PORT", 8080),
		Environment:        getEnv("ENVIRONMENT", "development"),
		Debug:              getEnvBool("DEBUG", false),
		ReadTimeout:        getEnvDuration("READ_TIMEOUT", 15*time.Second),
		WriteTimeout:       getEnvDuration("WRITE_TIMEOUT", 15*time.Second),
		PingInterval:       getEnvDuration("PING_INTERVAL", 54*time.Second),
		PongWait:           getEnvDuration("PONG_WAIT", 60*time.Second),
		WriteWait:          getEnvDuration("WRITE_WAIT", 10*time.Second),
		MaxMessageSize:     int64(getEnvInt("MAX_MESSAGE_SIZE", 512)),
		RedisURL:           getEnv("REDIS_URL", "redis://localhost:6379"),
		RedisPassword:      getEnv("REDIS_PASSWORD", ""),
		RedisDB:            getEnvInt("REDIS_DB", 0),
		JWTSecret:          getEnv("JWT_SECRET", "your-secret-key"),
		JWTAlgorithm:       getEnv("JWT_ALGORITHM", "HS256"),
		MaxConnections:     getEnvInt("MAX_CONNECTIONS", 100),
		IdleTimeout:        getEnvDuration("IDLE_TIMEOUT", 30*time.Minute),
		ConnectionTimeout:  getEnvDuration("CONNECTION_TIMEOUT", 30*time.Second),
		CORSOrigins:        getEnvSlice("CORS_ORIGINS", []string{"http://localhost:3000", "http://localhost"}),
		PrometheusEnabled:  getEnvBool("PROMETHEUS_ENABLED", true),
		MetricsPort:        getEnvInt("METRICS_PORT", 9090),
		TrustedProxies:     getEnvSlice("TRUSTED_PROXIES", []string{"127.0.0.1", "::1"}),
	}

	// Log configuration
	log.Info().
		Str("environment", cfg.Environment).
		Int("port", cfg.Port).
		Str("redis_url", cfg.RedisURL).
		Msg("Configuration loaded")

	return cfg
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolValue, err := strconv.ParseBool(value); err == nil {
			return boolValue
		}
	}
	return defaultValue
}

func getEnvDuration(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if durationValue, err := time.ParseDuration(value); err == nil {
			return durationValue
		}
	}
	return defaultValue
}

func getEnvSlice(key string, defaultValue []string) []string {
	if value := os.Getenv(key); value != "" {
		// Simple comma-separated parsing
		// In production, you might want more robust parsing
		return []string{value}
	}
	return defaultValue
}
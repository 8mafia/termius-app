import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "ParSSH"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Database settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "parssh"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "parssh"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    # JWT settings
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption settings
    ENCRYPTION_KEY_BASE64: str = ""

    # SSH Gateway settings
    SSH_GATEWAY_HOST: str = "ssh-gateway"
    SSH_GATEWAY_PORT: int = 8080

    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Security settings
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    SECURE_COOKIES: bool = False
    CSRF_PROTECTION: bool = True

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    AUTH_RATE_LIMIT_PER_MINUTE: int = 5

    # Email settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True

    # OAuth settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    # SSL settings
    DOMAIN: Optional[str] = None
    SSL_EMAIL: Optional[str] = None

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Monitoring settings
    PROMETHEUS_ENABLED: bool = True
    METRICS_PORT: int = 9090

    # Session settings
    SESSION_TIMEOUT_MINUTES: int = 30
    MAX_CONCURRENT_SESSIONS: int = 10

    # File upload settings
    MAX_FILE_SIZE_MB: int = 100
    UPLOAD_PATH: str = "/tmp/uploads"

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() in ("development", "dev", "local")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")

    def get_cors_origins(self) -> List[str]:
        if self.is_development:
            return ["*"]
        return self.CORS_ORIGINS

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
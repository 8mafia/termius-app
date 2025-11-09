import time
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.routing import Route

from app.core.config import settings
from app.core.database import init_db, close_db, get_redis, close_redis
from app.api import auth, users, hosts, groups, sessions
from app.utils.exceptions import ParSSHException, setup_exception_handlers

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.LOG_FORMAT == "json" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Counter(
    'active_connections_total',
    'Total active connections'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting ParSSH API server")

    # Startup
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Initialize Redis
        redis = await get_redis()
        logger.info("Redis initialized")

        logger.info("All services initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise

    yield

    # Shutdown
    try:
        await close_db()
        await close_redis()
        logger.info("All services shut down successfully")
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="ParSSH - Termius-like Multi-Platform SSH Manager API",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan
)

# Exception handlers
setup_exception_handlers(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Trusted hosts middleware
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Gzip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Request logging and metrics middleware."""
    start_time = time.time()

    # Generate request ID
    request_id = f"{int(time.time() * 1000)}-{id(request)}"

    # Log request
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    # Process request
    try:
        response = await call_next(request)

        # Calculate duration
        process_time = time.time() - start_time

        # Log response
        logger.info(
            "Request completed",
            request_id=request_id,
            status_code=response.status_code,
            process_time=round(process_time, 4)
        )

        # Update metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)

        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time, 4))

        return response

    except Exception as e:
        process_time = time.time() - start_time

        logger.error(
            "Request failed",
            request_id=request_id,
            error=str(e),
            process_time=round(process_time, 4)
        )

        # Update metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=500
        ).inc()

        raise


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Security headers middleware."""
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(hosts.router, prefix="/api/hosts", tags=["Hosts"])
app.include_router(groups.router, prefix="/api/groups", tags=["Groups"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = await check_database_health()
    redis_healthy = await check_redis_health()

    status = "healthy" if db_healthy and redis_healthy else "unhealthy"

    return {
        "status": status,
        "timestamp": time.time(),
        "version": settings.VERSION,
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy"
        }
    }


@app.get("/api/ready")
async def readiness_check():
    """Readiness check endpoint."""
    db_healthy = await check_database_health()
    redis_healthy = await check_redis_health()

    if not db_healthy or not redis_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not ready",
                "timestamp": time.time(),
                "services": {
                    "database": "ready" if db_healthy else "not ready",
                    "redis": "ready" if redis_healthy else "not ready"
                }
            }
        )

    return {
        "status": "ready",
        "timestamp": time.time()
    }


@app.get("/api/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.PROMETHEUS_ENABLED:
        return JSONResponse(
            status_code=404,
            content={"error": "Metrics not enabled"}
        )

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/api/info")
async def app_info():
    """Application information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "features": {
            "prometheus": settings.PROMETHEUS_ENABLED,
            "oauth": bool(settings.GOOGLE_CLIENT_ID or settings.GITHUB_CLIENT_ID),
            "email": bool(settings.SMTP_HOST),
            "csrf_protection": settings.CSRF_PROTECTION
        }
    }


async def check_database_health() -> bool:
    """Check database health."""
    try:
        from app.core.database import check_db_health
        return await check_db_health()
    except Exception:
        return False


async def check_redis_health() -> bool:
    """Check Redis health."""
    try:
        from app.core.database import check_redis_health
        return await check_redis_health()
    except Exception:
        return False


# Startup event handler (legacy)
@app.on_event("startup")
async def startup_event():
    """Legacy startup event handler."""
    logger.info("Startup event triggered")


# Shutdown event handler (legacy)
@app.on_event("shutdown")
async def shutdown_event():
    """Legacy shutdown event handler."""
    logger.info("Shutdown event triggered")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
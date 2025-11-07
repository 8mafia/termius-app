from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

logger = structlog.get_logger(__name__)


class ParSSHException(Exception):
    """Base exception for ParSSH application."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ParSSHException):
    """Validation error exception."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(ParSSHException):
    """Authentication error exception."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationError(ParSSHException):
    """Authorization error exception."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR"
        )


class NotFoundError(ParSSHException):
    """Resource not found error exception."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND"
        )


class ConflictError(ParSSHException):
    """Conflict error exception."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT"
        )


class RateLimitError(ParSSHException):
    """Rate limit error exception."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED"
        )


class DatabaseError(ParSSHException):
    """Database error exception."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR"
        )


class ExternalServiceError(ParSSHException):
    """External service error exception."""

    def __init__(self, message: str, service_name: str = "external service"):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service_name}
        )


class SSHConnectionError(ParSSHException):
    """SSH connection error exception."""

    def __init__(self, message: str = "SSH connection failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SSH_CONNECTION_ERROR"
        )


class EncryptionError(ParSSHException):
    """Encryption error exception."""

    def __init__(self, message: str = "Encryption/decryption failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ENCRYPTION_ERROR"
        )


async def parssh_exception_handler(request: Request, exc: ParSSHException) -> JSONResponse:
    """Handle ParSSH custom exceptions."""
    logger.error(
        "ParSSH exception",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": {}
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation exceptions."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(
        "Validation exception",
        errors=errors,
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"fields": errors}
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "details": {}
            }
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers for FastAPI application."""
    app.add_exception_handler(ParSSHException, parssh_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


# Error response utility functions
def create_error_response(
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code or f"HTTP_{status_code}",
                "message": message,
                "details": details or {}
            }
        }
    )


def create_success_response(
    data: Any,
    message: str = "Operation successful",
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """Create standardized success response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data
        }
    )


def create_paginated_response(
    data: list,
    total: int,
    page: int,
    size: int,
    message: str = "Data retrieved successfully"
) -> JSONResponse:
    """Create paginated response."""
    total_pages = (total + size - 1) // size

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": message,
            "data": data,
            "pagination": {
                "total": total,
                "page": page,
                "size": size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    )
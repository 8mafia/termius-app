from typing import Generator, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import structlog

from app.core.database import get_db, get_redis
from app.core.security import verify_token
from app.models.user import User
from app.utils.exceptions import AuthenticationError, AuthorizationError

logger = structlog.get_logger(__name__)

# HTTP Bearer scheme for token authentication
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    try:
        # Verify token
        token = credentials.credentials
        user_id = verify_token(token, "access")

        if user_id is None:
            raise AuthenticationError("Invalid authentication token")

        # Get user from database
        user = await User.get_by_id(db, user_id)
        if user is None:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        return user

    except AuthenticationError:
        raise
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise AuthenticationError("Authentication failed")


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise AuthenticationError("User account is disabled")
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current verified user."""
    if not current_user.is_verified:
        raise AuthenticationError("Email not verified")
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_verified_user)
) -> User:
    """Get current admin user."""
    if not current_user.is_admin:
        raise AuthorizationError("Admin access required")
    return current_user


async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if token is provided, otherwise return None."""
    try:
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]
        user_id = verify_token(token, "access")

        if user_id is None:
            return None

        # Get user from database
        user = await User.get_by_id(db, user_id)
        if user is None or not user.is_active:
            return None

        return user

    except Exception:
        return None


def get_redis_client() -> Generator[redis.Redis, None, None]:
    """Get Redis client."""
    import asyncio

    async def _get_redis():
        return await get_redis()

    # This is a synchronous dependency that returns an async Redis client
    # The actual async calls will be made in the route handlers
    class RedisDep:
        def __init__(self):
            self._redis = None

        async def get(self):
            if self._redis is None:
                self._redis = await get_redis()
            return self._redis

    return RedisDep()


class RateLimiter:
    """Rate limiter using Redis."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int = 60
    ) -> bool:
        """Check if request is allowed based on rate limit."""
        try:
            current = await self.redis.incr(key)
            if current == 1:
                await self.redis.expire(key, window)

            return current <= limit
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e))
            # Allow request if Redis is unavailable
            return True


async def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    redis_client = await get_redis()
    return RateLimiter(redis_client)


class PermissionChecker:
    """Permission checker for user authorization."""

    def __init__(self, required_permissions: list):
        self.required_permissions = required_permissions

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        """Check if user has required permissions."""
        # For now, admin users have all permissions
        if current_user.is_admin:
            return current_user

        # TODO: Implement proper permission system
        # For now, we'll use a simple permission check based on user properties

        user_permissions = []
        if current_user.is_verified:
            user_permissions.append("verified")
        if current_user.is_active:
            user_permissions.append("active")

        # Check if user has all required permissions
        for permission in self.required_permissions:
            if permission not in user_permissions:
                raise AuthorizationError(f"Permission required: {permission}")

        return current_user


def require_permissions(permissions: list):
    """Create dependency that requires specific permissions."""
    return PermissionChecker(permissions)


def get_client_ip(request: Request) -> str:
    """Get client IP address."""
    # Check for forwarded IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # Check for real IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to client IP
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Get user agent string."""
    return request.headers.get("User-Agent", "unknown")


async def get_pagination_params(
    page: int = 1,
    size: int = 20,
    max_size: int = 100
) -> dict:
    """Get and validate pagination parameters."""
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1"
        )

    if size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Size must be >= 1"
        )

    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Size must be <= {max_size}"
        )

    offset = (page - 1) * size

    return {
        "page": page,
        "size": size,
        "offset": offset,
        "limit": size
    }


def validate_json_content_type(request: Request) -> None:
    """Validate that request has JSON content type."""
    content_type = request.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Content-Type must be application/json"
        )


async def get_search_params(
    q: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc",
    allowed_sort_fields: list = None
) -> dict:
    """Get and validate search parameters."""
    if allowed_sort_fields is None:
        allowed_sort_fields = ["created_at", "updated_at", "name", "id"]

    if sort not in allowed_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field. Allowed fields: {', '.join(allowed_sort_fields)}"
        )

    if order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be 'asc' or 'desc'"
        )

    return {
        "query": q,
        "sort": sort,
        "order": order
    }
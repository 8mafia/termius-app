import asyncio
from typing import AsyncGenerator
import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Database engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
    poolclass=NullPool if settings.is_development else None,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database session error", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database."""
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")

        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")


# Redis connection
redis_client: redis.Redis = None


async def get_redis() -> redis.Redis:
    """Get Redis client."""
    global redis_client

    if redis_client is None:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={},
        )

        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established")

    return redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")


# Database health check
async def check_db_health() -> bool:
    """Check database health."""
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return False


# Redis health check
async def check_redis_health() -> bool:
    """Check Redis health."""
    try:
        redis = await get_redis()
        await redis.ping()
        return True
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return False


# Database utility functions
async def execute_raw_sql(query: str, params: dict = None) -> list:
    """Execute raw SQL query."""
    async with engine.begin() as conn:
        result = await conn.execute(query, params or {})
        return result.fetchall()


async def get_db_info() -> dict:
    """Get database information."""
    try:
        async with engine.begin() as conn:
            # Get PostgreSQL version
            version_result = await conn.execute("SELECT version()")
            version = version_result.scalar()

            # Get connection count
            conn_count_result = await conn.execute(
                "SELECT count(*) FROM pg_stat_activity"
            )
            conn_count = conn_count_result.scalar()

            # Get database size
            size_result = await conn.execute(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )
            db_size = size_result.scalar()

            return {
                "version": version,
                "connection_count": conn_count,
                "database_size": db_size,
                "status": "healthy"
            }
    except Exception as e:
        logger.error("Failed to get database info", error=str(e))
        return {
            "status": "error",
            "error": str(e)
        }


async def get_redis_info() -> dict:
    """Get Redis information."""
    try:
        redis = await get_redis()
        info = await redis.info()

        return {
            "version": info.get("redis_version"),
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "status": "healthy"
        }
    except Exception as e:
        logger.error("Failed to get Redis info", error=str(e))
        return {
            "status": "error",
            "error": str(e)
        }


# Connection pooling utilities
class DatabasePool:
    """Database connection pool manager."""

    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal

    async def get_connection(self):
        """Get database connection from pool."""
        return await self.engine.acquire()

    async def release_connection(self, connection):
        """Release connection back to pool."""
        await self.engine.release(connection)

    async def health_check(self) -> bool:
        """Check pool health."""
        return await check_db_health()


db_pool = DatabasePool()


# Transaction utilities
class TransactionManager:
    """Transaction manager for database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()


# Event listeners
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database connection pragmas."""
    if "sqlite" in settings.database_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL queries in development."""
    if settings.is_development:
        logger.debug("SQL Query", query=statement, params=parameters)


# Async context manager for database operations
class DatabaseContext:
    """Database context manager for async operations."""

    async def __aenter__(self):
        self.session = AsyncSessionLocal()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        else:
            await self.session.commit()
        await self.session.close()
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, JSON,
    Index, ForeignKey, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete

from app.core.database import Base


class Session(Base):
    """Session model for active terminal connections."""

    __tablename__ = "sessions"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=False)

    # Session identifiers
    session_token = Column(String(255), unique=True, nullable=False)
    websocket_id = Column(String(255), nullable=True)  # WebSocket connection ID

    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    is_shared = Column(Boolean, default=False, nullable=False)
    session_type = Column(String(20), default="terminal", nullable=False)  # terminal, sftp

    # Sharing settings
    shared_users = Column(ARRAY(String), default=[], nullable=False)  # List of user IDs
    permissions = Column(JSON, default=dict, nullable=False)  # User permission mapping

    # Terminal settings
    terminal_columns = Column(Integer, default=80, nullable=False)
    terminal_rows = Column(Integer, default=24, nullable=False)
    term_type = Column(String(50), default="xterm-256color", nullable=False)

    # Connection details
    ssh_session_id = Column(String(255), nullable=True)  # SSH Gateway session ID
    connection_info = Column(JSON, default=dict, nullable=False)

    # Activity tracking
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    # Session statistics
    bytes_sent = Column(Integer, default=0, nullable=False)
    bytes_received = Column(Integer, default=0, nullable=False)
    commands_executed = Column(Integer, default=0, nullable=False)

    # Session metadata
    client_info = Column(JSON, default=dict, nullable=False)  # Client browser info
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(Text, nullable=True)

    # Recording settings
    is_recording = Column(Boolean, default=False, nullable=False)
    recording_path = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    host = relationship("Host", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index('idx_sessions_user_id', 'user_id'),
        Index('idx_sessions_host_id', 'host_id'),
        Index('idx_sessions_token', 'session_token'),
        Index('idx_sessions_websocket', 'websocket_id'),
        Index('idx_sessions_active', 'is_active'),
        Index('idx_sessions_shared', 'is_shared'),
        Index('idx_sessions_started', 'started_at'),
        Index('idx_sessions_last_activity', 'last_activity'),
    )

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        user_id: str,
        host_id: str,
        session_token: str,
        **kwargs
    ) -> "Session":
        """Create a new session."""
        session = cls(
            user_id=user_id,
            host_id=host_id,
            session_token=session_token,
            **kwargs
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @classmethod
    async def get_by_id(cls, db: AsyncSession, session_id: str) -> Optional["Session"]:
        """Get session by ID."""
        result = await db.execute(
            select(cls).where(cls.id == session_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_token(cls, db: AsyncSession, token: str) -> Optional["Session"]:
        """Get session by token."""
        result = await db.execute(
            select(cls).where(cls.session_token == token)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_websocket_id(
        cls,
        db: AsyncSession,
        websocket_id: str
    ) -> Optional["Session"]:
        """Get session by WebSocket ID."""
        result = await db.execute(
            select(cls).where(cls.websocket_id == websocket_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_user_active_sessions(
        cls,
        db: AsyncSession,
        user_id: str,
        limit: int = 10
    ) -> List["Session"]:
        """Get user's active sessions."""
        result = await db.execute(
            select(cls)
            .where(
                and_(
                    cls.user_id == user_id,
                    cls.is_active == True
                )
            )
            .order_by(cls.last_activity.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @classmethod
    async def get_user_sessions(
        cls,
        db: AsyncSession,
        user_id: str,
        include_inactive: bool = False,
        offset: int = 0,
        limit: int = 20
    ) -> List["Session"]:
        """Get user's sessions with pagination."""
        query = select(cls).where(cls.user_id == user_id)

        if not include_inactive:
            query = query.where(cls.is_active == True)

        query = query.order_by(cls.last_activity.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_user_sessions_count(
        cls,
        db: AsyncSession,
        user_id: str,
        include_inactive: bool = False
    ) -> int:
        """Get count of user's sessions."""
        query = select(func.count(cls.id)).where(cls.user_id == user_id)

        if not include_inactive:
            query = query.where(cls.is_active == True)

        result = await db.execute(query)
        return result.scalar() or 0

    @classmethod
    async def get_shared_sessions(
        cls,
        db: AsyncSession,
        user_id: str
    ) -> List["Session"]:
        """Get sessions shared with user."""
        result = await db.execute(
            select(cls)
            .where(
                and_(
                    cls.is_shared == True,
                    cls.is_active == True,
                    cls.shared_users.contains([user_id])
                )
            )
            .order_by(cls.last_activity.desc())
        )
        return result.scalars().all()

    @classmethod
    async def cleanup_expired_sessions(
        cls,
        db: AsyncSession,
        expire_minutes: int = 60
    ) -> int:
        """Clean up expired sessions."""
        expire_time = datetime.utcnow() - timedelta(minutes=expire_minutes)

        result = await db.execute(
            update(cls)
            .where(
                and_(
                    cls.is_active == True,
                    cls.last_activity < expire_time
                )
            )
            .values(
                is_active=False,
                ended_at=datetime.utcnow()
            )
        )
        await db.commit()
        return result.rowcount

    async def update_activity(self, db: AsyncSession) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
        await db.commit()

    async def update_terminal_size(
        self,
        db: AsyncSession,
        columns: int,
        rows: int
    ) -> None:
        """Update terminal size."""
        self.terminal_columns = columns
        self.terminal_rows = rows
        self.last_activity = datetime.utcnow()
        await db.commit()

    async def update_connection_info(
        self,
        db: AsyncSession,
        info: Dict[str, Any]
    ) -> None:
        """Update connection info."""
        self.connection_info = {**(self.connection_info or {}), **info}
        self.last_activity = datetime.utcnow()
        await db.commit()

    async def set_websocket_id(
        self,
        db: AsyncSession,
        websocket_id: str
    ) -> None:
        """Set WebSocket connection ID."""
        self.websocket_id = websocket_id
        self.last_activity = datetime.utcnow()
        await db.commit()

    async def clear_websocket_id(self, db: AsyncSession) -> None:
        """Clear WebSocket connection ID."""
        self.websocket_id = None
        await db.commit()

    async def share_with_users(
        self,
        db: AsyncSession,
        user_ids: List[str],
        permissions: Dict[str, List[str]]
    ) -> None:
        """Share session with users."""
        self.is_shared = True
        self.shared_users = list(set(self.shared_users + user_ids))

        # Update permissions
        current_permissions = self.permissions or {}
        for user_id in user_ids:
            current_permissions[user_id] = permissions.get(user_id, ["read"])

        self.permissions = current_permissions
        await db.commit()

    async def revoke_access(self, db: AsyncSession, user_id: str) -> None:
        """Revoke user access to shared session."""
        if user_id in self.shared_users:
            self.shared_users.remove(user_id)
            if user_id in self.permissions:
                del self.permissions[user_id]

            # If no more shared users, disable sharing
            if not self.shared_users:
                self.is_shared = False
                self.permissions = {}

            await db.commit()

    async def update_stats(
        self,
        db: AsyncSession,
        bytes_sent: int = 0,
        bytes_received: int = 0,
        commands_executed: int = 0
    ) -> None:
        """Update session statistics."""
        self.bytes_sent += bytes_sent
        self.bytes_received += bytes_received
        self.commands_executed += commands_executed
        self.last_activity = datetime.utcnow()
        await db.commit()

    async def start_recording(self, db: AsyncSession, recording_path: str) -> None:
        """Start session recording."""
        self.is_recording = True
        self.recording_path = recording_path
        await db.commit()

    async def stop_recording(self, db: AsyncSession) -> None:
        """Stop session recording."""
        self.is_recording = False
        await db.commit()

    async def end_session(self, db: AsyncSession) -> None:
        """End session."""
        self.is_active = False
        self.ended_at = datetime.utcnow()
        self.websocket_id = None
        await db.commit()

    @property
    def duration_seconds(self) -> int:
        """Get session duration in seconds."""
        end_time = self.ended_at or datetime.utcnow()
        return int((end_time - self.started_at).total_seconds())

    @property
    def is_stale(self) -> bool:
        """Check if session is stale (no recent activity)."""
        stale_threshold = datetime.utcnow() - timedelta(minutes=30)
        return self.is_active and self.last_activity < stale_threshold

    @property
    def can_share(self) -> bool:
        """Check if session can be shared."""
        return self.is_active and self.session_type == "terminal"

    def has_user_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission."""
        # Owner has all permissions
        if str(self.user_id) == user_id:
            return True

        # Check shared user permissions
        user_permissions = self.permissions.get(user_id, [])
        return permission in user_permissions

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert session to dictionary."""
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "host_id": str(self.host_id),
            "session_token": self.session_token if include_sensitive else None,
            "websocket_id": self.websocket_id if include_sensitive else None,
            "is_active": self.is_active,
            "is_shared": self.is_shared,
            "session_type": self.session_type,
            "shared_users": self.shared_users,
            "permissions": self.permissions if include_sensitive else {},
            "terminal_columns": self.terminal_columns,
            "terminal_rows": self.terminal_rows,
            "term_type": self.term_type,
            "ssh_session_id": self.ssh_session_id if include_sensitive else None,
            "connection_info": self.connection_info if include_sensitive else {},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "commands_executed": self.commands_executed,
            "client_info": self.client_info,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "is_recording": self.is_recording,
            "duration_seconds": self.duration_seconds,
            "is_stale": self.is_stale,
            "can_share": self.can_share
        }

        if include_sensitive:
            data["recording_path"] = self.recording_path

        return data
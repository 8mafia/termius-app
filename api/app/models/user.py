import uuid
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, JSON,
    Index, Integer, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete

from app.core.database import Base
from app.core.security import get_password_hash, verify_password


class User(Base):
    """User model for authentication and user management."""

    __tablename__ = "users"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users

    # Profile fields
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Security fields
    salt = Column(String(255), nullable=False)  # Per-user salt for key derivation
    encryption_key = Column(Text, nullable=True)  # Encrypted user encryption key
    totp_secret = Column(String(32), nullable=True)  # TOTP secret for 2FA
    backup_codes = Column(ARRAY(String), nullable=True)  # Backup codes for 2FA

    # OAuth fields
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'github'
    oauth_id = Column(String(255), nullable=True)  # OAuth provider ID

    # Status fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Timestamp fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Settings
    settings = Column(JSON, default=dict, nullable=False)
    preferences = Column(JSON, default=dict, nullable=False)

    # Relationships
    hosts = relationship("Host", back_populates="user", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_oauth', 'oauth_provider', 'oauth_id'),
        Index('idx_users_active', 'is_active'),
        Index('idx_users_created', 'created_at'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        email: str,
        password: Optional[str] = None,
        full_name: Optional[str] = None,
        oauth_provider: Optional[str] = None,
        oauth_id: Optional[str] = None,
        is_admin: bool = False
    ) -> "User":
        """Create a new user."""
        import os

        user = cls(
            email=email.lower(),
            full_name=full_name,
            salt=secrets.token_urlsafe(32),
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            is_admin=is_admin
        )

        # Hash password if provided
        if password:
            user.password_hash = get_password_hash(password)

        await db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @classmethod
    async def get_by_id(cls, db: AsyncSession, user_id: str) -> Optional["User"]:
        """Get user by ID."""
        result = await db.execute(
            select(cls).where(cls.id == user_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_email(cls, db: AsyncSession, email: str) -> Optional["User"]:
        """Get user by email."""
        result = await db.execute(
            select(cls).where(cls.email == email.lower())
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_oauth(
        cls,
        db: AsyncSession,
        provider: str,
        oauth_id: str
    ) -> Optional["User"]:
        """Get user by OAuth provider and ID."""
        result = await db.execute(
            select(cls).where(
                and_(
                    cls.oauth_provider == provider,
                    cls.oauth_id == oauth_id
                )
            )
        )
        return result.scalar_one_or_none()

    @classmethod
    async def authenticate(
        cls,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional["User"]:
        """Authenticate user with email and password."""
        result = await db.execute(
            select(cls).where(
                and_(
                    cls.email == email.lower(),
                    cls.is_active == True
                )
            )
        )
        user = result.scalar_one_or_none()

        if user and user.password_hash and verify_password(password, user.password_hash):
            # Update last login
            await db.execute(
                update(cls)
                .where(cls.id == user.id)
                .values(last_login=datetime.utcnow())
            )
            await db.commit()
            return user

        return None

    async def update_password(self, db: AsyncSession, new_password: str) -> None:
        """Update user password."""
        self.password_hash = get_password_hash(new_password)
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def verify_password(self, password: str) -> bool:
        """Verify password against hash."""
        if not self.password_hash:
            return False
        return verify_password(password, self.password_hash)

    async def update_last_login(self, db: AsyncSession) -> None:
        """Update last login timestamp."""
        await db.execute(
            update(User)
            .where(User.id == self.id)
            .values(last_login=datetime.utcnow())
        )
        await db.commit()

    async def update_settings(self, db: AsyncSession, settings: Dict[str, Any]) -> None:
        """Update user settings."""
        self.settings = {**(self.settings or {}), **settings}
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def update_preferences(self, db: AsyncSession, preferences: Dict[str, Any]) -> None:
        """Update user preferences."""
        self.preferences = {**(self.preferences or {}), **preferences}
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def enable_2fa(self, db: AsyncSession, totp_secret: str, backup_codes: List[str]) -> None:
        """Enable 2FA for user."""
        self.totp_secret = totp_secret
        self.backup_codes = backup_codes
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def disable_2fa(self, db: AsyncSession) -> None:
        """Disable 2FA for user."""
        self.totp_secret = None
        self.backup_codes = None
        self.updated_at = datetime.utcnow()
        await db.commit()

    @property
    def has_2fa(self) -> bool:
        """Check if user has 2FA enabled."""
        return self.totp_secret is not None

    @property
    def is_oauth_user(self) -> bool:
        """Check if user is OAuth user."""
        return self.oauth_provider is not None

    async def get_active_sessions_count(self, db: AsyncSession) -> int:
        """Get count of active sessions."""
        from .session import Session

        result = await db.execute(
            select(func.count(Session.id))
            .where(
                and_(
                    Session.user_id == self.id,
                    Session.is_active == True
                )
            )
        )
        return result.scalar() or 0

    async def get_hosts_count(self, db: AsyncSession) -> int:
        """Get count of user's hosts."""
        from .host import Host

        result = await db.execute(
            select(func.count(Host.id))
            .where(Host.user_id == self.id)
        )
        return result.scalar() or 0

    async def get_recent_audit_logs(
        self,
        db: AsyncSession,
        limit: int = 10
    ) -> List["AuditLog"]:
        """Get recent audit logs for user."""
        from .audit_log import AuditLog

        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == self.id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def soft_delete(self, db: AsyncSession) -> None:
        """Soft delete user (deactivate)."""
        self.is_active = False
        self.email = f"deleted_{self.id}@deleted.com"
        self.updated_at = datetime.utcnow()
        await db.commit()

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user to dictionary."""
        data = {
            "id": str(self.id),
            "email": self.email,
            "full_name": self.full_name,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_admin": self.is_admin,
            "has_2fa": self.has_2fa,
            "is_oauth_user": self.is_oauth_user,
            "oauth_provider": self.oauth_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "settings": self.settings or {},
            "preferences": self.preferences or {}
        }

        if include_sensitive:
            data.update({
                "salt": self.salt,
                "encryption_key": self.encryption_key,
                "totp_secret": self.totp_secret,
                "backup_codes": self.backup_codes
            })

        return data

    async def get_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Get user statistics."""
        hosts_count = await self.get_hosts_count(db)
        sessions_count = await self.get_active_sessions_count(db)

        return {
            "hosts_count": hosts_count,
            "active_sessions_count": sessions_count,
            "account_age_days": (datetime.utcnow() - self.created_at).days if self.created_at else 0
        }
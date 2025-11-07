import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON,
    Index, ForeignKey, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete

from app.core.database import Base


class Host(Base):
    """Host model for SSH connection configurations."""

    __tablename__ = "hosts"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Connection details
    name = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=False)
    port = Column(Integer, default=22, nullable=False)
    username = Column(String(255), nullable=False)

    # Encrypted credentials
    password_encrypted = Column(Text, nullable=True)  # Encrypted password
    private_key_encrypted = Column(Text, nullable=True)  # Encrypted private key
    private_key_passphrase_encrypted = Column(Text, nullable=True)  # Encrypted passphrase

    # Connection settings
    connection_type = Column(String(20), default="password", nullable=False)  # password, key, agent
    jump_host_id = Column(UUID(as_uuid=True), ForeignKey("hosts.id"), nullable=True)

    # Authentication settings
    auth_method = Column(String(20), default="password", nullable=False)  # password, key, agent
    use_agent = Column(Boolean, default=False, nullable=False)
    agent_forwarding = Column(Boolean, default=False, nullable=False)

    # Terminal settings
    term_type = Column(String(50), default="xterm-256color", nullable=False)
    terminal_columns = Column(Integer, default=80, nullable=False)
    terminal_rows = Column(Integer, default=24, nullable=False)

    # Organization
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True)
    tags = Column(ARRAY(String), default=[], nullable=False)
    is_favorite = Column(Boolean, default=False, nullable=False)

    # Connection options
    connection_timeout = Column(Integer, default=30, nullable=False)
    keep_alive = Column(Boolean, default=True, nullable=False)
    compression = Column(Boolean, default=False, nullable=False)

    # Port forwarding
    port_forwardings = Column(JSON, default=list, nullable=False)  # List of port forwarding rules

    # SSH options
    ssh_options = Column(JSON, default=dict, nullable=False)  # Custom SSH options

    # Metadata
    notes = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code for display

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_connected_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    connection_status = Column(String(20), default="unknown", nullable=False)  # unknown, online, offline, error

    # Relationships
    user = relationship("User", back_populates="hosts")
    group = relationship("Group", back_populates="hosts")
    jump_host = relationship("Host", remote_side=[id])
    sessions = relationship("Session", back_populates="host", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_hosts_user_id', 'user_id'),
        Index('idx_hosts_group_id', 'group_id'),
        Index('idx_hosts_name', 'name'),
        Index('idx_hosts_hostname', 'hostname'),
        Index('idx_hosts_tags', 'tags', postgresql_using='gin'),
        Index('idx_hosts_favorite', 'is_favorite'),
        Index('idx_hosts_active', 'is_active'),
        Index('idx_hosts_created', 'created_at'),
        Index('idx_hosts_last_connected', 'last_connected_at'),
    )

    def __repr__(self):
        return f"<Host(id={self.id}, name={self.name}, hostname={self.hostname})>"

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        user_id: str,
        name: str,
        hostname: str,
        username: str,
        port: int = 22,
        **kwargs
    ) -> "Host":
        """Create a new host."""
        host = cls(
            user_id=user_id,
            name=name,
            hostname=hostname,
            username=username,
            port=port,
            **kwargs
        )

        db.add(host)
        await db.commit()
        await db.refresh(host)
        return host

    @classmethod
    async def get_by_id(cls, db: AsyncSession, host_id: str) -> Optional["Host"]:
        """Get host by ID."""
        result = await db.execute(
            select(cls).where(cls.id == host_id)
        )
        return result.scalar_one_or_none()

    @classmethod
    async def get_user_hosts(
        cls,
        db: AsyncSession,
        user_id: str,
        group_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_favorite: Optional[bool] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 20
    ) -> List["Host"]:
        """Get user's hosts with optional filtering."""
        query = select(cls).where(cls.user_id == user_id)

        # Apply filters
        if group_id:
            query = query.where(cls.group_id == group_id)

        if is_favorite is not None:
            query = query.where(cls.is_favorite == is_favorite)

        if tags:
            query = query.where(cls.tags.overlap(tags))

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    cls.name.ilike(search_term),
                    cls.hostname.ilike(search_term),
                    cls.username.ilike(search_term),
                    cls.notes.ilike(search_term)
                )
            )

        # Order and limit
        query = query.order_by(cls.name.asc()).offset(offset).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_user_hosts_count(
        cls,
        db: AsyncSession,
        user_id: str,
        group_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_favorite: Optional[bool] = None,
        search: Optional[str] = None
    ) -> int:
        """Get count of user's hosts with optional filtering."""
        query = select(func.count(cls.id)).where(cls.user_id == user_id)

        # Apply filters
        if group_id:
            query = query.where(cls.group_id == group_id)

        if is_favorite is not None:
            query = query.where(cls.is_favorite == is_favorite)

        if tags:
            query = query.where(cls.tags.overlap(tags))

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    cls.name.ilike(search_term),
                    cls.hostname.ilike(search_term),
                    cls.username.ilike(search_term),
                    cls.notes.ilike(search_term)
                )
            )

        result = await db.execute(query)
        return result.scalar() or 0

    @classmethod
    async def get_favorites(cls, db: AsyncSession, user_id: str) -> List["Host"]:
        """Get user's favorite hosts."""
        result = await db.execute(
            select(cls)
            .where(
                and_(
                    cls.user_id == user_id,
                    cls.is_favorite == True,
                    cls.is_active == True
                )
            )
            .order_by(cls.name.asc())
        )
        return result.scalars().all()

    @classmethod
    async def get_recently_connected(
        cls,
        db: AsyncSession,
        user_id: str,
        limit: int = 10
    ) -> List["Host"]:
        """Get recently connected hosts."""
        result = await db.execute(
            select(cls)
            .where(
                and_(
                    cls.user_id == user_id,
                    cls.last_connected_at.isnot(None),
                    cls.is_active == True
                )
            )
            .order_by(cls.last_connected_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update(self, db: AsyncSession, **kwargs) -> None:
        """Update host details."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def update_connection_status(
        self,
        db: AsyncSession,
        status: str
    ) -> None:
        """Update connection status."""
        self.connection_status = status
        if status == "online":
            self.last_connected_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def set_favorite(self, db: AsyncSession, is_favorite: bool) -> None:
        """Set host as favorite."""
        self.is_favorite = is_favorite
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def add_tags(self, db: AsyncSession, tags: List[str]) -> None:
        """Add tags to host."""
        existing_tags = set(self.tags or [])
        new_tags = existing_tags.union(set(tags))
        self.tags = list(new_tags)
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def remove_tags(self, db: AsyncSession, tags: List[str]) -> None:
        """Remove tags from host."""
        existing_tags = set(self.tags or [])
        remaining_tags = existing_tags - set(tags)
        self.tags = list(remaining_tags)
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def add_port_forwarding(
        self,
        db: AsyncSession,
        local_port: int,
        remote_host: str,
        remote_port: int,
        forward_type: str = "local"
    ) -> None:
        """Add port forwarding rule."""
        forwardings = self.port_forwardings or []
        forwardings.append({
            "local_port": local_port,
            "remote_host": remote_host,
            "remote_port": remote_port,
            "type": forward_type,
            "created_at": datetime.utcnow().isoformat()
        })
        self.port_forwardings = forwardings
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def remove_port_forwarding(self, db: AsyncSession, local_port: int) -> None:
        """Remove port forwarding rule."""
        forwardings = self.port_forwardings or []
        forwardings = [f for f in forwardings if f["local_port"] != local_port]
        self.port_forwardings = forwardings
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def soft_delete(self, db: AsyncSession) -> None:
        """Soft delete host."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def restore(self, db: AsyncSession) -> None:
        """Restore soft deleted host."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
        await db.commit()

    async def delete(self, db: AsyncSession) -> None:
        """Permanently delete host."""
        await db.delete(self)
        await db.commit()

    @property
    def display_name(self) -> str:
        """Get display name for host."""
        return f"{self.name} ({self.username}@{self.hostname}:{self.port})"

    @property
    def connection_string(self) -> str:
        """Get SSH connection string."""
        return f"{self.username}@{self.hostname}:{self.port}"

    def to_dict(self, include_credentials: bool = False) -> Dict[str, Any]:
        """Convert host to dictionary."""
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "hostname": self.hostname,
            "port": self.port,
            "username": self.username,
            "connection_type": self.connection_type,
            "auth_method": self.auth_method,
            "use_agent": self.use_agent,
            "agent_forwarding": self.agent_forwarding,
            "term_type": self.term_type,
            "terminal_columns": self.terminal_columns,
            "terminal_rows": self.terminal_rows,
            "group_id": str(self.group_id) if self.group_id else None,
            "tags": self.tags or [],
            "is_favorite": self.is_favorite,
            "connection_timeout": self.connection_timeout,
            "keep_alive": self.keep_alive,
            "compression": self.compression,
            "port_forwardings": self.port_forwardings or [],
            "ssh_options": self.ssh_options or {},
            "notes": self.notes,
            "color": self.color,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
            "is_active": self.is_active,
            "connection_status": self.connection_status,
            "jump_host_id": str(self.jump_host_id) if self.jump_host_id else None
        }

        if include_credentials:
            data.update({
                "password_encrypted": self.password_encrypted,
                "private_key_encrypted": self.private_key_encrypted,
                "private_key_passphrase_encrypted": self.private_key_passphrase_encrypted
            })

        return data

    async def test_connection(self, db: AsyncSession) -> Dict[str, Any]:
        """Test SSH connection to host."""
        # This would integrate with the SSH Gateway service
        # For now, return a mock response
        return {
            "host_id": str(self.id),
            "status": "success",
            "message": "Connection test successful",
            "latency_ms": 45,
            "tested_at": datetime.utcnow().isoformat()
        }
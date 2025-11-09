import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, Text, JSON,
    Index, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc

from app.core.database import Base


class AuditLog(Base):
    """Audit log model for security and usage tracking."""

    __tablename__ = "audit_logs"

    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Event details
    action = Column(String(100), nullable=False)  # login, logout, create_host, etc.
    resource_type = Column(String(50), nullable=False)  # user, host, session, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=True)  # ID of affected resource
    resource_name = Column(String(255), nullable=True)  # Human-readable resource name

    # Event details
    description = Column(Text, nullable=True)  # Human-readable description
    details = Column(JSON, default=dict, nullable=False)  # Additional event details

    # Request information
    ip_address = Column(INET, nullable=True)  # Client IP address
    user_agent = Column(Text, nullable=True)  # User agent string
    endpoint = Column(String(255), nullable=True)  # API endpoint
    method = Column(String(10), nullable=True)  # HTTP method

    # Status and result
    status = Column(String(20), default="success", nullable=False)  # success, failure, warning
    error_message = Column(Text, nullable=True)  # Error message if failed
    result = Column(JSON, default=dict, nullable=False)  # Event result

    # Security context
    session_id = Column(UUID(as_uuid=True), nullable=True)  # Session ID if applicable
    authentication_method = Column(String(50), nullable=True)  # password, oauth, token
    mfa_verified = Column(Boolean, default=False, nullable=False)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    duration_ms = Column(Integer, nullable=True)  # Event duration in milliseconds

    # Risk assessment
    risk_level = Column(String(20), default="low", nullable=False)  # low, medium, high, critical
    tags = Column(JSON, default=list, nullable=False)  # Event tags for filtering

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_user_id', 'user_id'),
        Index('idx_audit_logs_action', 'action'),
        Index('idx_audit_logs_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_logs_status', 'status'),
        Index('idx_audit_logs_risk', 'risk_level'),
        Index('idx_audit_logs_created', 'created_at'),
        Index('idx_audit_logs_ip', 'ip_address'),
        Index('idx_audit_logs_session', 'session_id'),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"

    @classmethod
    async def create(
        cls,
        db: AsyncSession,
        action: str,
        resource_type: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        authentication_method: Optional[str] = None,
        mfa_verified: bool = False,
        duration_ms: Optional[int] = None,
        risk_level: str = "low",
        tags: Optional[List[str]] = None
    ) -> "AuditLog":
        """Create a new audit log entry."""
        audit_log = cls(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            description=description,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            status=status,
            error_message=error_message,
            result=result or {},
            session_id=session_id,
            authentication_method=authentication_method,
            mfa_verified=mfa_verified,
            duration_ms=duration_ms,
            risk_level=risk_level,
            tags=tags or []
        )

        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        return audit_log

    @classmethod
    async def log_authentication_event(
        cls,
        db: AsyncSession,
        action: str,  # login, logout, login_failed, etc.
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        authentication_method: Optional[str] = None,
        mfa_verified: bool = False
    ) -> "AuditLog":
        """Log authentication event."""
        resource_name = email if email else f"User {user_id}"

        # Determine risk level based on event
        risk_level = "low"
        if action == "login_failed":
            risk_level = "medium"
        elif action == "password_reset" or action == "mfa_disabled":
            risk_level = "high"

        return await cls.create(
            db=db,
            action=action,
            resource_type="user",
            user_id=user_id,
            resource_name=resource_name,
            description=f"Authentication event: {action}",
            details={
                "email": email,
                "authentication_method": authentication_method
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            authentication_method=authentication_method,
            mfa_verified=mfa_verified,
            risk_level=risk_level,
            tags=["authentication"]
        )

    @classmethod
    async def log_host_event(
        cls,
        db: AsyncSession,
        action: str,  # create_host, update_host, delete_host, connect_host, etc.
        user_id: str,
        host_id: str,
        host_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> "AuditLog":
        """Log host-related event."""
        risk_level = "low"
        if action in ["delete_host", "export_hosts"]:
            risk_level = "medium"
        elif action == "connect_failed":
            risk_level = "medium"

        return await cls.create(
            db=db,
            action=action,
            resource_type="host",
            user_id=user_id,
            resource_id=host_id,
            resource_name=host_name,
            description=f"Host event: {action}",
            details={"host_id": host_id},
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
            risk_level=risk_level,
            tags=["host"]
        )

    @classmethod
    async def log_session_event(
        cls,
        db: AsyncSession,
        action: str,  # start_session, end_session, share_session, etc.
        user_id: str,
        session_id: str,
        host_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        duration_ms: Optional[int] = None
    ) -> "AuditLog":
        """Log session-related event."""
        risk_level = "low"
        if action == "share_session":
            risk_level = "medium"

        return await cls.create(
            db=db,
            action=action,
            resource_type="session",
            user_id=user_id,
            resource_id=session_id,
            resource_name=f"Session for {host_name}" if host_name else f"Session {session_id}",
            description=f"Session event: {action}",
            details={"session_id": session_id},
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            duration_ms=duration_ms,
            risk_level=risk_level,
            tags=["session"]
        )

    @classmethod
    async def log_security_event(
        cls,
        db: AsyncSession,
        action: str,  # privilege_escalation, suspicious_activity, etc.
        user_id: Optional[str] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        risk_level: str = "high"
    ) -> "AuditLog":
        """Log security-related event."""
        return await cls.create(
            db=db,
            action=action,
            resource_type="security",
            user_id=user_id,
            description=description or f"Security event: {action}",
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            risk_level=risk_level,
            tags=["security"]
        )

    @classmethod
    async def get_user_logs(
        cls,
        db: AsyncSession,
        user_id: str,
        actions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List["AuditLog"]:
        """Get user's audit logs."""
        query = select(cls).where(cls.user_id == user_id)

        if actions:
            query = query.where(cls.action.in_(actions))

        if resource_types:
            query = query.where(cls.resource_type.in_(resource_types))

        query = query.order_by(desc(cls.created_at)).offset(offset).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_user_logs_count(
        cls,
        db: AsyncSession,
        user_id: str,
        actions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None
    ) -> int:
        """Get count of user's audit logs."""
        query = select(func.count(cls.id)).where(cls.user_id == user_id)

        if actions:
            query = query.where(cls.action.in_(actions))

        if resource_types:
            query = query.where(cls.resource_type.in_(resource_types))

        result = await db.execute(query)
        return result.scalar() or 0

    @classmethod
    async def search_logs(
        cls,
        db: AsyncSession,
        search_term: str,
        limit: int = 50,
        offset: int = 0
    ) -> List["AuditLog"]:
        """Search audit logs."""
        search_pattern = f"%{search_term}%"
        result = await db.execute(
            select(cls)
            .where(
                or_(
                    cls.action.ilike(search_pattern),
                    cls.resource_type.ilike(search_pattern),
                    cls.resource_name.ilike(search_pattern),
                    cls.description.ilike(search_pattern),
                    cls.ip_address.ilike(search_pattern)
                )
            )
            .order_by(desc(cls.created_at))
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    @classmethod
    async def get_failed_login_attempts(
        cls,
        db: AsyncSession,
        hours: int = 24,
        ip_address: Optional[str] = None
    ) -> List["AuditLog"]:
        """Get failed login attempts."""
        from datetime import datetime, timedelta

        time_threshold = datetime.utcnow() - timedelta(hours=hours)

        query = select(cls).where(
            and_(
                cls.action == "login_failed",
                cls.created_at >= time_threshold
            )
        )

        if ip_address:
            query = query.where(cls.ip_address == ip_address)

        query = query.order_by(desc(cls.created_at))

        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def get_security_events(
        cls,
        db: AsyncSession,
        risk_levels: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List["AuditLog"]:
        """Get security events."""
        query = select(cls).where(cls.resource_type == "security")

        if risk_levels:
            query = query.where(cls.risk_level.in_(risk_levels))
        else:
            # Default to medium and above
            query = query.where(cls.risk_level.in_(["medium", "high", "critical"]))

        query = query.order_by(desc(cls.created_at)).offset(offset).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @classmethod
    async def cleanup_old_logs(
        cls,
        db: AsyncSession,
        days: int = 90
    ) -> int:
        """Clean up old audit logs."""
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Keep high and critical risk level logs longer
        from sqlalchemy import delete

        # Delete low and medium risk logs older than cutoff
        stmt = delete(cls).where(
            and_(
                cls.created_at < cutoff_date,
                cls.risk_level.in_(["low", "medium"])
            )
        )

        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    @property
    def is_recent(self) -> bool:
        """Check if log entry is recent (last 24 hours)."""
        from datetime import datetime, timedelta

        recent_threshold = datetime.utcnow() - timedelta(hours=24)
        return self.created_at >= recent_threshold

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "resource_name": self.resource_name,
            "description": self.description,
            "details": self.details or {},
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "endpoint": self.endpoint,
            "method": self.method,
            "status": self.status,
            "error_message": self.error_message,
            "result": self.result or {},
            "session_id": str(self.session_id) if self.session_id else None,
            "authentication_method": self.authentication_method,
            "mfa_verified": self.mfa_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "duration_ms": self.duration_ms,
            "risk_level": self.risk_level,
            "tags": self.tags or [],
            "is_recent": self.is_recent
        }
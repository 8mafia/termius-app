from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SessionBase(BaseModel):
    """Base session schema."""
    host_id: str = Field(..., description="Host ID")
    terminal_columns: int = Field(default=80, description="Terminal columns")
    terminal_rows: int = Field(default=24, description="Terminal rows")
    term_type: str = Field(default="xterm-256color", description="Terminal type")


class SessionCreate(SessionBase):
    """Session creation schema."""
    session_type: str = Field(default="terminal", description="Session type")


class SessionShare(BaseModel):
    """Session sharing schema."""
    user_ids: List[str] = Field(..., description="User IDs to share with")
    permissions: Dict[str, List[str]] = Field(default_factory=dict, description="User permissions")


class SessionResponse(SessionBase):
    """Session response schema."""
    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    session_token: Optional[str] = Field(None, description="Session token")
    websocket_id: Optional[str] = Field(None, description="WebSocket ID")
    is_active: bool = Field(default=True, description="Is active")
    is_shared: bool = Field(default=False, description="Is shared")
    session_type: str = Field(default="terminal", description="Session type")
    shared_users: List[str] = Field(default_factory=list, description="Shared users")
    permissions: Dict[str, List[str]] = Field(default_factory=dict, description="User permissions")
    ssh_session_id: Optional[str] = Field(None, description="SSH session ID")
    connection_info: Dict[str, Any] = Field(default_factory=dict, description="Connection info")
    started_at: Optional[str] = Field(None, description="Start time")
    last_activity: Optional[str] = Field(None, description="Last activity")
    ended_at: Optional[str] = Field(None, description="End time")
    bytes_sent: int = Field(default=0, description="Bytes sent")
    bytes_received: int = Field(default=0, description="Bytes received")
    commands_executed: int = Field(default=0, description="Commands executed")
    client_info: Dict[str, Any] = Field(default_factory=dict, description="Client info")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    is_recording: bool = Field(default=False, description="Is recording")
    duration_seconds: int = Field(default=0, description="Duration in seconds")
    is_stale: bool = Field(default=False, description="Is stale")
    can_share: bool = Field(default=False, description="Can be shared")

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        return cls(
            id=str(obj.id),
            user_id=str(obj.user_id),
            host_id=str(obj.host_id),
            session_token=obj.session_token,
            websocket_id=obj.websocket_id,
            is_active=obj.is_active,
            is_shared=obj.is_shared,
            session_type=obj.session_type,
            shared_users=obj.shared_users or [],
            permissions=obj.permissions or {},
            terminal_columns=obj.terminal_columns,
            terminal_rows=obj.terminal_rows,
            term_type=obj.term_type,
            ssh_session_id=obj.ssh_session_id,
            connection_info=obj.connection_info or {},
            started_at=obj.started_at.isoformat() if obj.started_at else None,
            last_activity=obj.last_activity.isoformat() if obj.last_activity else None,
            ended_at=obj.ended_at.isoformat() if obj.ended_at else None,
            bytes_sent=obj.bytes_sent,
            bytes_received=obj.bytes_received,
            commands_executed=obj.commands_executed,
            client_info=obj.client_info or {},
            ip_address=str(obj.ip_address) if obj.ip_address else None,
            user_agent=obj.user_agent,
            is_recording=obj.is_recording,
            duration_seconds=obj.duration_seconds,
            is_stale=obj.is_stale,
            can_share=obj.can_share
        )


class SessionStats(BaseModel):
    """Session statistics."""
    total_sessions: int = Field(default=0, description="Total sessions")
    active_sessions: int = Field(default=0, description="Active sessions")
    shared_sessions: int = Field(default=0, description="Shared sessions")
    total_duration_seconds: int = Field(default=0, description="Total duration")
    total_bytes_sent: int = Field(default=0, description="Total bytes sent")
    total_bytes_received: int = Field(default=0, description="Total bytes received")
    total_commands: int = Field(default=0, description="Total commands")
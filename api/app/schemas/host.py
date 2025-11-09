from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HostBase(BaseModel):
    """Base host schema."""
    name: str = Field(..., description="Host name")
    hostname: str = Field(..., description="Hostname or IP address")
    port: int = Field(default=22, description="SSH port")
    username: str = Field(..., description="SSH username")


class HostCreate(HostBase):
    """Host creation schema."""
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="Private key content")
    private_key_passphrase: Optional[str] = Field(None, description="Private key passphrase")
    connection_type: str = Field(default="password", description="Connection type")
    auth_method: str = Field(default="password", description="Authentication method")
    group_id: Optional[str] = Field(None, description="Group ID")
    tags: List[str] = Field(default_factory=list, description="Tags")
    notes: Optional[str] = Field(None, description="Notes")
    color: Optional[str] = Field(None, description="Display color")


class HostUpdate(BaseModel):
    """Host update schema."""
    name: Optional[str] = Field(None, description="Host name")
    hostname: Optional[str] = Field(None, description="Hostname or IP address")
    port: Optional[int] = Field(None, description="SSH port")
    username: Optional[str] = Field(None, description="SSH username")
    password: Optional[str] = Field(None, description="SSH password")
    private_key: Optional[str] = Field(None, description="Private key content")
    private_key_passphrase: Optional[str] = Field(None, description="Private key passphrase")
    connection_type: Optional[str] = Field(None, description="Connection type")
    auth_method: Optional[str] = Field(None, description="Authentication method")
    group_id: Optional[str] = Field(None, description="Group ID")
    tags: Optional[List[str]] = Field(None, description="Tags")
    notes: Optional[str] = Field(None, description="Notes")
    color: Optional[str] = Field(None, description="Display color")
    is_favorite: Optional[bool] = Field(None, description="Is favorite")


class HostResponse(HostBase):
    """Host response schema."""
    id: str = Field(..., description="Host ID")
    user_id: str = Field(..., description="User ID")
    connection_type: str = Field(..., description="Connection type")
    auth_method: str = Field(..., description="Authentication method")
    use_agent: bool = Field(default=False, description="Use SSH agent")
    agent_forwarding: bool = Field(default=False, description="SSH agent forwarding")
    term_type: str = Field(default="xterm-256color", description="Terminal type")
    terminal_columns: int = Field(default=80, description="Terminal columns")
    terminal_rows: int = Field(default=24, description="Terminal rows")
    group_id: Optional[str] = Field(None, description="Group ID")
    tags: List[str] = Field(default_factory=list, description="Tags")
    is_favorite: bool = Field(default=False, description="Is favorite")
    connection_timeout: int = Field(default=30, description="Connection timeout")
    keep_alive: bool = Field(default=True, description="Keep alive")
    compression: bool = Field(default=False, description="Compression")
    port_forwardings: List[Dict[str, Any]] = Field(default_factory=list, description="Port forwarding rules")
    ssh_options: Dict[str, Any] = Field(default_factory=dict, description="SSH options")
    notes: Optional[str] = Field(None, description="Notes")
    color: Optional[str] = Field(None, description="Display color")
    created_at: Optional[str] = Field(None, description="Creation time")
    updated_at: Optional[str] = Field(None, description="Last update time")
    last_connected_at: Optional[str] = Field(None, description="Last connection time")
    is_active: bool = Field(default=True, description="Is active")
    connection_status: str = Field(default="unknown", description="Connection status")
    jump_host_id: Optional[str] = Field(None, description="Jump host ID")

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        return cls(
            id=str(obj.id),
            user_id=str(obj.user_id),
            name=obj.name,
            hostname=obj.hostname,
            port=obj.port,
            username=obj.username,
            connection_type=obj.connection_type,
            auth_method=obj.auth_method,
            use_agent=obj.use_agent,
            agent_forwarding=obj.agent_forwarding,
            term_type=obj.term_type,
            terminal_columns=obj.terminal_columns,
            terminal_rows=obj.terminal_rows,
            group_id=str(obj.group_id) if obj.group_id else None,
            tags=obj.tags or [],
            is_favorite=obj.is_favorite,
            connection_timeout=obj.connection_timeout,
            keep_alive=obj.keep_alive,
            compression=obj.compression,
            port_forwardings=obj.port_forwardings or [],
            ssh_options=obj.ssh_options or {},
            notes=obj.notes,
            color=obj.color,
            created_at=obj.created_at.isoformat() if obj.created_at else None,
            updated_at=obj.updated_at.isoformat() if obj.updated_at else None,
            last_connected_at=obj.last_connected_at.isoformat() if obj.last_connected_at else None,
            is_active=obj.is_active,
            connection_status=obj.connection_status,
            jump_host_id=str(obj.jump_host_id) if obj.jump_host_id else None
        )


class HostConnectionTest(BaseModel):
    """Host connection test result."""
    host_id: str = Field(..., description="Host ID")
    status: str = Field(..., description="Connection status")
    message: str = Field(..., description="Status message")
    latency_ms: Optional[int] = Field(None, description="Latency in milliseconds")
    tested_at: str = Field(..., description="Test timestamp")


class HostConnectionSettings(BaseModel):
    """Host connection settings."""
    connection_timeout: int = Field(default=30, description="Connection timeout")
    keep_alive: bool = Field(default=True, description="Keep alive")
    compression: bool = Field(default=False, description="Compression")
    term_type: str = Field(default="xterm-256color", description="Terminal type")
    terminal_columns: int = Field(default=80, description="Terminal columns")
    terminal_rows: int = Field(default=24, description="Terminal rows")


class HostPortForwarding(BaseModel):
    """Host port forwarding rule."""
    local_port: int = Field(..., description="Local port")
    remote_host: str = Field(..., description="Remote host")
    remote_port: int = Field(..., description="Remote port")
    forward_type: str = Field(default="local", description="Forward type")
    created_at: str = Field(..., description="Creation time")
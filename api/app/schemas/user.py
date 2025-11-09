from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr = Field(..., description="Email address")
    full_name: Optional[str] = Field(None, description="Full name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8, description="Password")


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: Optional[str] = Field(None, description="Full name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    settings: Optional[Dict[str, Any]] = Field(None, description="User settings")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class UserResponse(UserBase):
    """User response schema."""
    id: str = Field(..., description="User ID")
    is_active: bool = Field(..., description="Is user active")
    is_verified: bool = Field(..., description="Is user verified")
    is_admin: bool = Field(..., description="Is user admin")
    has_2fa: bool = Field(..., description="Has 2FA enabled")
    is_oauth_user: bool = Field(..., description="Is OAuth user")
    oauth_provider: Optional[str] = Field(None, description="OAuth provider")
    created_at: Optional[str] = Field(None, description="Creation time")
    updated_at: Optional[str] = Field(None, description="Last update time")
    last_login: Optional[str] = Field(None, description="Last login time")
    settings: Dict[str, Any] = Field(default_factory=dict, description="User settings")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Create from ORM object."""
        return cls(
            id=str(obj.id),
            email=obj.email,
            full_name=obj.full_name,
            avatar_url=obj.avatar_url,
            is_active=obj.is_active,
            is_verified=obj.is_verified,
            is_admin=obj.is_admin,
            has_2fa=obj.has_2fa,
            is_oauth_user=obj.is_oauth_user,
            oauth_provider=obj.oauth_provider,
            created_at=obj.created_at.isoformat() if obj.created_at else None,
            updated_at=obj.updated_at.isoformat() if obj.updated_at else None,
            last_login=obj.last_login.isoformat() if obj.last_login else None,
            settings=obj.settings or {},
            preferences=obj.preferences or {}
        )


class UserProfile(UserResponse):
    """Extended user profile."""
    stats: Dict[str, Any] = Field(default_factory=dict, description="User statistics")


class UserSettings(BaseModel):
    """User settings schema."""
    theme: str = Field(default="light", description="Theme preference")
    language: str = Field(default="en", description="Language preference")
    timezone: str = Field(default="UTC", description="Timezone")
    notifications: Dict[str, bool] = Field(default_factory=dict, description="Notification settings")
    security: Dict[str, Any] = Field(default_factory=dict, description="Security settings")


class UserStats(BaseModel):
    """User statistics."""
    hosts_count: int = Field(default=0, description="Number of hosts")
    active_sessions_count: int = Field(default=0, description="Number of active sessions")
    account_age_days: int = Field(default=0, description="Account age in days")
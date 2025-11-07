from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator


class UserLogin(BaseModel):
    """User login request."""
    username: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=1, description="Password")


class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    full_name: Optional[str] = Field(None, description="Full name")

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class Token(BaseModel):
    """Token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Token data."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    token_type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str = Field(..., description="JWT refresh token")


class PasswordReset(BaseModel):
    """Password reset request."""
    email: EmailStr = Field(..., description="Email address")


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")

    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class ChangePassword(BaseModel):
    """Change password request."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class TOTPSetup(BaseModel):
    """TOTP setup response."""
    secret: str = Field(..., description="TOTP secret")
    qr_code: str = Field(..., description="QR code image (base64)")
    backup_codes: List[str] = Field(..., description="Backup codes")


class TOTPVerify(BaseModel):
    """TOTP verification request."""
    token: str = Field(..., min_length=6, max_length=6, description="TOTP token")


class TOTPEnable(BaseModel):
    """Enable TOTP request."""
    token: str = Field(..., min_length=6, max_length=6, description="TOTP token")
    secret: str = Field(..., description="TOTP secret")


class TOTPDisable(BaseModel):
    """Disable TOTP request."""
    password: str = Field(..., description="Password for confirmation")
    backup_code: Optional[str] = Field(None, description="Backup code (alternative to password)")


class OAuthLogin(BaseModel):
    """OAuth login request."""
    provider: str = Field(..., description="OAuth provider (google, github)")
    code: str = Field(..., description="Authorization code")
    state: Optional[str] = Field(None, description="State parameter")


class OAuthCallback(BaseModel):
    """OAuth callback response."""
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    user_info: dict = Field(..., description="User information")


class LogoutRequest(BaseModel):
    """Logout request."""
    refresh_token: Optional[str] = Field(None, description="Refresh token to revoke")


class RevokeTokenRequest(BaseModel):
    """Revoke token request."""
    token: str = Field(..., description="Token to revoke")
    token_type: str = Field(..., description="Token type (access/refresh)")


class VerifyEmail(BaseModel):
    """Email verification request."""
    token: str = Field(..., description="Email verification token")


class ResendVerification(BaseModel):
    """Resend verification email request."""
    email: EmailStr = Field(..., description="Email address")


class LoginResponse(BaseModel):
    """Login response with user data."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: dict = Field(..., description="User information")
    requires_2fa: bool = Field(default=False, description="Whether 2FA is required")


class TwoFactorChallenge(BaseModel):
    """2FA challenge response."""
    challenge_id: str = Field(..., description="Challenge ID")
    methods: List[str] = Field(..., description="Available 2FA methods")


class TwoFactorResponse(BaseModel):
    """2FA verification response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class SessionInfo(BaseModel):
    """Session information."""
    session_id: str = Field(..., description="Session ID")
    created_at: str = Field(..., description="Session creation time")
    last_activity: str = Field(..., description="Last activity time")
    ip_address: str = Field(..., description="IP address")
    user_agent: str = Field(..., description="User agent")
    is_current: bool = Field(default=False, description="Is current session")


class ActiveSessionsResponse(BaseModel):
    """Active sessions response."""
    sessions: List[SessionInfo] = Field(..., description="Active sessions")
    total: int = Field(..., description="Total number of sessions")


class RevokeSessionRequest(BaseModel):
    """Revoke session request."""
    session_id: str = Field(..., description="Session ID to revoke")


class ApiKeyCreate(BaseModel):
    """Create API key request."""
    name: str = Field(..., description="API key name")
    scopes: List[str] = Field(default=["read"], description="API key scopes")
    expires_at: Optional[str] = Field(None, description="Expiration date")


class ApiKeyResponse(BaseModel):
    """API key response."""
    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    key: str = Field(..., description="API key (only shown on creation)")
    scopes: List[str] = Field(..., description="API key scopes")
    created_at: str = Field(..., description="Creation time")
    expires_at: Optional[str] = Field(None, description="Expiration date")
    last_used_at: Optional[str] = Field(None, description="Last used time")


class ApiKeyInfo(BaseModel):
    """API key info (without the actual key)."""
    id: str = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    scopes: List[str] = Field(..., description="API key scopes")
    created_at: str = Field(..., description="Creation time")
    expires_at: Optional[str] = Field(None, description="Expiration date")
    last_used_at: Optional[str] = Field(None, description="Last used time")
    is_active: bool = Field(..., description="Is API key active")
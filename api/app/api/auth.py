import secrets
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import (
    get_db, get_redis_client, get_rate_limiter,
    get_client_ip, get_user_agent
)
from app.core.config import settings
from app.core.database import get_redis
from app.core.security import (
    create_access_token, create_refresh_token, verify_token,
    generate_password_reset_token, verify_password_reset_token,
    generate_totp_secret, generate_totp_qr_code, verify_totp_token,
    generate_session_token
)
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.auth import (
    UserLogin, UserRegister, Token, RefreshTokenRequest,
    PasswordReset, PasswordResetConfirm, ChangePassword,
    TOTPSetup, TOTPVerify, TOTPEnable, TOTPDisable,
    LoginResponse, TwoFactorChallenge, TwoFactorResponse,
    LogoutRequest, VerifyEmail, ResendVerification,
    ActiveSessionsResponse, RevokeSessionRequest
)
from app.schemas.user import UserResponse
from app.utils.exceptions import (
    AuthenticationError, ValidationError, RateLimitError,
    NotFoundError, ConflictError
)

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(
    request: Request,
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Register a new user."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    rate_limiter = await get_rate_limiter()

    # Rate limiting
    rate_limit_key = f"register:{client_ip}"
    if not await rate_limiter.is_allowed(rate_limit_key, settings.AUTH_RATE_LIMIT_PER_MINUTE):
        raise RateLimitError("Too many registration attempts")

    # Check if user already exists
    existing_user = await User.get_by_email(db, user_data.email)
    if existing_user:
        await AuditLog.log_authentication_event(
            db=db,
            action="register_failed",
            email=user_data.email,
            ip_address=client_ip,
            user_agent=user_agent,
            status="failure",
            error_message="Email already registered"
        )
        raise ConflictError("Email already registered")

    try:
        # Create user
        user = await User.create(
            db=db,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )

        # Log successful registration
        await AuditLog.log_authentication_event(
            db=db,
            action="register",
            user_id=str(user.id),
            email=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
            status="success"
        )

        logger.info("User registered successfully", user_id=user.id, email=user.email)

        return UserResponse.from_orm(user)

    except Exception as e:
        logger.error("Registration failed", email=user_data.email, error=str(e))
        raise ValidationError("Registration failed")


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Authenticate user and return tokens."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    rate_limiter = await get_rate_limiter()

    # Rate limiting
    rate_limit_key = f"login:{client_ip}"
    if not await rate_limiter.is_allowed(rate_limit_key, settings.AUTH_RATE_LIMIT_PER_MINUTE):
        raise RateLimitError("Too many login attempts")

    # Authenticate user
    user = await User.authenticate(db, user_data.username, user_data.password)
    if not user:
        await AuditLog.log_authentication_event(
            db=db,
            action="login_failed",
            email=user_data.username,
            ip_address=client_ip,
            user_agent=user_agent,
            status="failure",
            error_message="Invalid credentials"
        )
        raise AuthenticationError("Invalid email or password")

    # Check if user has 2FA enabled
    if user.has_2fa:
        # Create temporary challenge
        challenge_id = generate_session_token()
        redis = await get_redis()
        await redis.setex(
            f"2fa_challenge:{challenge_id}",
            300,  # 5 minutes
            str(user.id)
        )

        await AuditLog.log_authentication_event(
            db=db,
            action="login_2fa_challenge",
            user_id=str(user.id),
            email=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
            status="success"
        )

        return LoginResponse(
            access_token="",
            refresh_token="",
            token_type="bearer",
            expires_in=0,
            user=UserResponse.from_orm(user).dict(),
            requires_2fa=True
        )

    # Create tokens
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        expires_delta=refresh_token_expires
    )

    # Log successful login
    await AuditLog.log_authentication_event(
        db=db,
        action="login",
        user_id=str(user.id),
        email=user.email,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success",
        authentication_method="password",
        mfa_verified=False
    )

    logger.info("User logged in successfully", user_id=user.id, email=user.email)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.from_orm(user).dict(),
        requires_2fa=False
    )


@router.post("/verify-2fa", response_model=TwoFactorResponse)
async def verify_2fa(
    request: Request,
    challenge_data: TOTPVerify,
    challenge_id: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Verify 2FA token and complete login."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    redis = await get_redis()

    # Get user ID from challenge
    user_id = await redis.get(f"2fa_challenge:{challenge_id}")
    if not user_id:
        raise AuthenticationError("Invalid or expired challenge")

    # Get user
    user = await User.get_by_id(db, user_id)
    if not user or not user.has_2fa:
        raise AuthenticationError("Invalid challenge")

    # Verify TOTP token
    if not verify_totp_token(user.totp_secret, challenge_data.token):
        await AuditLog.log_authentication_event(
            db=db,
            action="login_failed",
            user_id=str(user.id),
            email=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
            status="failure",
            error_message="Invalid 2FA token"
        )
        raise AuthenticationError("Invalid 2FA token")

    # Clear challenge
    await redis.delete(f"2fa_challenge:{challenge_id}")

    # Create tokens
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        expires_delta=refresh_token_expires
    )

    # Log successful login
    await AuditLog.log_authentication_event(
        db=db,
        action="login",
        user_id=str(user.id),
        email=user.email,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success",
        authentication_method="password",
        mfa_verified=True
    )

    logger.info("User logged in successfully with 2FA", user_id=user.id, email=user.email)

    return TwoFactorResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Refresh access token."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Verify refresh token
    user_id = verify_token(token_data.refresh_token, "refresh")
    if not user_id:
        raise AuthenticationError("Invalid refresh token")

    # Get user
    user = await User.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    # Create new access token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires
    )

    # Log token refresh
    await AuditLog.log_authentication_event(
        db=db,
        action="token_refresh",
        user_id=str(user.id),
        email=user.email,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success"
    )

    return Token(
        access_token=access_token,
        refresh_token=token_data.refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout")
async def logout(
    request: Request,
    logout_data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Logout user and revoke tokens."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Log logout
    await AuditLog.log_authentication_event(
        db=db,
        action="logout",
        user_id=str(current_user.id),
        email=current_user.email,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success"
    )

    # In a real implementation, you would add the refresh token to a blacklist
    # For now, we'll just log the logout

    logger.info("User logged out successfully", user_id=current_user.id, email=current_user.email)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current user information."""
    return UserResponse.from_orm(current_user)


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Change user password."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Verify current password
    if not await current_user.verify_password(password_data.current_password):
        raise AuthenticationError("Current password is incorrect")

    # Update password
    await current_user.update_password(db, password_data.new_password)

    # Log password change
    await AuditLog.log_authentication_event(
        db=db,
        action="password_change",
        user_id=str(current_user.id),
        email=current_user.email,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success"
    )

    logger.info("Password changed successfully", user_id=current_user.id, email=current_user.email)

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    password_data: PasswordReset,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Request password reset."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    rate_limiter = await get_rate_limiter()

    # Rate limiting
    rate_limit_key = f"reset_password:{client_ip}"
    if not await rate_limiter.is_allowed(rate_limit_key, 5, 3600):  # 5 per hour
        raise RateLimitError("Too many password reset attempts")

    # Get user
    user = await User.get_by_email(db, password_data.email)
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a reset link has been sent"}

    # Generate reset token
    reset_token = generate_password_reset_token(user.email)

    # In a real implementation, you would send this via email
    # For now, we'll just log it (development only)
    if settings.is_development:
        logger.info("Password reset token", email=user.email, token=reset_token)

    # Log password reset request
    await AuditLog.log_authentication_event(
        db=db,
        action="password_reset_request",
        user_id=str(user.id),
        email=user.email,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success"
    )

    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    request: Request,
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Reset password with token."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Verify reset token
    email = verify_password_reset_token(reset_data.token)
    if not email:
        raise AuthenticationError("Invalid or expired reset token")

    # Get user
    user = await User.get_by_email(db, email)
    if not user:
        raise NotFoundError("User not found")

    # Update password
    await user.update_password(db, reset_data.new_password)

    # Log password reset
    await AuditLog.log_authentication_event(
        db=db,
        action="password_reset",
        user_id=str(user.id),
        email=user.email,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success"
    )

    logger.info("Password reset successfully", user_id=user.id, email=user.email)

    return {"message": "Password reset successfully"}


@router.post("/enable-2fa", response_model=TOTPSetup)
async def enable_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Setup 2FA for user."""
    if current_user.has_2fa:
        raise ConflictError("2FA is already enabled")

    # Generate TOTP secret
    secret = generate_totp_secret()
    backup_codes = [secrets.token_hex(4) for _ in range(10)]

    # Generate QR code
    qr_code = generate_totp_qr_code(current_user.email, secret)

    # Store secret temporarily (not activated yet)
    redis = await get_redis()
    await redis.setex(
        f"totp_setup:{current_user.id}",
        600,  # 10 minutes
        f"{secret}:{','.join(backup_codes)}"
    )

    return TOTPSetup(
        secret=secret,
        qr_code=qr_code,
        backup_codes=backup_codes
    )


@router.post("/confirm-2fa")
async def confirm_2fa(
    request: Request,
    totp_data: TOTPEnable,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Confirm and enable 2FA."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Get temporary secret
    redis = await get_redis()
    temp_data = await redis.get(f"totp_setup:{current_user.id}")
    if not temp_data:
        raise ValidationError("2FA setup not initiated or expired")

    secret, backup_codes_str = temp_data.split(":", 1)
    backup_codes = backup_codes_str.split(",")

    # Verify TOTP token
    if not verify_totp_token(secret, totp_data.token):
        raise ValidationError("Invalid 2FA token")

    # Enable 2FA
    await current_user.enable_2fa(db, secret, backup_codes)

    # Clean up temporary data
    await redis.delete(f"totp_setup:{current_user.id}")

    # Log 2FA enable
    await AuditLog.log_authentication_event(
        db=db,
        action="2fa_enabled",
        user_id=str(current_user.id),
        email=current_user.email,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success"
    )

    logger.info("2FA enabled successfully", user_id=current_user.id, email=current_user.email)

    return {"message": "2FA enabled successfully"}


@router.post("/disable-2fa")
async def disable_2fa(
    request: Request,
    totp_data: TOTPDisable,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Disable 2FA."""
    client_ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    if not current_user.has_2fa:
        raise ConflictError("2FA is not enabled")

    # Verify password or backup code
    if totp_data.backup_code:
        if totp_data.backup_code not in (current_user.backup_codes or []):
            raise AuthenticationError("Invalid backup code")
    else:
        if not await current_user.verify_password(totp_data.password):
            raise AuthenticationError("Invalid password")

    # Disable 2FA
    await current_user.disable_2fa(db)

    # Log 2FA disable
    await AuditLog.log_authentication_event(
        db=db,
        action="2fa_disabled",
        user_id=str(current_user.id),
        email=current_user.email,
        ip_address=client_ip,
        user_agent=user_agent,
        status="success"
    )

    logger.info("2FA disabled successfully", user_id=current_user.id, email=current_user.email)

    return {"message": "2FA disabled successfully"}
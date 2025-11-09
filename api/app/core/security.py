import secrets
import hashlib
import base64
import os
from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pyotp import TOTP
import qrcode
from io import BytesIO
import base64

from app.core.config import settings


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT refresh token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow()
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        token_id: str = payload.get("sub")
        token_type_claim: str = payload.get("type")

        if token_id is None or token_type_claim != token_type:
            return None

        return token_id
    except JWTError:
        return None


def get_password_hash(password: str) -> str:
    """Hash password using Argon2."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_password_reset_token(email: str) -> str:
    """Generate password reset token."""
    delta = timedelta(hours=1)  # Token expires in 1 hour
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify password reset token."""
    try:
        decoded_token = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return decoded_token["sub"]
    except JWTError:
        return None


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.master_key = self._decode_key(master_key)
        else:
            self.master_key = self._generate_key()

    def _decode_key(self, key_str: str) -> bytes:
        """Decode base64 key, handling missing padding."""
        # Add padding if missing
        padding_needed = 4 - (len(key_str) % 4)
        if padding_needed != 4:
            key_str += "=" * padding_needed

        try:
            return base64.b64decode(key_str.encode())
        except Exception:
            # If decoding fails, treat as raw key and hash it
            return hashlib.sha256(key_str.encode()).digest()

    def _generate_key(self) -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()

    def derive_user_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from user password."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode())
        return base64.urlsafe_b64encode(key)

    def encrypt_credential(self, data: str, user_key: bytes) -> str:
        """Encrypt credential data."""
        f = Fernet(user_key)
        encrypted_data = f.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()

    def decrypt_credential(self, encrypted_data: str, user_key: bytes) -> str:
        """Decrypt credential data."""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            f = Fernet(user_key)
            decrypted_data = f.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception:
            raise ValueError("Failed to decrypt data")

    def encrypt_with_master_key(self, data: str) -> str:
        """Encrypt data with master key."""
        f = Fernet(self.master_key)
        encrypted_data = f.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()

    def decrypt_with_master_key(self, encrypted_data: str) -> str:
        """Decrypt data with master key."""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            f = Fernet(self.master_key)
            decrypted_data = f.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception:
            raise ValueError("Failed to decrypt data")


def generate_secure_random_string(length: int = 32) -> str:
    """Generate cryptographically secure random string."""
    return secrets.token_urlsafe(length)


def generate_session_token() -> str:
    """Generate secure session token."""
    return secrets.token_urlsafe(32)


def generate_totp_secret() -> str:
    """Generate TOTP secret for 2FA."""
    return pyotp.random_base32()


def generate_totp_qr_code(user_email: str, secret: str) -> str:
    """Generate QR code for TOTP setup."""
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email,
        issuer_name="ParSSH"
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    img_str = base64.b64encode(buffer.read()).decode()
    return f"data:image/png;base64,{img_str}"


def verify_totp_token(secret: str, token: str) -> bool:
    """Verify TOTP token."""
    try:
        totp = TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 1 step tolerance
    except Exception:
        return False


def generate_api_key() -> str:
    """Generate API key for external integrations."""
    return f"parssh_{secrets.token_urlsafe(40)}"


def hash_api_key(api_key: str) -> str:
    """Hash API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify API key against hash."""
    return hash_api_key(api_key) == hashed_key


def generate_csrf_token() -> str:
    """Generate CSRF token."""
    return secrets.token_urlsafe(32)


# Global encryption service instance
encryption_service = EncryptionService(settings.ENCRYPTION_KEY_BASE64)
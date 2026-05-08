import bcrypt
from jose import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pyotp
import secrets
import base64

from app.core.config import settings


# Password Hashing
def hash_password(password: str) -> str:
    """Hash password using bcrypt with cost factor 12"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


# JWT Token Management
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with 15-minute expiration"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token with 30-day expiration"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Verify token is valid and of correct type"""
    payload = decode_token(token)
    if payload and payload.get("type") == token_type:
        return payload
    return None


# TOTP for MFA
def generate_totp_secret() -> str:
    """Generate 160-bit random TOTP secret (Base32 encoded)"""
    random_bytes = secrets.token_bytes(20)  # 160 bits
    return base64.b32encode(random_bytes).decode('utf-8')


def generate_totp_uri(secret: str, email: str) -> str:
    """Generate otpauth:// URI for QR code generation"""
    totp = pyotp.TOTP(secret, digits=settings.MFA_DIGITS, period=settings.MFA_PERIOD)
    return totp.provisioning_uri(
        name=email,
        issuer_name=settings.MFA_ISSUER
    )


def verify_totp(secret: str, token: str, valid_window: int = 1) -> bool:
    """Verify TOTP token with ±1 step skew tolerance"""
    totp = pyotp.TOTP(secret, digits=settings.MFA_DIGITS, period=settings.MFA_PERIOD)
    return totp.verify(token, valid_window=valid_window)


# Recovery Codes
def generate_recovery_codes(count: int = 10) -> list[str]:
    """Generate 10 random 8-character recovery codes"""
    codes = []
    for _ in range(count):
        code = secrets.token_hex(4).upper()  # 8 characters, hex, uppercase
        codes.append(code)
    return codes


def hash_recovery_code(code: str) -> str:
    """Hash recovery code using bcrypt for secure storage"""
    return hash_password(code)


# Secure Token Generation
def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token"""
    return secrets.token_urlsafe(length)


# Email Token Hashing
def hash_email_token(token: str) -> str:
    """Hash email verification/reset token using SHA256"""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()

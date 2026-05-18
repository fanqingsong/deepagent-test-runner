"""
Unified Authentication Service

Supports both local JWT authentication and Casdoor SSO authentication.
"""

import os
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select

from app.core.config import settings
from app.core.auth_security import decode_token

# Casdoor SDK (optional import)
try:
    from casdoor import CasdoorSDK
    CASDOOR_AVAILABLE = True
except ImportError:
    CASDOOR_AVAILABLE = False

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()

# Global Casdoor SDK instance
_casdoor_sdk = None


def get_casdoor_sdk():
    """Get or initialize Casdoor SDK."""
    global _casdoor_sdk
    if not CASDOOR_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Casdoor SDK not installed. Install with: pip install casdoor"
        )

    if _casdoor_sdk is None:
        endpoint = os.environ.get("CASDOOR_ENDPOINT", "http://casdoor:8000")
        client_id = os.environ.get("CASDOOR_CLIENT_ID", "")
        client_secret = os.environ.get("CASDOOR_CLIENT_SECRET", "")
        organization = os.environ.get("CASDOOR_ORGANIZATION", "admin")
        application = os.environ.get("CASDOOR_APPLICATION", "app-example")
        certificate = os.environ.get("CASDOOR_CERTIFICATE", "")

        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Casdoor configuration missing"
            )

        _casdoor_sdk = CasdoorSDK(
            endpoint=endpoint,
            client_id=client_id,
            client_secret=client_secret,
            certificate=certificate,
            org_name=organization,
            application_name=application
        )

    return _casdoor_sdk


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Verify a JWT token from Authorization header.

    Supports both local JWT tokens and Casdoor tokens.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        dict: User information from token
    """
    token = credentials.credentials

    # Try local JWT first
    try:
        payload = decode_token(token)
        if payload:
            payload["provider"] = "local"
            user_id = payload.get("sub")
            if user_id:
                return payload
    except Exception:
        pass  # Try Casdoor next

    # Try Casdoor token
    try:
        if CASDOOR_AVAILABLE:
            sdk = get_casdoor_sdk()
            payload = sdk.parse_jwt_token(token)
            # Normalize Casdoor payload to match local format
            normalized_payload = {
                "sub": payload.get("id"),
                "username": payload.get("name"),
                "email": payload.get("email"),
                "provider": "casdoor",
                "roles": payload.get("roles", [])
            }
            return normalized_payload
    except Exception:
        pass

    # If neither worked, raise error
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def verify_permission(required_roles: list = None):
    """
    Dependency factory to verify if user has required roles.

    Args:
        required_roles: List of roles required to access the resource

    Returns:
        FastAPI dependency function
    """
    async def dependency(user: dict = Depends(verify_token)):
        """Inner dependency that checks user roles."""
        if required_roles is None:
            return user

        # Check if user has required roles
        user_roles = user.get("roles", [])

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return user

    return dependency


async def authenticate_user_local(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user with local username and password.

    Args:
        username: The username
        password: The password

    Returns:
        Token response if successful, None otherwise
    """
    from app.core.security import verify_password, create_access_token
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import get_db
    from app.models.user import User

    try:
        async for db in get_db():
            # Query user from database
            result = await db.execute(
                select(User).where(User.username == username)
            )
            user = result.scalar_one_or_none()

            if not user or not user.is_active:
                return None

            if not verify_password(password, user.hashed_password):
                return None

            # Create access token
            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin
            }
            access_token = create_access_token(data=token_data)

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "provider": "local",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": user.is_admin
                }
            }
    except Exception as e:
        # Import failed, return None
        return None


async def authenticate_user_casdoor(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user with Casdoor username and password.

    Args:
        username: The username
        password: The password

    Returns:
        Token response if successful, None otherwise
    """
    if not CASDOOR_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Casdoor SDK not installed"
        )

    try:
        sdk = get_casdoor_sdk()
        token_response = sdk.get_oauth_token(
            code="",
            username=username,
            password=password,
            grant_type="password"
        )

        # Get user info
        user_info = sdk.get_user(token_response["access_token"])

        return {
            "access_token": token_response.get("access_token"),
            "refresh_token": token_response.get("refresh_token"),
            "token_type": "bearer",
            "provider": "casdoor",
            "user": {
                "id": user_info.get("id"),
                "username": user_info.get("name"),
                "email": user_info.get("email"),
                "roles": user_info.get("roles", [])
            }
        }
    except Exception as e:
        return None


async def refresh_token(refresh_token: str, provider: str) -> Optional[dict]:
    """
    Refresh an access token using a refresh token.

    Args:
        refresh_token: The refresh token
        provider: The auth provider ("local" or "casdoor")

    Returns:
        New token response if successful, None otherwise
    """
    if provider == "casdoor" and CASDOOR_AVAILABLE:
        try:
            sdk = get_casdoor_sdk()
            new_tokens = sdk.refresh_token_request(
                refresh_token=refresh_token,
                scope=""
            )
            return new_tokens
        except Exception:
            return None

    # Local tokens don't support refresh in current implementation
    return None


"""
Authentication Service — orchestration layer for user authentication

Coordinates registration, email verification, authentication, and password management.
Split into focused modules:
- AuthRegistrationService: User registration and email verification
- AuthPasswordResetService: Password reset and change operations
"""

from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.auth_security import verify_password
from app.utils.email import normalize_email
from app.core.auth_rate_limit import check_rate_limit
import logging

from .auth_registration import AuthRegistrationService
from .auth_password_reset import AuthPasswordResetService

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user authentication and management"""

    @staticmethod
    async def check_email_exists(db: AsyncSession, email: str) -> bool:
        """Check if email already exists in database."""
        return await AuthRegistrationService.check_email_exists(db, email)

    @staticmethod
    async def register_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Tuple[bool, Optional[str], Optional[User]]:
        """Register a new user account."""
        return await AuthRegistrationService.register_user(db, email, password)

    @staticmethod
    async def verify_email(
        db: AsyncSession,
        token: str
    ) -> Tuple[bool, Optional[str], Optional[User]]:
        """Verify user email with token."""
        return await AuthRegistrationService.verify_email(db, token)

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
        ip_address: str
    ) -> Tuple[bool, Optional[str], Optional[User]]:
        """
        Authenticate user with email and password.

        Args:
            db: Database session
            email: User email
            password: User password
            ip_address: Client IP address for rate limiting

        Returns:
            Tuple of (success, error_message, user_object)
        """
        # Normalize email
        normalized_email = normalize_email(email)

        # Check rate limit
        allowed, remaining, retry_after = await check_rate_limit(
            identifier=ip_address,
            max_attempts=5,
            window_seconds=900
        )

        if not allowed:
            return False, f"Too many login attempts. Try again in {retry_after} seconds.", None

        # Find user by email
        query = select(User).where(
            User.email == normalized_email,
            User.status == "active"
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            # Rate limit still applies even for non-existent users
            return False, "Invalid email or password", None

        # Check if account is locked
        if user.is_locked():
            return False, "Account is temporarily locked due to failed login attempts. Try again later.", None

        # Verify password
        if not verify_password(password, user.hashed_password):
            # Increment failed login attempts
            user.failed_login_attempts += 1

            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.lock_account(minutes=15)
                await db.commit()
                logger.warning(f"Account {user.id} locked due to 5 failed login attempts")

            return False, "Invalid email or password", None

        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.update_last_login()

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating user after login: {str(e)}")
            return False, "Login failed", None

        # Check if MFA is enabled
        from app.services.auth.mfa_service import MFAService
        mfa_success, mfa_enabled, _ = await MFAService.get_mfa_status(db, user.id)

        if mfa_success and mfa_enabled:
            return True, "MFA_REQUIRED", user

        return True, None, user

    @staticmethod
    async def logout_user(
        db: AsyncSession,
        user_id: int,
        session_token: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Logout user and invalidate session.

        Args:
            db: Database session
            user_id: User ID
            session_token: Session token to invalidate

        Returns:
            Tuple of (success, error_message)
        """
        from app.services.auth.session_service import SessionService

        session = await SessionService.validate_session_token(db, session_token)

        if not session:
            return False, "Invalid session"

        try:
            session.terminate()
            await db.commit()

            logger.info(f"User {user_id} logged out successfully")
            return True, None

        except Exception as e:
            await db.rollback()
            logger.error(f"Error during logout: {str(e)}")
            return False, "Logout failed"

    @staticmethod
    async def generate_password_reset_token(
        db: AsyncSession,
        email: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Generate password reset token and send email."""
        return await AuthPasswordResetService.generate_password_reset_token(db, email)

    @staticmethod
    async def verify_password_reset_token(
        db: AsyncSession,
        token: str
    ) -> Tuple[bool, Optional[str], Optional[User]]:
        """Verify password reset token."""
        return await AuthPasswordResetService.verify_password_reset_token(db, token)

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        token: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """Reset user password with valid token."""
        return await AuthPasswordResetService.reset_password(db, token, new_password)

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """Change user password (requires current password verification)."""
        return await AuthPasswordResetService.change_password(db, user_id, current_password, new_password)

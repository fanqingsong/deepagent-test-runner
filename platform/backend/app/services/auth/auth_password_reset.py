"""
Authentication Password Reset Service

Handles password reset and change operations.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import EmailToken
from app.models.user import User
from app.core.auth_security import hash_password, hash_email_token
from app.utils.password import validate_password_strength
from app.utils.email import is_valid_email_format, normalize_email, send_email
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AuthPasswordResetService:
    """Handles password reset and change operations."""

    @staticmethod
    async def generate_password_reset_token(
        db: AsyncSession,
        email: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate password reset token and send email.

        Args:
            db: Database session
            email: User email address

        Returns:
            Tuple of (success, error_message, reset_token)
        """
        # Normalize email
        normalized_email = normalize_email(email)

        # Validate email format
        if not is_valid_email_format(normalized_email):
            return False, "Invalid email format", None

        # Find user by email
        query = select(User).where(
            User.email == normalized_email,
            User.status == "active"
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            # Don't reveal if email exists or not for security
            logger.info(f"Password reset requested for non-existent email: {normalized_email}")
            return True, None, None

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        hashed_token = hash_email_token(reset_token)
        expiry = datetime.utcnow() + timedelta(hours=1)

        try:
            # Create email token record
            email_token = EmailToken(
                user_id=user.id,
                token_hash=hashed_token,
                token_type="password_reset",
                expires_at=expiry
            )
            db.add(email_token)
            await db.commit()

            # Send reset email directly (non-blocking)
            reset_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/auth/reset-password?token={reset_token}"
            await send_email(
                to_email=user.email,
                subject="Reset Your Password",
                template_name="password_reset",
                context={"reset_url": reset_url},
            )

            logger.info(f"Password reset token generated for user {user.id}")
            return True, None, reset_token

        except Exception as e:
            await db.rollback()
            logger.error(f"Error generating password reset token: {str(e)}")
            return False, "Failed to generate reset token", None

    @staticmethod
    async def verify_password_reset_token(
        db: AsyncSession,
        token: str
    ) -> Tuple[bool, Optional[str], Optional[User]]:
        """
        Verify password reset token.

        Args:
            db: Database session
            token: Reset token to verify

        Returns:
            Tuple of (success, error_message, user_object)
        """
        # Hash the provided token
        hashed_token = hash_email_token(token)

        # Find token in database
        query = select(EmailToken).where(
            EmailToken.token_hash == hashed_token,
            EmailToken.token_type == "password_reset",
            EmailToken.used_at.is_(None)
        )
        result = await db.execute(query)
        email_token = result.scalar_one_or_none()

        if not email_token:
            return False, "Invalid or expired reset token", None

        # Check if token is expired
        if email_token.is_expired():
            return False, "Reset token has expired", None

        # Get user
        user_query = select(User).where(User.id == email_token.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()

        if not user:
            return False, "User not found", None

        return True, None, user

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        token: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Reset user password with valid token.

        Args:
            db: Database session
            token: Valid reset token
            new_password: New password to set

        Returns:
            Tuple of (success, error_message)
        """
        from app.services.auth.session_service import SessionService

        # Verify token
        success, error_message, user = await AuthPasswordResetService.verify_password_reset_token(db, token)

        if not success:
            return False, error_message

        # Validate password strength
        is_valid, validation_error = validate_password_strength(new_password)
        if not is_valid:
            return False, validation_error

        try:
            # Hash new password
            user.hashed_password = hash_password(new_password)

            # Mark token as used
            hashed_token = hash_email_token(token)
            token_query = select(EmailToken).where(
                EmailToken.token_hash == hashed_token,
                EmailToken.token_type == "password_reset"
            )
            token_result = await db.execute(token_query)
            email_token = token_result.scalar_one_or_none()

            if email_token:
                email_token.mark_as_used()

            # Invalidate all existing sessions for security
            await SessionService.terminate_all_user_sessions(db, user.id)

            await db.commit()

            logger.info(f"Password reset successful for user {user.id}")
            return True, None

        except Exception as e:
            await db.rollback()
            logger.error(f"Error resetting password: {str(e)}")
            return False, "Failed to reset password"

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user password (requires current password verification).

        Args:
            db: Database session
            user_id: User ID
            current_password: Current password for verification
            new_password: New password to set

        Returns:
            Tuple of (success, error_message)
        """
        from app.services.auth.session_service import SessionService
        from app.models.auth import UserSession

        # Get user
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False, "User not found"

        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            return False, "Current password is incorrect"

        # Validate new password strength
        is_valid, validation_error = validate_password_strength(new_password)
        if not is_valid:
            return False, validation_error

        # Check if new password is same as current
        if verify_password(new_password, user.hashed_password):
            return False, "New password must be different from current password"

        try:
            # Update password
            user.hashed_password = hash_password(new_password)

            # Invalidate all other sessions for security
            # Get all sessions for user
            session_query = select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
            session_result = await db.execute(session_query)
            sessions = session_result.scalars().all()

            # Terminate all sessions
            for session in sessions:
                session.terminate()

            await db.commit()

            logger.info(f"Password changed successfully for user {user_id}")
            return True, None

        except Exception as e:
            await db.rollback()
            logger.error(f"Error changing password: {str(e)}")
            return False, "Failed to change password"

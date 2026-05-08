from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import Optional, Tuple
import secrets
import logging

from app.models.auth import UserAccount, EmailToken
from app.core.auth_security import hash_password, hash_email_token, generate_secure_token, verify_password
from app.utils.password import validate_password_strength
from app.utils.email import is_valid_email_format, normalize_email
from app.shared.email.client import email_client
from app.core.auth_rate_limit import check_rate_limit

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user registration and verification"""

    @staticmethod
    async def check_email_exists(db: AsyncSession, email: str) -> bool:
        """
        Check if email already exists in database.

        Args:
            db: Database session
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        query = select(UserAccount).where(UserAccount.email == normalize_email(email))
        result = await db.execute(query)
        return result.first() is not None

    @staticmethod
    async def register_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Tuple[bool, Optional[str], Optional[UserAccount]]:
        """
        Register a new user account.

        Args:
            db: Database session
            email: User email address
            password: User password

        Returns:
            Tuple of (success, error_message, user_object)
        """
        # Validate email format
        if not is_valid_email_format(email):
            return False, "Invalid email format", None

        # Normalize email
        normalized_email = normalize_email(email)

        # Validate password strength
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            return False, f"Password requirements not met: {', '.join(errors)}", None

        # Check if email already exists
        if await AuthService.check_email_exists(db, normalized_email):
            return False, "Email already registered", None

        try:
            # Create new user
            user = UserAccount(
                email=normalized_email,
                password_hash=hash_password(password),
                is_verified=False,
                status="active"
            )

            db.add(user)
            await db.flush()

            # Generate email verification token
            verification_token = generate_secure_token()
            token_hash = hash_email_token(verification_token)

            # Create email token record (24-hour expiry)
            email_token = EmailToken(
                user_id=user.id,
                token_hash=token_hash,
                token_type="verification",
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )

            db.add(email_token)
            await db.commit()
            await db.refresh(user)

            # Queue verification email
            verification_url = f"http://localhost:8013/auth/verify-email?token={verification_token}"
            email_client.send_verification_email(normalized_email, verification_url)

            logger.info(f"User registered successfully: {user.id}")
            return True, None, user

        except IntegrityError as e:
            await db.rollback()
            logger.error(f"IntegrityError during registration: {str(e)}")
            return False, "Email already registered", None
        except Exception as e:
            await db.rollback()
            logger.error(f"Error during registration: {str(e)}")
            return False, "Registration failed. Please try again.", None

    @staticmethod
    async def verify_email(
        db: AsyncSession,
        token: str
    ) -> Tuple[bool, Optional[str], Optional[UserAccount]]:
        """
        Verify user email with token.

        Args:
            db: Database session
            token: Verification token

        Returns:
            Tuple of (success, error_message, user_object)
        """
        # Hash the token to match database storage
        token_hash = hash_email_token(token)

        # Find unused token within expiry period
        query = select(EmailToken).where(
            EmailToken.token_hash == token_hash,
            EmailToken.token_type == "verification",
            EmailToken.used_at.is_(None)
        )
        result = await db.execute(query)
        email_token = result.first()

        if not email_token:
            return False, "Invalid or expired verification token", None

        if email_token.is_expired():
            return False, "Verification token has expired", None

        try:
            # Get user and mark as verified
            user_query = select(UserAccount).where(UserAccount.id == email_token.user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one()

            user.set_email_verified()

            # Mark token as used
            email_token.mark_as_used()

            await db.commit()

            logger.info(f"Email verified successfully: {user.id}")
            return True, None, user

        except Exception as e:
            await db.rollback()
            logger.error(f"Error during email verification: {str(e)}")
            return False, "Email verification failed", None

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
        ip_address: str
    ) -> Tuple[bool, Optional[str], Optional[UserAccount]]:
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
        query = select(UserAccount).where(
            UserAccount.email == normalized_email,
            UserAccount.status == "active"
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
        if not verify_password(password, user.password_hash):
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
        from app.services.mfa_service import MFAService
        mfa_success, mfa_enabled, _ = await MFAService.get_mfa_status(db, user.id)

        if mfa_success and mfa_enabled:
            # Return special response indicating MFA is required
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
        from app.services.session_service import SessionService

        # Validate session
        session = await SessionService.validate_session_token(db, session_token)

        if not session:
            return False, "Invalid session"

        try:
            # Terminate session
            session.terminate()
            await db.commit()

            logger.info(f"User {user_id} logged out successfully")
            return True, None

        except Exception as e:
            await db.rollback()
            logger.error(f"Error during logout: {str(e)}")
            return False, "Logout failed"

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
        ip_address: str
    ) -> Tuple[bool, Optional[str], Optional[UserAccount]]:
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
        query = select(UserAccount).where(
            UserAccount.email == normalized_email,
            UserAccount.status == "active"
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
        if not verify_password(password, user.password_hash):
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
        from app.services.session_service import SessionService

        # Validate session
        session = await SessionService.validate_session_token(db, session_token)

        if not session:
            return False, "Invalid session"

        try:
            # Terminate session
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
        """
        Generate password reset token and send email.

        Args:
            db: Database session
            email: User email address

        Returns:
            Tuple of (success, error_message, reset_token)
        """
        from app.tasks.email_tasks import send_email_task

        # Normalize email
        normalized_email = normalize_email(email)

        # Validate email format
        if not is_valid_email_format(normalized_email):
            return False, "Invalid email format", None

        # Find user by email
        query = select(UserAccount).where(
            UserAccount.email == normalized_email,
            UserAccount.status == "active"
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

            # Send reset email
            await send_email_task.kick(
                template_id="password-reset",
                to_email=user.email,
                context={
                    "reset_token": reset_token,
                    "user_name": user.email.split('@')[0],
                    "expiry_hours": 1
                }
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
    ) -> Tuple[bool, Optional[str], Optional[UserAccount]]:
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
        user_query = select(UserAccount).where(UserAccount.id == email_token.user_id)
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
        # Verify token
        success, error_message, user = await AuthService.verify_password_reset_token(db, token)

        if not success:
            return False, error_message

        # Validate password strength
        is_valid, validation_error = validate_password_strength(new_password)
        if not is_valid:
            return False, validation_error

        try:
            # Hash new password
            user.password_hash = hash_password(new_password)

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
            from app.services.session_service import SessionService
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
        # Get user
        query = select(UserAccount).where(UserAccount.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False, "User not found"

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            return False, "Current password is incorrect"

        # Validate new password strength
        is_valid, validation_error = validate_password_strength(new_password)
        if not is_valid:
            return False, validation_error

        # Check if new password is same as current
        if verify_password(new_password, user.password_hash):
            return False, "New password must be different from current password"

        try:
            # Update password
            user.password_hash = hash_password(new_password)

            # Invalidate all other sessions for security
            from app.services.session_service import SessionService
            from sqlalchemy import select
            from app.models.auth import UserSession

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

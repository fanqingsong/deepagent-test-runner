"""
Authentication Registration Service

Handles user registration and email verification.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.auth import EmailToken
from app.models.user import User
from app.models.role import Role, user_roles
from app.core.auth_security import hash_password, hash_email_token, generate_secure_token
from app.utils.password import validate_password_strength
from app.utils.email import is_valid_email_format, normalize_email, send_email
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class AuthRegistrationService:
    """Handles user registration and email verification."""

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
        query = select(User).where(User.email == normalize_email(email))
        result = await db.execute(query)
        return result.first() is not None

    @staticmethod
    async def register_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Tuple[bool, Optional[str], Optional[User]]:
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
        if await AuthRegistrationService.check_email_exists(db, normalized_email):
            return False, "Email already registered", None

        try:
            # Create new user with all fields
            user = User(
                username=normalized_email.split('@')[0],  # Optional username derived from email
                email=normalized_email,
                hashed_password=hash_password(password),
                is_verified=False,
                status="active",
                is_active=True,
                is_admin=False,
            )

            db.add(user)
            await db.flush()

            # Assign default tester role via association table (avoids lazy-load in async)
            tester_role = (await db.execute(
                select(Role).where(Role.name == "tester")
            )).scalar_one_or_none()
            if tester_role:
                await db.execute(
                    insert(user_roles).values(user_id=user.id, role_id=tester_role.id)
                )

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

            # Send verification email directly (non-blocking)
            verification_url = (
                f"{settings.FRONTEND_BASE_URL.rstrip('/')}/auth/verify-email"
                f"?token={verification_token}"
            )
            await send_email(
                to_email=normalized_email,
                subject="Verify Your Email Address",
                template_name="verification",
                context={"verification_url": verification_url},
            )

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
    ) -> Tuple[bool, Optional[str], Optional[User]]:
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
        email_token = result.scalar_one_or_none()

        if not email_token:
            return False, "Invalid or expired verification token", None

        if email_token.is_expired():
            return False, "Verification token has expired", None

        try:
            # Get user and mark as verified
            user_query = select(User).where(User.id == email_token.user_id)
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

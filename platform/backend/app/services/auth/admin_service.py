"""
Admin service for user management and account operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Tuple, Optional
import logging

from app.models.user import User
from app.utils.email import send_email

logger = logging.getLogger(__name__)


class AdminService:
    """Admin service for user account management"""

    @staticmethod
    async def suspend_user(
        db: AsyncSession,
        user_id: int,
        reason: str,
        admin_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Suspend a user account.

        Args:
            db: Database session
            user_id: User ID to suspend
            reason: Reason for suspension
            admin_id: Admin user ID performing the suspension

        Returns:
            Tuple of (success, error_message)
        """
        # Get user to suspend
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False, "User not found"

        if user.is_suspended():
            return False, "User is already suspended"

        # Prevent admin from suspending themselves
        if user_id == admin_id:
            return False, "Cannot suspend your own account"

        try:
            # Suspend the user
            user.suspend(reason)

            # Send suspension email
            await send_email(
                to_email=user.email,
                subject="Account Suspended",
                template_name="account_suspended",
                context={"reason": reason},
            )

            await db.commit()

            logger.info(f"User {user_id} suspended by admin {admin_id}. Reason: {reason}")
            return True, None

        except Exception as e:
            await db.rollback()
            logger.error(f"Error suspending user {user_id}: {str(e)}")
            return False, "Failed to suspend user"

    @staticmethod
    async def reactivate_user(
        db: AsyncSession,
        user_id: int,
        admin_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Reactivate a suspended user account.

        Args:
            db: Database session
            user_id: User ID to reactivate
            admin_id: Admin user ID performing the reactivation

        Returns:
            Tuple of (success, error_message)
        """
        # Get user to reactivate
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return False, "User not found"

        if not user.is_suspended():
            return False, "User is not suspended"

        try:
            # Reactivate the user
            user.reactivate()

            # Send reactivation email (reuse suspension template with positive message)
            await send_email(
                to_email=user.email,
                subject="Account Reactivated",
                template_name="account_suspended",
                context={"reason": "Your account has been reactivated by an administrator."},
            )

            await db.commit()

            logger.info(f"User {user_id} reactivated by admin {admin_id}")
            return True, None

        except Exception as e:
            await db.rollback()
            logger.error(f"Error reactivating user {user_id}: {str(e)}")
            return False, "Failed to reactivate user"

    @staticmethod
    async def check_suspension_during_login(
        db: AsyncSession,
        user: User
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user account is suspended during login.

        Args:
            db: Database session
            user: User account object

        Returns:
            Tuple of (is_suspended, suspension_message)
        """
        if user.is_suspended():
            return True, "Your account has been suspended. Please contact support for assistance."

        return False, None

"""
Token Quota Repository Implementation

SQLAlchemy implementation of TokenQuota repository following async patterns.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.token_quota import TokenQuota
from app.repositories.interfaces.token_quota_repository_interface import ITokenQuotaRepository

logger = logging.getLogger(__name__)


class SQLAlchemyTokenQuotaRepository(ITokenQuotaRepository):
    """
    SQLAlchemy implementation of TokenQuota repository.

    Handles all database operations for TokenQuota model using async SQLAlchemy patterns.
    Provides proper error handling, logging, and transaction management.
    """

    def __init__(self):
        """Initialize the repository."""
        self._model_class = TokenQuota

    async def create(
        self,
        quota: Any,
        db_session: AsyncSession
    ) -> TokenQuota:
        """
        Create a new token quota.

        Args:
            quota: TokenQuotaCreate schema with quota data
            db_session: Database session

        Returns:
            Created TokenQuota object

        Raises:
            ValueError: If quota already exists for user with same name
        """
        # Check if quota already exists for this user with same name
        existing = await self.exists_for_user(quota.user_id, quota.name, db_session)
        if existing:
            raise ValueError(
                f"Quota already exists for user_id={quota.user_id}, name='{quota.name}'"
            )

        # Create new quota
        new_quota = TokenQuota(
            user_id=quota.user_id,
            name=quota.name,
            description=quota.description,
            period_type=quota.period_type,
            reset_strategy=quota.reset_strategy,
            period_start=quota.period_start,
            period_end=quota.period_end,
            total_tokens=quota.total_tokens,
            used_tokens=0,
            remaining_tokens=quota.total_tokens,
            priority=quota.priority,
            enforcement_mode=quota.enforcement_mode,
            status=quota.status,
            alert_thresholds=quota.alert_thresholds,
            config_data=quota.config_data
        )

        try:
            db_session.add(new_quota)
            await db_session.flush()
            await db_session.refresh(new_quota)

            logger.info(f"Created token quota {new_quota.id} for user {new_quota.user_id}")
            return new_quota

        except Exception as e:
            logger.error(f"Error creating token quota: {e}")
            await db_session.rollback()
            raise

    async def get_by_id(self, quota_id: int, db_session: AsyncSession) -> Optional[TokenQuota]:
        """
        Retrieve a token quota by its primary key ID.

        Args:
            quota_id: Primary key ID
            db_session: Database session

        Returns:
            TokenQuota object or None if not found
        """
        try:
            stmt = select(TokenQuota).where(TokenQuota.id == quota_id)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting quota by ID {quota_id}: {e}")
            return None

    async def get_by_user(
        self,
        user_id: int,
        db_session: AsyncSession,
        quota_name: Optional[str] = None
    ) -> Optional[TokenQuota]:
        """
        Retrieve a token quota by user ID and optionally by name.

        Args:
            user_id: User ID
            db_session: Database session
            quota_name: Optional quota name filter

        Returns:
            TokenQuota object or None if not found
        """
        try:
            stmt = select(TokenQuota).where(TokenQuota.user_id == user_id)

            if quota_name:
                stmt = stmt.where(TokenQuota.name == quota_name)

            stmt = stmt.order_by(desc(TokenQuota.created_at)).limit(1)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting quota for user {user_id}: {e}")
            return None

    async def get_by_user_all(
        self,
        user_id: int,
        db_session: AsyncSession,
        status: Optional[str] = None
    ) -> List[TokenQuota]:
        """
        Retrieve all quotas for a user.

        Args:
            user_id: User ID
            db_session: Database session
            status: Optional status filter

        Returns:
            List of TokenQuota objects
        """
        try:
            stmt = select(TokenQuota).where(TokenQuota.user_id == user_id)

            if status:
                stmt = stmt.where(TokenQuota.status == status)

            stmt = stmt.order_by(desc(TokenQuota.created_at))
            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting all quotas for user {user_id}: {e}")
            return []

    async def get_all(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[TokenQuota]:
        """
        Retrieve all token quotas with optional filtering.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip
            status: Optional status filter

        Returns:
            List of TokenQuota objects, ordered by created_at DESC
        """
        try:
            stmt = select(TokenQuota)

            if status:
                stmt = stmt.where(TokenQuota.status == status)

            stmt = stmt.order_by(desc(TokenQuota.created_at)).offset(offset).limit(limit)
            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting all quotas: {e}")
            return []

    async def get_active_quotas(
        self,
        db_session: AsyncSession,
        limit: int = 100
    ) -> List[TokenQuota]:
        """
        Retrieve all active token quotas.

        Args:
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of active TokenQuota objects
        """
        try:
            stmt = select(TokenQuota).where(
                TokenQuota.status == "active"
            ).order_by(desc(TokenQuota.created_at)).limit(limit)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting active quotas: {e}")
            return []

    async def get_exhausted_quotas(
        self,
        db_session: AsyncSession,
        limit: int = 100
    ) -> List[TokenQuota]:
        """
        Retrieve all exhausted token quotas.

        Args:
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of exhausted TokenQuota objects
        """
        try:
            stmt = select(TokenQuota).where(
                TokenQuota.status == "exhausted"
            ).order_by(desc(TokenQuota.created_at)).limit(limit)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting exhausted quotas: {e}")
            return []

    async def update(
        self,
        quota_id: int,
        updates: Dict[str, Any],
        db_session: AsyncSession
    ) -> TokenQuota:
        """
        Update a token quota.

        Args:
            quota_id: Primary key ID
            updates: Dictionary of fields to update
            db_session: Database session

        Returns:
            Updated TokenQuota object

        Raises:
            ValueError: If quota not found
        """
        try:
            quota = await self.get_by_id(quota_id, db_session)
            if not quota:
                raise ValueError(f"Quota not found: {quota_id}")

            for field, value in updates.items():
                if hasattr(quota, field):
                    setattr(quota, field, value)

            quota.updated_at = datetime.utcnow()
            await db_session.flush()
            await db_session.refresh(quota)

            logger.info(f"Updated token quota {quota_id}")
            return quota

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating quota {quota_id}: {e}")
            await db_session.rollback()
            raise

    async def update_usage(
        self,
        quota_id: int,
        tokens_used: int,
        db_session: AsyncSession
    ) -> TokenQuota:
        """
        Update usage for a token quota.

        Args:
            quota_id: Quota ID
            tokens_used: Number of tokens to add to used count
            db_session: Database session

        Returns:
            Updated TokenQuota object

        Raises:
            ValueError: If quota not found
        """
        try:
            quota = await self.get_by_id(quota_id, db_session)
            if not quota:
                raise ValueError(f"Quota not found: {quota_id}")

            # Update usage using model method
            quota.update_usage(tokens_used)
            quota.updated_at = datetime.utcnow()

            await db_session.flush()
            await db_session.refresh(quota)

            logger.debug(f"Updated usage for quota {quota_id}: +{tokens_used} tokens")
            return quota

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating usage for quota {quota_id}: {e}")
            await db_session.rollback()
            raise

    async def reset_period(
        self,
        quota_id: int,
        new_period_start: datetime,
        new_period_end: Optional[datetime],
        db_session: AsyncSession
    ) -> TokenQuota:
        """
        Reset the period for a token quota.

        Args:
            quota_id: Quota ID
            new_period_start: Start of new period
            new_period_end: End of new period (optional)
            db_session: Database session

        Returns:
            Updated TokenQuota object

        Raises:
            ValueError: If quota not found
        """
        try:
            quota = await self.get_by_id(quota_id, db_session)
            if not quota:
                raise ValueError(f"Quota not found: {quota_id}")

            # Reset period using model method
            quota.reset_period(new_period_start, new_period_end)

            await db_session.flush()
            await db_session.refresh(quota)

            logger.info(f"Reset period for quota {quota_id}")
            return quota

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error resetting period for quota {quota_id}: {e}")
            await db_session.rollback()
            raise

    async def delete(self, quota_id: int, db_session: AsyncSession) -> bool:
        """
        Delete a token quota by its ID.

        Args:
            quota_id: Primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        try:
            quota = await self.get_by_id(quota_id, db_session)
            if not quota:
                return False

            await db_session.delete(quota)
            await db_session.flush()

            logger.info(f"Deleted token quota {quota_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting quota {quota_id}: {e}")
            await db_session.rollback()
            return False

    async def count(
        self,
        db_session: AsyncSession,
        user_id: Optional[int] = None
    ) -> int:
        """
        Count total token quotas.

        Args:
            db_session: Database session
            user_id: Optional user ID filter

        Returns:
            Total count of token quotas
        """
        try:
            stmt = select(func.count(TokenQuota.id))

            if user_id:
                stmt = stmt.where(TokenQuota.user_id == user_id)

            result = await db_session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting quotas: {e}")
            return 0

    async def exists_for_user(
        self,
        user_id: int,
        quota_name: str,
        db_session: AsyncSession
    ) -> bool:
        """
        Check if a quota exists for a user.

        Args:
            user_id: User ID
            quota_name: Quota name
            db_session: Database session

        Returns:
            True if exists, False otherwise
        """
        try:
            stmt = select(func.count(TokenQuota.id)).where(
                and_(
                    TokenQuota.user_id == user_id,
                    TokenQuota.name == quota_name
                )
            )

            result = await db_session.execute(stmt)
            count = result.scalar() or 0
            return count > 0
        except Exception as e:
            logger.error(f"Error checking quota existence: {e}")
            return False

"""
Token Quota Repository Interface

Abstract interface for TokenQuota repository operations following SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime


class ITokenQuotaRepository(ABC):
    """
    Abstract interface for TokenQuota repository operations.

    This interface defines the contract for TokenQuota data access operations,
    enabling dependency inversion and making services testable and flexible.
    """

    @abstractmethod
    async def create(
        self,
        quota: Any,
        db_session: Any
    ) -> Any:
        """
        Create a new token quota.

        Args:
            quota: TokenQuotaCreate schema with quota data
            db_session: Database session

        Returns:
            Created TokenQuota object

        Raises:
            ValueError: If validation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, quota_id: int, db_session: Any) -> Optional[Any]:
        """
        Retrieve a token quota by its primary key ID.

        Args:
            quota_id: Primary key ID
            db_session: Database session

        Returns:
            TokenQuota object or None if not found
        """
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: int,
        db_session: Any,
        quota_name: Optional[str] = None
    ) -> Optional[Any]:
        """
        Retrieve a token quota by user ID and optionally by name.

        Args:
            user_id: User ID
            db_session: Database session
            quota_name: Optional quota name filter

        Returns:
            TokenQuota object or None if not found
        """
        pass

    @abstractmethod
    async def get_by_user_all(
        self,
        user_id: int,
        db_session: Any,
        status: Optional[str] = None
    ) -> List[Any]:
        """
        Retrieve all quotas for a user.

        Args:
            user_id: User ID
            db_session: Database session
            status: Optional status filter

        Returns:
            List of TokenQuota objects
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Any]:
        """
        Retrieve all token quotas with optional filtering.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip
            status: Optional status filter

        Returns:
            List of TokenQuota objects
        """
        pass

    @abstractmethod
    async def get_active_quotas(
        self,
        db_session: Any,
        limit: int = 100
    ) -> List[Any]:
        """
        Retrieve all active token quotas.

        Args:
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of active TokenQuota objects
        """
        pass

    @abstractmethod
    async def get_exhausted_quotas(
        self,
        db_session: Any,
        limit: int = 100
    ) -> List[Any]:
        """
        Retrieve all exhausted token quotas.

        Args:
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of exhausted TokenQuota objects
        """
        pass

    @abstractmethod
    async def update(
        self,
        quota_id: int,
        updates: Dict[str, Any],
        db_session: Any
    ) -> Any:
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
        pass

    @abstractmethod
    async def update_usage(
        self,
        quota_id: int,
        tokens_used: int,
        db_session: Any
    ) -> Any:
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
        pass

    @abstractmethod
    async def reset_period(
        self,
        quota_id: int,
        new_period_start: datetime,
        new_period_end: Optional[datetime],
        db_session: Any
    ) -> Any:
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
        pass

    @abstractmethod
    async def delete(self, quota_id: int, db_session: Any) -> bool:
        """
        Delete a token quota by its ID.

        Args:
            quota_id: Primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def count(self, db_session: Any, user_id: Optional[int] = None) -> int:
        """
        Count total token quotas.

        Args:
            db_session: Database session
            user_id: Optional user ID filter

        Returns:
            Total count of token quotas
        """
        pass

    @abstractmethod
    async def exists_for_user(
        self,
        user_id: int,
        quota_name: str,
        db_session: Any
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
        pass

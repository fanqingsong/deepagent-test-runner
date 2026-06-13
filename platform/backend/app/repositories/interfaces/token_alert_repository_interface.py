"""
Token Alert Repository Interface

Abstract interface for TokenAlert repository operations following SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime


class ITokenAlertRepository(ABC):
    """
    Abstract interface for TokenAlert repository operations.

    This interface defines the contract for TokenAlert data access operations,
    enabling dependency inversion and making services testable and flexible.
    """

    @abstractmethod
    async def create(
        self,
        alert: Any,
        db_session: Any
    ) -> Any:
        """
        Create a new token alert.

        Args:
            alert: TokenAlertCreate schema with alert data
            db_session: Database session

        Returns:
            Created TokenAlert object

        Raises:
            ValueError: If validation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, alert_id: int, db_session: Any) -> Optional[Any]:
        """
        Retrieve a token alert by its primary key ID.

        Args:
            alert_id: Primary key ID
            db_session: Database session

        Returns:
            TokenAlert object or None if not found
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """
        Retrieve all token alerts.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TokenAlert objects
        """
        pass

    @abstractmethod
    async def get_active_alerts(
        self,
        db_session: Any,
        budget_id: Optional[int] = None,
        quota_id: Optional[int] = None,
        user_id: Optional[int] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[Any]:
        """
        Retrieve active (unacknowledged) alerts.

        Args:
            db_session: Database session
            budget_id: Optional budget ID filter
            quota_id: Optional quota ID filter
            user_id: Optional user ID filter
            severity: Optional severity filter
            limit: Maximum number of records to return

        Returns:
            List of active TokenAlert objects
        """
        pass

    @abstractmethod
    async def get_recent_alerts(
        self,
        budget_id: Optional[int] = None,
        quota_id: Optional[int] = None,
        alert_type: Optional[str] = None,
        since: Optional[datetime] = None,
        db_session: Any = None,
        limit: int = 10
    ) -> List[Any]:
        """
        Retrieve recent alerts within a time period.

        Args:
            budget_id: Optional budget ID filter
            quota_id: Optional quota ID filter
            alert_type: Optional alert type filter
            since: Start time for recent alerts
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of recent TokenAlert objects
        """
        pass

    @abstractmethod
    async def get_alerts_since(
        self,
        since: datetime,
        db_session: Any,
        budget_id: Optional[int] = None,
        quota_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Any]:
        """
        Retrieve alerts created since a specific time.

        Args:
            since: Start time
            db_session: Database session
            budget_id: Optional budget ID filter
            quota_id: Optional quota ID filter
            user_id: Optional user ID filter
            limit: Maximum number of records to return

        Returns:
            List of TokenAlert objects
        """
        pass

    @abstractmethod
    async def acknowledge(
        self,
        alert_id: int,
        user_id: int,
        db_session: Any
    ) -> Any:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            user_id: User ID acknowledging
            db_session: Database session

        Returns:
            Updated TokenAlert object

        Raises:
            ValueError: If alert not found
        """
        pass

    @abstractmethod
    async def resolve(
        self,
        alert_id: int,
        db_session: Any
    ) -> Any:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID
            db_session: Database session

        Returns:
            Updated TokenAlert object

        Raises:
            ValueError: If alert not found
        """
        pass

    @abstractmethod
    async def update(
        self,
        alert_id: int,
        updates: Dict[str, Any],
        db_session: Any
    ) -> Any:
        """
        Update a token alert.

        Args:
            alert_id: Primary key ID
            updates: Dictionary of fields to update
            db_session: Database session

        Returns:
            Updated TokenAlert object

        Raises:
            ValueError: If alert not found
        """
        pass

    @abstractmethod
    async def delete(self, alert_id: int, db_session: Any) -> bool:
        """
        Delete a token alert by its ID.

        Args:
            alert_id: Primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def count(self, db_session: Any, acknowledged: Optional[bool] = None) -> int:
        """
        Count total token alerts.

        Args:
            db_session: Database session
            acknowledged: Optional acknowledgment status filter

        Returns:
            Total count of token alerts
        """
        pass

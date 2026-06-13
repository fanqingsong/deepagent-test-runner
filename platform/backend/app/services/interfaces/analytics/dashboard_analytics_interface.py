"""
Dashboard Analytics Interface

Defines the contract for dashboard summary operations.
Following Interface Segregation Principle - focused, single-purpose interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class IDashboardAnalytics(ABC):
    """
    Interface for dashboard summary operations.

    This interface focuses only on dashboard-level aggregations
    and summary statistics, following Interface Segregation Principle.
    """

    @abstractmethod
    async def get_dashboard_summary(
        self,
        days: int = 30,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get dashboard summary statistics.

        Args:
            days: Number of days to look back
            user_id: User ID for filtering (None for admin)
            is_admin: Whether user is admin
            db: Optional database session

        Returns:
            Dictionary containing summary statistics
        """
        pass

    @abstractmethod
    async def get_total_test_definitions(
        self,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        db: Optional[AsyncSession] = None
    ) -> int:
        """
        Get total count of test definitions.

        Args:
            user_id: User ID for filtering (None for admin)
            is_admin: Whether user is admin
            db: Optional database session

        Returns:
            Total count of test definitions
        """
        pass

    @abstractmethod
    async def get_test_runs_by_day(
        self,
        days: int = 30,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get test runs grouped by day.

        Args:
            days: Number of days to look back
            user_id: User ID for filtering (None for admin)
            is_admin: Whether user is admin
            db: Optional database session

        Returns:
            List of daily test run statistics
        """
        pass

"""
Suite Analytics Interface

Defines the contract for suite analytics operations.
Following Interface Segregation Principle - focused, single-purpose interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class ISuiteAnalytics(ABC):
    """
    Interface for suite analytics operations.

    This interface focuses only on test suite analytics and reporting,
    following Interface Segregation Principle.
    """

    @abstractmethod
    async def get_suite_dashboard_summary(
        self,
        days: int = 30,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Get suite dashboard summary statistics.

        Args:
            days: Number of days to look back
            user_id: User ID for filtering (None for admin)
            is_admin: Whether user is admin
            db: Optional database session

        Returns:
            Dictionary containing suite summary statistics
        """
        pass

    @abstractmethod
    async def get_suites_with_latest_run(
        self,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get test suites with their latest run information.

        Args:
            user_id: User ID for filtering (None for admin)
            is_admin: Whether user is admin
            db: Optional database session

        Returns:
            List of test suites with latest run data
        """
        pass

    @abstractmethod
    async def get_suite_run_timeline(
        self,
        suite_id: int,
        limit: int = 10,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get timeline of suite runs.

        Args:
            suite_id: Test suite ID
            limit: Maximum number of runs to return
            db: Optional database session

        Returns:
            List of suite runs in timeline order
        """
        pass

    @abstractmethod
    async def get_suite_run_with_test_cases(
        self,
        run_id: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get suite run with associated test cases.

        Args:
            run_id: Suite run identifier
            db: Optional database session

        Returns:
            Suite run data with test cases, or None if not found
        """
        pass

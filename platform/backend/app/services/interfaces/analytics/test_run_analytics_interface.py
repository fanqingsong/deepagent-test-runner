"""
Test Run Analytics Interface

Defines the contract for test run data retrieval operations.
Following Interface Segregation Principle - focused, single-purpose interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class ITestRunAnalytics(ABC):
    """
    Interface for test run data retrieval operations.

    This interface focuses only on test run queries and retrieval,
    following Interface Segregation Principle.
    """

    @abstractmethod
    async def get_recent_test_runs(
        self,
        limit: int = 100,
        user_id: Optional[int] = None,
        is_admin: bool = False,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent test runs with test definition names.

        Args:
            limit: Maximum number of runs to return
            user_id: User ID for filtering (None for admin)
            is_admin: Whether user is admin
            db: Optional database session

        Returns:
            List of recent test runs
        """
        pass

    @abstractmethod
    async def get_test_cases_for_run(
        self,
        run_id: str,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get detailed test cases for a specific test run.

        Args:
            run_id: Run identifier
            db: Optional database session

        Returns:
            List of test cases with results
        """
        pass

    @abstractmethod
    async def get_test_runs_for_app(
        self,
        app_id: int,
        limit: int = 50,
        offset: int = 0,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get test runs for a specific application.

        Args:
            app_id: Application ID
            limit: Maximum number of runs to return
            offset: Number of runs to skip
            db: Optional database session

        Returns:
            List of test runs for the application
        """
        pass

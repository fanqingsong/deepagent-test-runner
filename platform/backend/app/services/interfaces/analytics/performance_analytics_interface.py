"""
Performance Analytics Interface

Defines the contract for performance analysis operations.
Following Interface Segregation Principle - focused, single-purpose interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


class IPerformanceAnalytics(ABC):
    """
    Interface for performance analysis operations.

    This interface focuses only on performance metrics and analysis,
    following Interface Segregation Principle.
    """

    @abstractmethod
    async def get_slowest_tests(
        self,
        limit: int = 20,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get slowest tests.

        Args:
            limit: Maximum number of tests to return
            db: Optional database session

        Returns:
            List of slowest tests with durations
        """
        pass

    @abstractmethod
    async def get_flaky_tests(
        self,
        days: int = 30,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get flaky tests (inconsistent results).

        Args:
            days: Number of days to look back
            db: Optional database session

        Returns:
            List of flaky tests with inconsistency metrics
        """
        pass

    @abstractmethod
    async def get_failure_patterns(
        self,
        limit: int = 10,
        db: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get common failure patterns.

        Args:
            limit: Maximum number of patterns to return
            db: Optional database session

        Returns:
            List of failure patterns
        """
        pass

"""
Test Run Repository Interface

Abstract interface for TestRun repository operations following SOLID principles.
This enables Dependency Inversion - services depend on abstractions, not concretions.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime


class ITestRunRepository(ABC):
    """
    Abstract interface for TestRun repository operations.

    This interface defines the contract for TestRun data access operations,
    enabling dependency inversion and making services testable and flexible.
    """

    @abstractmethod
    async def create(
        self,
        run_id: str,
        test_definition_id: Optional[int],
        start_time_ms: int,
        db_session: Any
    ) -> Any:
        """
        Create a new test run record.

        Args:
            run_id: Unique run identifier
            test_definition_id: Test definition ID
            start_time_ms: Start time in milliseconds
            db_session: Database session

        Returns:
            Created TestRun object

        Raises:
            ValueError: If validation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, run_id: str, db_session: Any) -> Optional[Any]:
        """
        Retrieve a test run by its run_id.

        Args:
            run_id: Unique run identifier
            db_session: Database session

        Returns:
            TestRun object or None if not found
        """
        pass

    @abstractmethod
    async def get_by_pk(self, pk: int, db_session: Any) -> Optional[Any]:
        """
        Retrieve a test run by its primary key.

        Args:
            pk: Primary key ID
            db_session: Database session

        Returns:
            TestRun object or None if not found
        """
        pass

    @abstractmethod
    async def update_status(
        self,
        run_id: str,
        status: str,
        db_session: Any,
        start_time_ms: Optional[int] = None,
        end_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Any:
        """
        Update test run status and optionally timestamps.

        Args:
            run_id: Unique run identifier
            status: New status value
            db_session: Database session
            start_time_ms: Optional start time in milliseconds
            end_time_ms: Optional end time in milliseconds
            error_message: Optional error message for failed runs

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If test run not found or status transition invalid
        """
        pass

    @abstractmethod
    async def update_results(
        self,
        run_id: str,
        results: Dict[str, Any],
        db_session: Any
    ) -> Any:
        """
        Update test run with execution results.

        Args:
            run_id: Unique run identifier
            results: Dictionary containing test results including:
                - total_tests: Total number of tests
                - passed: Number of passed tests
                - failed: Number of failed tests
                - skipped: Number of skipped tests
                - total_duration_ms: Total duration in milliseconds
                - status: Final status
                - error_message: Optional error message
                - start_time_ms: Start time in milliseconds
                - end_time_ms: End time in milliseconds
                - test_definition_id: Test definition ID
            db_session: Database session

        Returns:
            Updated TestRun object

        Raises:
            ValueError: If test run not found
        """
        pass

    @abstractmethod
    async def get_by_test_definition_id(
        self,
        test_definition_id: int,
        db_session: Any,
        limit: int = 10,
        offset: int = 0
    ) -> List[Any]:
        """
        Retrieve test runs for a specific test definition.

        Args:
            test_definition_id: Test definition ID
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TestRun objects, ordered by created_at DESC
        """
        pass

    @abstractmethod
    async def get_pending_runs(self, db_session: Any, limit: int = 100) -> List[Any]:
        """
        Retrieve all pending test runs.

        Args:
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of pending TestRun objects, ordered by created_at ASC
        """
        pass

    @abstractmethod
    async def get_recent_runs(
        self,
        db_session: Any,
        days: int = 7,
        limit: int = 100
    ) -> List[Any]:
        """
        Retrieve recent test runs within the specified time window.

        Args:
            db_session: Database session
            days: Number of days to look back (default: 7)
            limit: Maximum number of records to return

        Returns:
            List of TestRun objects, ordered by created_at DESC
        """
        pass

    @abstractmethod
    async def count_by_status(self, status: str, db_session: Any) -> int:
        """
        Count test runs by status.

        Args:
            status: Status to count (e.g., 'pending', 'running', 'passed', 'failed')
            db_session: Database session

        Returns:
            Count of test runs with the specified status
        """
        pass

    @abstractmethod
    async def delete(self, run_id: str, db_session: Any) -> bool:
        """
        Delete a test run by its run_id.

        Args:
            run_id: Unique run identifier
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Any]:
        """
        Retrieve all test runs with optional filtering.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip
            status_filter: Optional status filter

        Returns:
            List of TestRun objects, ordered by created_at DESC
        """
        pass

    @abstractmethod
    async def exists(self, run_id: str, db_session: Any) -> bool:
        """
        Check if a test run exists.

        Args:
            run_id: Unique run identifier
            db_session: Database session

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_stats_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        db_session: Any
    ) -> Dict[str, Any]:
        """
        Get test run statistics for a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            db_session: Database session

        Returns:
            Dictionary containing statistics:
                - total_runs: Total number of runs
                - passed: Number of passed runs
                - failed: Number of failed runs
                - avg_duration: Average duration in seconds
        """
        pass

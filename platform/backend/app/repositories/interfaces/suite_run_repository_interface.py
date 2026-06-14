"""
Suite Run Repository Interface

Defines the contract for suite run data access operations.
Following the Dependency Inversion Principle and Repository Pattern.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.suite_run import SuiteRun, SuiteRunEntry


class ISuiteRunRepository(ABC):
    """
    Interface for suite run repository operations.

    This interface defines the contract for data access operations
    related to suite runs and their entries, following the Repository Pattern.
    """

    @abstractmethod
    async def create(
        self,
        suite_id: int,
        run_id: str,
        status: str,
        execution_mode: str,
        total_tests: int,
        environment: dict,
        triggered_by: str,
        start_time: int,
        db_session: Optional[AsyncSession] = None
    ) -> SuiteRun:
        """
        Create a new suite run.

        Args:
            suite_id: Test suite ID
            run_id: Unique run identifier
            status: Initial status
            execution_mode: Execution mode (sequential, parallel, etc.)
            total_tests: Total number of tests in suite
            environment: Environment variables
            triggered_by: Trigger source
            start_time: Start timestamp in milliseconds
            db_session: Database session

        Returns:
            Created SuiteRun object
        """
        pass

    @abstractmethod
    async def get_by_run_id(
        self,
        run_id: str,
        db_session: Optional[AsyncSession] = None,
        load_entries: bool = False
    ) -> Optional[SuiteRun]:
        """
        Get a suite run by run_id.

        Args:
            run_id: Suite run identifier
            db_session: Database session
            load_entries: Whether to load associated entries

        Returns:
            SuiteRun object or None if not found
        """
        pass

    @abstractmethod
    async def get_by_id(
        self,
        suite_run_id: int,
        db_session: Optional[AsyncSession] = None,
        load_entries: bool = False
    ) -> Optional[SuiteRun]:
        """
        Get a suite run by database ID.

        Args:
            suite_run_id: Suite run database ID
            db_session: Database session
            load_entries: Whether to load associated entries

        Returns:
            SuiteRun object or None if not found
        """
        pass

    @abstractmethod
    async def update_status(
        self,
        suite_run_id: int,
        status: str,
        db_session: Optional[AsyncSession] = None,
        end_time: Optional[int] = None,
        error: Optional[str] = None
    ) -> Optional[SuiteRun]:
        """
        Update suite run status.

        Args:
            suite_run_id: Suite run database ID
            status: New status
            end_time: Optional end timestamp in milliseconds
            error: Optional error message
            db_session: Database session

        Returns:
            Updated SuiteRun object or None if not found
        """
        pass

    @abstractmethod
    async def update_final_results(
        self,
        suite_run_id: int,
        passed: int,
        failed: int,
        skipped: int,
        total_duration: Optional[int],
        db_session: Optional[AsyncSession] = None
    ) -> Optional[SuiteRun]:
        """
        Update suite run with final execution results.

        Args:
            suite_run_id: Suite run database ID
            passed: Number of passed tests
            failed: Number of failed tests
            skipped: Number of skipped tests
            total_duration: Optional total duration in milliseconds
            db_session: Database session

        Returns:
            Updated SuiteRun object or None if not found
        """
        pass

    @abstractmethod
    async def list_by_suite_id(
        self,
        suite_id: int,
        skip: int = 0,
        limit: int = 50,
        db_session: Optional[AsyncSession] = None
    ) -> List[SuiteRun]:
        """
        List suite runs for a specific suite.

        Args:
            suite_id: Test suite ID
            skip: Number of runs to skip
            limit: Maximum number of runs to return
            db_session: Database session

        Returns:
            List of SuiteRun objects
        """
        pass

    @abstractmethod
    async def get_entries(
        self,
        suite_run_id: int,
        db_session: Optional[AsyncSession] = None
    ) -> List[SuiteRunEntry]:
        """
        Get all entries for a suite run.

        Args:
            suite_run_id: Suite run database ID
            db_session: Database session

        Returns:
            List of SuiteRunEntry objects
        """
        pass

    @abstractmethod
    async def create_entries(
        self,
        suite_run_id: int,
        entries: List[dict],
        db_session: Optional[AsyncSession] = None
    ) -> List[SuiteRunEntry]:
        """
        Create suite run entries.

        Args:
            suite_run_id: Suite run database ID
            entries: List of entry dictionaries
            db_session: Database session

        Returns:
            List of created SuiteRunEntry objects
        """
        pass

    @abstractmethod
    async def update_entry_status(
        self,
        entry_id: int,
        status: str,
        started_at: Optional[int] = None,
        finished_at: Optional[int] = None,
        test_run_id: Optional[str] = None,
        error_message: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        duration: Optional[int] = None
    ) -> Optional[SuiteRunEntry]:
        """
        Update suite run entry status.

        Args:
            entry_id: Entry database ID
            status: New status
            started_at: Optional start timestamp in milliseconds
            finished_at: Optional finish timestamp in milliseconds
            test_run_id: Optional associated test run ID
            error_message: Optional error message
            duration: Optional execution duration in milliseconds
            db_session: Database session

        Returns:
            Updated SuiteRunEntry object or None if not found
        """
        pass

    @abstractmethod
    async def cancel_pending_entries(
        self,
        suite_run_id: int,
        from_order: int,
        db_session: Optional[AsyncSession] = None
    ) -> int:
        """
        Cancel all pending entries from a specific order.

        Args:
            suite_run_id: Suite run database ID
            from_order: Entry order to start canceling from
            db_session: Database session

        Returns:
            Number of entries canceled
        """
        pass

"""
Schedule Repository Interface

Abstract interface for Schedule repository operations following SOLID principles.
This enables Dependency Inversion - services depend on abstractions, not concretions.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime


class IScheduleRepository(ABC):
    """
    Abstract interface for Schedule repository operations.

    This interface defines the contract for Schedule data access operations,
    enabling dependency inversion and making services testable and flexible.
    """

    @abstractmethod
    async def create(
        self,
        schedule_data: Dict[str, Any],
        db_session: Any
    ) -> Any:
        """
        Create a new schedule record.

        Args:
            schedule_data: Dictionary containing schedule fields:
                - name: Schedule name
                - schedule_type: Type of schedule (single, suite, tag)
                - test_definition_ids: List of test definition IDs
                - test_definition_id: Optional single test definition ID
                - test_suite_id: Optional test suite ID
                - tag_filter: Optional tag filter
                - preset_type: Optional preset type
                - cron_expression: Cron expression for scheduling
                - timezone: Timezone for schedule (default: UTC)
                - environment_overrides: Environment configuration overrides
                - is_active: Active status (default: True)
                - allow_concurrent: Allow concurrent executions (default: False)
                - max_retries: Maximum retry attempts (default: 0)
                - retry_interval_seconds: Retry interval in seconds (default: 60)
                - run_config_id: Optional run configuration ID
                - created_by: Optional user ID who created the schedule
            db_session: Database session

        Returns:
            Created Schedule object

        Raises:
            ValueError: If validation fails or cron expression is invalid
        """
        pass

    @abstractmethod
    async def get_by_id(self, schedule_id: int, db_session: Any) -> Optional[Any]:
        """
        Retrieve a schedule by its primary key ID.

        Args:
            schedule_id: Schedule primary key ID
            db_session: Database session

        Returns:
            Schedule object or None if not found
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        db_session: Any,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False
    ) -> List[Any]:
        """
        Retrieve all schedules with optional filtering.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip
            active_only: If True, only return active schedules

        Returns:
            List of Schedule objects, ordered by created_at DESC
        """
        pass

    @abstractmethod
    async def get_active_schedules(self, db_session: Any) -> List[Any]:
        """
        Retrieve all active schedules.

        Args:
            db_session: Database session

        Returns:
            List of active Schedule objects, ordered by next_run_time ASC
        """
        pass

    @abstractmethod
    async def get_by_test_definition_id(
        self,
        definition_id: int,
        db_session: Any
    ) -> List[Any]:
        """
        Retrieve all schedules for a specific test definition.

        Args:
            definition_id: Test definition ID
            db_session: Database session

        Returns:
            List of Schedule objects associated with the test definition
        """
        pass

    @abstractmethod
    async def get_by_suite_id(self, suite_id: int, db_session: Any) -> List[Any]:
        """
        Retrieve all schedules for a specific test suite.

        Args:
            suite_id: Test suite ID
            db_session: Database session

        Returns:
            List of Schedule objects associated with the test suite
        """
        pass

    @abstractmethod
    async def update(
        self,
        schedule_id: int,
        updates: Dict[str, Any],
        db_session: Any
    ) -> Any:
        """
        Update a schedule with new values.

        Args:
            schedule_id: Schedule primary key ID
            updates: Dictionary of fields to update:
                - name: Optional new name
                - cron_expression: Optional new cron expression
                - timezone: Optional new timezone
                - environment_overrides: Optional new environment overrides
                - is_active: Optional new active status
                - allow_concurrent: Optional new concurrent setting
                - max_retries: Optional new max retries
                - retry_interval_seconds: Optional new retry interval
                - test_definition_ids: Optional new test definition IDs
            db_session: Database session

        Returns:
            Updated Schedule object

        Raises:
            ValueError: If schedule not found or validation fails
        """
        pass

    @abstractmethod
    async def update_next_run_time(
        self,
        schedule_id: int,
        next_run_time: datetime,
        db_session: Any
    ) -> Any:
        """
        Update the next run time for a schedule.

        Args:
            schedule_id: Schedule primary key ID
            next_run_time: Next scheduled execution time
            db_session: Database session

        Returns:
            Updated Schedule object

        Raises:
            ValueError: If schedule not found
        """
        pass

    @abstractmethod
    async def activate(self, schedule_id: int, db_session: Any) -> Any:
        """
        Activate a schedule.

        Args:
            schedule_id: Schedule primary key ID
            db_session: Database session

        Returns:
            Updated Schedule object with is_active=True

        Raises:
            ValueError: If schedule not found
        """
        pass

    @abstractmethod
    async def deactivate(self, schedule_id: int, db_session: Any) -> Any:
        """
        Deactivate a schedule.

        Args:
            schedule_id: Schedule primary key ID
            db_session: Database session

        Returns:
            Updated Schedule object with is_active=False

        Raises:
            ValueError: If schedule not found
        """
        pass

    @abstractmethod
    async def delete(self, schedule_id: int, db_session: Any) -> bool:
        """
        Delete a schedule by its primary key ID.

        Args:
            schedule_id: Schedule primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def get_by_type(
        self,
        schedule_type: str,
        db_session: Any,
        active_only: bool = False
    ) -> List[Any]:
        """
        Retrieve schedules by type.

        Args:
            schedule_type: Schedule type (single, suite, tag)
            db_session: Database session
            active_only: If True, only return active schedules

        Returns:
            List of Schedule objects of the specified type
        """
        pass

    @abstractmethod
    async def get_due_schedules(
        self,
        before_time: datetime,
        db_session: Any
    ) -> List[Any]:
        """
        Retrieve schedules that are due for execution.

        Args:
            before_time: Time threshold for due schedules
            db_session: Database session

        Returns:
            List of active Schedule objects with next_run_time <= before_time
        """
        pass

    @abstractmethod
    async def count(self, db_session: Any) -> int:
        """
        Count all schedules.

        Args:
            db_session: Database session

        Returns:
            Total number of schedules
        """
        pass

    @abstractmethod
    async def count_by_status(self, is_active: bool, db_session: Any) -> int:
        """
        Count schedules by active status.

        Args:
            is_active: Active status to count
            db_session: Database session

        Returns:
            Number of schedules with the specified active status
        """
        pass

    @abstractmethod
    async def update_last_run_time(
        self,
        schedule_id: int,
        last_run_time: datetime,
        db_session: Any
    ) -> Any:
        """
        Update the last run time for a schedule.

        Args:
            schedule_id: Schedule primary key ID
            last_run_time: Last execution time
            db_session: Database session

        Returns:
            Updated Schedule object

        Raises:
            ValueError: If schedule not found
        """
        pass

    @abstractmethod
    async def exists(self, schedule_id: int, db_session: Any) -> bool:
        """
        Check if a schedule exists.

        Args:
            schedule_id: Schedule primary key ID
            db_session: Database session

        Returns:
            True if exists, False otherwise
        """
        pass

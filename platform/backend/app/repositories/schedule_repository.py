"""
Schedule Repository Implementation

SQLAlchemy implementation of Schedule repository following async patterns.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, desc, asc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.schedule import Schedule
from app.repositories.interfaces.schedule_repository_interface import IScheduleRepository

logger = logging.getLogger(__name__)


class SQLAlchemyScheduleRepository(IScheduleRepository):
    """
    SQLAlchemy implementation of Schedule repository.

    Handles all database operations for Schedule model using async SQLAlchemy patterns.
    Provides proper error handling, logging, and transaction management.
    """

    def __init__(self):
        """Initialize the repository."""
        self._model_class = Schedule

    async def create(
        self,
        schedule_data: Dict[str, Any],
        db_session: AsyncSession
    ) -> Schedule:
        """
        Create a new schedule record.

        Args:
            schedule_data: Dictionary containing schedule fields
            db_session: Database session

        Returns:
            Created Schedule object

        Raises:
            ValueError: If validation fails or cron expression is invalid
        """
        # Validate cron expression
        cron_expression = schedule_data.get('cron_expression')
        if not cron_expression:
            raise ValueError("cron_expression is required")

        # Validate schedule_type
        schedule_type = schedule_data.get('schedule_type')
        if not schedule_type:
            raise ValueError("schedule_type is required")

        # Create new schedule
        schedule = Schedule(
            name=schedule_data.get('name'),
            schedule_type=schedule_type,
            test_definition_ids=schedule_data.get('test_definition_ids', []),
            test_definition_id=schedule_data.get('test_definition_id'),
            test_suite_id=schedule_data.get('test_suite_id'),
            tag_filter=schedule_data.get('tag_filter'),
            preset_type=schedule_data.get('preset_type'),
            cron_expression=cron_expression,
            timezone=schedule_data.get('timezone', 'UTC'),
            environment_overrides=schedule_data.get('environment_overrides', {}),
            is_active=schedule_data.get('is_active', True),
            allow_concurrent=schedule_data.get('allow_concurrent', False),
            max_retries=schedule_data.get('max_retries', 0),
            retry_interval_seconds=schedule_data.get('retry_interval_seconds', 60),
            run_config_id=schedule_data.get('run_config_id'),
            created_by=schedule_data.get('created_by')
        )

        try:
            db_session.add(schedule)
            await db_session.flush()
            await db_session.refresh(schedule)

            logger.info(f"Created schedule {schedule.id}: {schedule.name}")
            return schedule

        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            await db_session.rollback()
            raise

    async def get_by_id(
        self,
        schedule_id: int,
        db_session: AsyncSession
    ) -> Optional[Schedule]:
        """
        Retrieve a schedule by its primary key ID.

        Args:
            schedule_id: Schedule primary key ID
            db_session: Database session

        Returns:
            Schedule object or None if not found
        """
        try:
            stmt = select(Schedule).where(Schedule.id == schedule_id)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving schedule {schedule_id}: {e}")
            return None

    async def get_all(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        active_only: bool = False
    ) -> List[Schedule]:
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
        try:
            stmt = select(Schedule)

            if active_only:
                stmt = stmt.where(Schedule.is_active == True)

            stmt = stmt.order_by(desc(Schedule.created_at)).offset(offset).limit(limit)
            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error retrieving schedules: {e}")
            return []

    async def get_active_schedules(self, db_session: AsyncSession) -> List[Schedule]:
        """
        Retrieve all active schedules.

        Args:
            db_session: Database session

        Returns:
            List of active Schedule objects, ordered by next_run_time ASC
        """
        try:
            stmt = select(Schedule).where(
                Schedule.is_active == True
            ).order_by(asc(Schedule.next_run_time))

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error retrieving active schedules: {e}")
            return []

    async def get_by_test_definition_id(
        self,
        definition_id: int,
        db_session: AsyncSession
    ) -> List[Schedule]:
        """
        Retrieve all schedules for a specific test definition.

        Args:
            definition_id: Test definition ID
            db_session: Database session

        Returns:
            List of Schedule objects associated with the test definition
        """
        try:
            # Check both test_definition_id and test_definition_ids array
            stmt = select(Schedule).where(
                and_(
                    Schedule.is_active == True,
                    (
                        (Schedule.test_definition_id == definition_id) |
                        (definition_id == Schedule.test_definition_ids[0])  # ANY element in array
                    )
                )
            )

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error retrieving schedules for test definition {definition_id}: {e}")
            return []

    async def get_by_suite_id(
        self,
        suite_id: int,
        db_session: AsyncSession
    ) -> List[Schedule]:
        """
        Retrieve all schedules for a specific test suite.

        Args:
            suite_id: Test suite ID
            db_session: Database session

        Returns:
            List of Schedule objects associated with the test suite
        """
        try:
            stmt = select(Schedule).where(
                and_(
                    Schedule.is_active == True,
                    Schedule.test_suite_id == suite_id
                )
            ).order_by(desc(Schedule.created_at))

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error retrieving schedules for test suite {suite_id}: {e}")
            return []

    async def update(
        self,
        schedule_id: int,
        updates: Dict[str, Any],
        db_session: AsyncSession
    ) -> Schedule:
        """
        Update a schedule with new values.

        Args:
            schedule_id: Schedule primary key ID
            updates: Dictionary of fields to update
            db_session: Database session

        Returns:
            Updated Schedule object

        Raises:
            ValueError: If schedule not found or validation fails
        """
        schedule = await self.get_by_id(schedule_id, db_session)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        try:
            # Update allowed fields
            allowed_fields = {
                'name', 'cron_expression', 'timezone', 'environment_overrides',
                'is_active', 'allow_concurrent', 'max_retries',
                'retry_interval_seconds', 'test_definition_ids'
            }

            for field, value in updates.items():
                if field in allowed_fields and hasattr(schedule, field):
                    setattr(schedule, field, value)

            await db_session.flush()
            await db_session.refresh(schedule)

            logger.info(f"Updated schedule {schedule_id}")
            return schedule

        except Exception as e:
            logger.error(f"Error updating schedule {schedule_id}: {e}")
            await db_session.rollback()
            raise

    async def update_next_run_time(
        self,
        schedule_id: int,
        next_run_time: datetime,
        db_session: AsyncSession
    ) -> Schedule:
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
        schedule = await self.get_by_id(schedule_id, db_session)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        try:
            schedule.next_run_time = next_run_time
            await db_session.flush()
            await db_session.refresh(schedule)

            logger.debug(f"Updated next_run_time for schedule {schedule_id} to {next_run_time}")
            return schedule

        except Exception as e:
            logger.error(f"Error updating next_run_time for schedule {schedule_id}: {e}")
            await db_session.rollback()
            raise

    async def activate(self, schedule_id: int, db_session: AsyncSession) -> Schedule:
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
        schedule = await self.get_by_id(schedule_id, db_session)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        try:
            schedule.is_active = True
            await db_session.flush()
            await db_session.refresh(schedule)

            logger.info(f"Activated schedule {schedule_id}")
            return schedule

        except Exception as e:
            logger.error(f"Error activating schedule {schedule_id}: {e}")
            await db_session.rollback()
            raise

    async def deactivate(
        self,
        schedule_id: int,
        db_session: AsyncSession
    ) -> Schedule:
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
        schedule = await self.get_by_id(schedule_id, db_session)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        try:
            schedule.is_active = False
            await db_session.flush()
            await db_session.refresh(schedule)

            logger.info(f"Deactivated schedule {schedule_id}")
            return schedule

        except Exception as e:
            logger.error(f"Error deactivating schedule {schedule_id}: {e}")
            await db_session.rollback()
            raise

    async def delete(self, schedule_id: int, db_session: AsyncSession) -> bool:
        """
        Delete a schedule by its primary key ID.

        Args:
            schedule_id: Schedule primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        schedule = await self.get_by_id(schedule_id, db_session)
        if not schedule:
            return False

        try:
            await db_session.delete(schedule)
            await db_session.flush()

            logger.info(f"Deleted schedule {schedule_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting schedule {schedule_id}: {e}")
            await db_session.rollback()
            return False

    async def get_by_type(
        self,
        schedule_type: str,
        db_session: AsyncSession,
        active_only: bool = False
    ) -> List[Schedule]:
        """
        Retrieve schedules by type.

        Args:
            schedule_type: Schedule type (single, suite, tag)
            db_session: Database session
            active_only: If True, only return active schedules

        Returns:
            List of Schedule objects of the specified type
        """
        try:
            stmt = select(Schedule).where(Schedule.schedule_type == schedule_type)

            if active_only:
                stmt = stmt.where(Schedule.is_active == True)

            stmt = stmt.order_by(desc(Schedule.created_at))

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error retrieving schedules of type {schedule_type}: {e}")
            return []

    async def get_due_schedules(
        self,
        before_time: datetime,
        db_session: AsyncSession
    ) -> List[Schedule]:
        """
        Retrieve schedules that are due for execution.

        Args:
            before_time: Time threshold for due schedules
            db_session: Database session

        Returns:
            List of active Schedule objects with next_run_time <= before_time
        """
        try:
            stmt = select(Schedule).where(
                and_(
                    Schedule.is_active == True,
                    Schedule.next_run_time <= before_time
                )
            ).order_by(asc(Schedule.next_run_time))

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error retrieving due schedules: {e}")
            return []

    async def count(self, db_session: AsyncSession) -> int:
        """
        Count all schedules.

        Args:
            db_session: Database session

        Returns:
            Total number of schedules
        """
        try:
            stmt = select(func.count(Schedule.id))
            result = await db_session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting schedules: {e}")
            return 0

    async def count_by_status(
        self,
        is_active: bool,
        db_session: AsyncSession
    ) -> int:
        """
        Count schedules by active status.

        Args:
            is_active: Active status to count
            db_session: Database session

        Returns:
            Number of schedules with the specified active status
        """
        try:
            stmt = select(func.count(Schedule.id)).where(
                Schedule.is_active == is_active
            )
            result = await db_session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting schedules by status: {e}")
            return 0

    async def update_last_run_time(
        self,
        schedule_id: int,
        last_run_time: datetime,
        db_session: AsyncSession
    ) -> Schedule:
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
        schedule = await self.get_by_id(schedule_id, db_session)
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        try:
            schedule.last_run_time = last_run_time
            await db_session.flush()
            await db_session.refresh(schedule)

            logger.debug(f"Updated last_run_time for schedule {schedule_id} to {last_run_time}")
            return schedule

        except Exception as e:
            logger.error(f"Error updating last_run_time for schedule {schedule_id}: {e}")
            await db_session.rollback()
            raise

    async def exists(self, schedule_id: int, db_session: AsyncSession) -> bool:
        """
        Check if a schedule exists.

        Args:
            schedule_id: Schedule primary key ID
            db_session: Database session

        Returns:
            True if exists, False otherwise
        """
        try:
            stmt = select(func.count(Schedule.id)).where(Schedule.id == schedule_id)
            result = await db_session.execute(stmt)
            count = result.scalar() or 0
            return count > 0
        except Exception as e:
            logger.error(f"Error checking schedule existence: {e}")
            return False

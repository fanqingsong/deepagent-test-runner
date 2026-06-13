"""
Test Suite Schedule Synchronization Helper (Refactored with Repository Pattern)

This is an EXAMPLE of how to refactor code to use the Repository Pattern.
The original file (suite_schedule_helper.py) uses direct database access.
This version demonstrates how to use IScheduleRepository instead.

Migration Pattern:
1. Import IScheduleRepository from interfaces
2. Get repository from RepositoryFactory
3. Replace direct DB operations with repository methods
4. Maintain same functionality with better testability
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_suite import TestSuite
from app.repositories.repository_factory import RepositoryFactory
from app.repositories.interfaces.schedule_repository_interface import IScheduleRepository

logger = logging.getLogger(__name__)


async def sync_suite_schedule(
    db: AsyncSession,
    suite: TestSuite,
    schedule_repository: Optional[IScheduleRepository] = None
) -> None:
    """
    Create, update, or deactivate the linked Schedule record for a suite.

    This refactored version uses the Repository Pattern for better testability
    and separation of concerns.

    Args:
        db: Database session
        suite: TestSuite to sync schedule for
        schedule_repository: Optional IScheduleRepository (uses factory if not provided)
    """
    from app.services.temporal_schedule_service import create, update, pause

    # Use provided repository or get from factory
    if schedule_repository is None:
        schedule_repository = RepositoryFactory.get_schedule_repository()

    if suite.schedule_enabled and suite.cron_expression:
        # Only schedule approved suites
        if getattr(suite, "review_status", "approved") != "approved":
            logger.warning(f"Skipping schedule for unapproved suite {suite.id}")
            if suite.schedule_id:
                # Use repository to check if schedule exists
                if await schedule_repository.exists(suite.schedule_id, db):
                    await schedule_repository.deactivate(suite.schedule_id, db)
                    await pause(suite.schedule_id)
            return

        # Validate cron
        try:
            croniter(suite.cron_expression, datetime.now(timezone.utc))
        except (ValueError, KeyError):
            logger.warning(f"Invalid cron for suite {suite.id}: {suite.cron_expression}")
            return

        # Upsert linked schedule
        schedule = None
        if suite.schedule_id:
            # Use repository to get existing schedule
            schedule = await schedule_repository.get_by_id(suite.schedule_id, db)

        if schedule is None:
            # Create new schedule using repository
            schedule_data = {
                'name': f"{suite.name} (自动)",
                'schedule_type': 'suite',
                'test_definition_ids': suite.test_definition_ids or [],
                'test_suite_id': suite.id,
                'cron_expression': suite.cron_expression,
                'timezone': suite.timezone,
                'is_active': True,
                'allow_concurrent': suite.schedule_allow_concurrent,
                'max_retries': suite.schedule_max_retries,
                'retry_interval_seconds': suite.schedule_retry_interval,
                'created_by': int(suite.created_by) if suite.created_by else None,
            }

            schedule = await schedule_repository.create(schedule_data, db)
            suite.schedule_id = schedule.id

            # Sync to Temporal
            test_def_ids = suite.test_definition_ids or []
            if test_def_ids:
                await create(suite.schedule_id, suite.cron_expression, str(test_def_ids[0]), True)
        else:
            # Update existing schedule using repository
            updates = {
                'name': f"{suite.name} (自动)",
                'test_definition_ids': suite.test_definition_ids or [],
                'cron_expression': suite.cron_expression,
                'timezone': suite.timezone,
                'is_active': True,
                'allow_concurrent': suite.schedule_allow_concurrent,
                'max_retries': suite.schedule_max_retries,
                'retry_interval_seconds': suite.schedule_retry_interval,
            }

            schedule = await schedule_repository.update(schedule.id, updates, db)

            # Sync to Temporal
            test_def_ids = suite.test_definition_ids or []
            if test_def_ids:
                await update(suite.schedule_id, suite.cron_expression, str(test_def_ids[0]), True)

        # Calculate next run time
        try:
            cron = croniter(schedule.cron_expression, datetime.now(timezone.utc))
            next_time = cron.get_next(datetime)
            # Strip timezone info — PostgreSQL stores TIMESTAMP WITHOUT TIME ZONE
            next_run_time = next_time.replace(tzinfo=None) if next_time.tzinfo else next_time

            # Use repository to update next run time
            await schedule_repository.update_next_run_time(schedule.id, next_run_time, db)

            suite.next_run_time = next_run_time
        except Exception as e:
            logger.error(f"Failed to calculate next run time: {e}")

        # Sync last_run_time
        suite.last_run_time = schedule.last_run_time
    else:
        # Deactivate linked schedule if exists
        if suite.schedule_id:
            # Use repository to check if schedule exists
            if await schedule_repository.exists(suite.schedule_id, db):
                await schedule_repository.deactivate(suite.schedule_id, db)
                await pause(suite.schedule_id)

        suite.next_run_time = None


"""
MIGRATION COMPARISON:

BEFORE (Direct Database Access):
--------------------------------
from app.models.schedule import Schedule
from sqlalchemy import select

# Direct SQL query
result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
schedule = result.scalar_one_or_none()

# Direct object creation
schedule = Schedule(name="Test", schedule_type="suite", ...)
db.add(schedule)
await db.flush()

# Direct field updates
schedule.is_active = False
await db.flush()


AFTER (Repository Pattern):
----------------------------
from app.repositories.interfaces.schedule_repository_interface import IScheduleRepository

# Repository method call
schedule = await schedule_repository.get_by_id(schedule_id, db)

# Repository create method
schedule = await schedule_repository.create({
    'name': 'Test',
    'schedule_type': 'suite',
    ...
}, db)

# Repository update method
schedule = await schedule_repository.deactivate(schedule_id, db)


BENEFITS:
---------
✓ Better testability - can mock IScheduleRepository
✓ Separation of concerns - data access logic isolated
✓ Consistent interface - all repositories follow same pattern
✓ Error handling - centralized in repository
✓ Logging - centralized in repository
✓ Follows SOLID Dependency Inversion Principle


TESTING EXAMPLE:
----------------
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_sync_suite_schedule():
    # Create mock repository
    mock_repo = AsyncMock()
    mock_repo.create.return_value = Mock(id=1, name="Test Schedule")
    mock_repo.exists.return_value = True

    # Test with mock
    suite = TestSuite(id=1, name="Test Suite", ...)
    await sync_suite_schedule(db, suite, schedule_repository=mock_repo)

    # Verify repository was called
    mock_repo.create.assert_called_once()
"""

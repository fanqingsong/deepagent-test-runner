"""
Test Suite Schedule Synchronization Helper

Handles schedule creation, updates, and deactivation for test suites.
"""

import logging
from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import Schedule
from app.models.test_suite import TestSuite

logger = logging.getLogger(__name__)


async def sync_suite_schedule(db: AsyncSession, suite: TestSuite) -> None:
    """Create, update, or deactivate the linked Schedule record for a suite."""
    from app.services.temporal_schedule_service import create, update, pause

    if suite.schedule_enabled and suite.cron_expression:
        # Only schedule approved suites
        if getattr(suite, "review_status", "approved") != "approved":
            logger.warning(f"Skipping schedule for unapproved suite {suite.id}")
            if suite.schedule_id:
                result = await db.execute(
                    select(Schedule).where(Schedule.id == suite.schedule_id)
                )
                schedule = result.scalar_one_or_none()
                if schedule:
                    schedule.is_active = False
                    await pause(suite.schedule_id)
            return

        # Validate cron
        try:
            croniter(suite.cron_expression, datetime.now(timezone.utc))
        except (ValueError, KeyError):
            logger.warning(f"Invalid cron for suite {suite.id}: {suite.cron_expression}")
            return

        # Upsert linked schedule
        if suite.schedule_id:
            result = await db.execute(
                select(Schedule).where(Schedule.id == suite.schedule_id)
            )
            schedule = result.scalar_one_or_none()
        else:
            schedule = None

        if schedule is None:
            schedule = Schedule(
                name=f"{suite.name} (自动)",
                schedule_type="suite",
                test_definition_ids=suite.test_definition_ids or [],
                test_suite_id=suite.id,
                cron_expression=suite.cron_expression,
                timezone=suite.timezone,
                is_active=True,
                allow_concurrent=suite.schedule_allow_concurrent,
                max_retries=suite.schedule_max_retries,
                retry_interval_seconds=suite.schedule_retry_interval,
                created_by=int(suite.created_by) if suite.created_by else None,
            )
            db.add(schedule)
            await db.flush()
            suite.schedule_id = schedule.id

            # Sync to Temporal
            test_def_ids = suite.test_definition_ids or []
            if test_def_ids:
                await create(suite.schedule_id, suite.cron_expression, str(test_def_ids[0]), True)
        else:
            schedule.name = f"{suite.name} (自动)"
            schedule.test_definition_ids = suite.test_definition_ids or []
            schedule.cron_expression = suite.cron_expression
            schedule.timezone = suite.timezone
            schedule.is_active = True
            schedule.allow_concurrent = suite.schedule_allow_concurrent
            schedule.max_retries = suite.schedule_max_retries
            schedule.retry_interval_seconds = suite.schedule_retry_interval

            # Sync to Temporal
            test_def_ids = suite.test_definition_ids or []
            if test_def_ids:
                await update(suite.schedule_id, suite.cron_expression, str(test_def_ids[0]), True)

        # Calculate next run time
        try:
            cron = croniter(schedule.cron_expression, datetime.now(timezone.utc))
            next_time = cron.get_next(datetime)
            # Strip timezone info — PostgreSQL stores TIMESTAMP WITHOUT TIME ZONE
            schedule.next_run_time = next_time.replace(tzinfo=None) if next_time.tzinfo else next_time
            suite.next_run_time = schedule.next_run_time
        except Exception as e:
            logger.error(f"Failed to calculate next run time: {e}")

        # Sync last_run_time
        suite.last_run_time = schedule.last_run_time
    else:
        # Deactivate linked schedule if exists
        if suite.schedule_id:
            result = await db.execute(
                select(Schedule).where(Schedule.id == suite.schedule_id)
            )
            schedule = result.scalar_one_or_none()
            if schedule:
                schedule.is_active = False
                await pause(suite.schedule_id)
        suite.next_run_time = None

"""
Schedule Management Activities

Temporal activities for schedule management ported from Celery tasks.
These activities handle schedule synchronization and execution.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.activities import get_default_retry_policy
from app.core.worker_db import run_with_session
from app.models.schedule import Schedule
from app.models.test_run import TestRun
from app.services.execution_service import ExecutionService
from temporalio import activity

logger = logging.getLogger(__name__)


# Input/Output Models for Activities


class GetActiveSchedulesInput:
    """Input for get_active_schedules activity."""

    pass


class GetActiveSchedulesOutput:
    """Output from get_active_schedules activity."""

    schedules: List[Dict[str, Any]]


class UpdateScheduleNextRunInput:
    """Input for update_schedule_next_run activity."""

    schedule_id: int


class UpdateScheduleNextRunOutput:
    """Output from update_schedule_next_run activity."""

    schedule_id: int
    next_run_time: Optional[datetime]
    success: bool


class ExecuteScheduledTestInput:
    """Input for execute_scheduled_test activity."""

    schedule_id: int


class ExecuteScheduledTestOutput:
    """Output from execute_scheduled_test activity."""

    schedule_id: int
    run_id: Optional[str]
    success: bool
    message: str
    tests_queued: int


# Activity Implementations


@activity.defn
async def get_active_schedules(input: GetActiveSchedulesInput) -> GetActiveSchedulesOutput:
    """
    Retrieve all active schedules from database.

    This activity queries the database for all schedules where is_active=True
    and returns them as a list of dictionaries for workflow processing.

    Returns:
        GetActiveSchedulesOutput with list of active schedules
    """
    logger.info("Fetching active schedules from database")

    async def _fetch_schedules(db: AsyncSession) -> GetActiveSchedulesOutput:
        result = await db.execute(
            select(Schedule).where(Schedule.is_active == True)
        )
        schedules = result.scalars().all()

        schedule_dicts = []
        for schedule in schedules:
            schedule_dicts.append({
                "id": schedule.id,
                "name": schedule.name,
                "cron_expression": schedule.cron_expression,
                "test_definition_id": schedule.test_definition_id,
                "test_suite_id": schedule.test_suite_id,
                "is_active": schedule.is_active,
                "last_run_time": schedule.last_run_time.isoformat() if schedule.last_run_time else None,
                "next_run_time": schedule.next_run_time.isoformat() if schedule.next_run_time else None,
                "max_retries": schedule.max_retries,
                "retry_interval_seconds": schedule.retry_interval_seconds,
                "timeout_seconds": schedule.timeout_seconds,
                "environment": schedule.environment,
            })

        logger.info(f"Found {len(schedule_dicts)} active schedules")
        return GetActiveSchedulesOutput(schedules=schedule_dicts)

    return await run_with_session(_fetch_schedules)


@activity.defn
async def update_schedule_next_run(input: UpdateScheduleNextRunInput) -> UpdateScheduleNextRunOutput:
    """
    Calculate and update next run time for a schedule.

    This activity uses croniter to calculate the next execution time based
    on the schedule's cron expression and updates the database record.

    Args:
        input: UpdateScheduleNextRunInput with schedule_id

    Returns:
        UpdateScheduleNextRunOutput with updated next_run_time
    """
    schedule_id = input.schedule_id
    logger.info(f"Updating next run time for schedule {schedule_id}")

    async def _update_next_run(db: AsyncSession) -> UpdateScheduleNextRunOutput:
        # Load schedule
        result = await db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            logger.warning(f"Schedule {schedule_id} not found")
            return UpdateScheduleNextRunOutput(
                schedule_id=schedule_id,
                next_run_time=None,
                success=False
            )

        try:
            # Calculate next run time using croniter
            # Use naive datetime (no timezone) for database compatibility
            base_time = datetime.utcnow()
            cron = croniter(schedule.cron_expression, base_time)
            next_time = cron.get_next(datetime)

            # Update schedule
            schedule.next_run_time = next_time
            await db.commit()

            logger.info(
                f"Updated schedule {schedule_id} next run time to {next_time.isoformat()}"
            )

            return UpdateScheduleNextRunOutput(
                schedule_id=schedule_id,
                next_run_time=next_time,
                success=True
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to calculate next run time for schedule {schedule_id}: {e}")
            return UpdateScheduleNextRunOutput(
                schedule_id=schedule_id,
                next_run_time=None,
                success=False
            )

    return await run_with_session(_update_next_run)


@activity.defn
async def execute_scheduled_test(input: ExecuteScheduledTestInput) -> ExecuteScheduledTestOutput:
    """
    Execute tests for a scheduled run.

    This activity:
    1. Loads the schedule from database
    2. Updates last_run_time and calculates next_run_time
    3. Checks execution limits
    4. Resolves target test definitions
    5. Creates test run record
    6. Queues test execution for each test definition

    Args:
        input: ExecuteScheduledTestInput with schedule_id

    Returns:
        ExecuteScheduledTestOutput with execution results
    """
    import uuid

    schedule_id = input.schedule_id
    run_id = str(uuid.uuid4())

    logger.info(f"Executing scheduled test for schedule_id={schedule_id}, run_id={run_id}")

    async def _execute(db: AsyncSession) -> ExecuteScheduledTestOutput:
        # Load schedule
        result = await db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return ExecuteScheduledTestOutput(
                schedule_id=schedule_id,
                run_id=None,
                success=False,
                message="Schedule not found",
                tests_queued=0
            )

        if not schedule.is_active:
            logger.info(f"Schedule {schedule_id} is not active, skipping")
            return ExecuteScheduledTestOutput(
                schedule_id=schedule_id,
                run_id=None,
                success=False,
                message="Schedule is not active",
                tests_queued=0
            )

        # Update last run time and calculate next run time
        schedule.last_run_time = datetime.utcnow()

        try:
            cron = croniter(schedule.cron_expression, datetime.utcnow())
            schedule.next_run_time = cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Failed to calculate next run time for schedule {schedule_id}: {e}")
            # Continue anyway - this is non-critical

        await db.commit()

        # Check execution limits
        exec_service = ExecutionService(db)
        can_execute = await exec_service.check_execution_limit(schedule, db)
        if not can_execute:
            logger.warning(f"Execution limit reached for schedule {schedule_id}, skipping")
            return ExecuteScheduledTestOutput(
                schedule_id=schedule_id,
                run_id=None,
                success=False,
                message="Execution limit reached",
                tests_queued=0
            )

        # Resolve target test definitions
        try:
            test_definition_ids = await exec_service.resolve_target_tests(schedule, db)
        except Exception as e:
            logger.error(f"Failed to resolve target tests for schedule {schedule_id}: {e}")
            return ExecuteScheduledTestOutput(
                schedule_id=schedule_id,
                run_id=None,
                success=False,
                message=f"Failed to resolve target tests: {str(e)}",
                tests_queued=0
            )

        if not test_definition_ids:
            logger.warning(f"No test definitions found for schedule {schedule_id}")
            return ExecuteScheduledTestOutput(
                schedule_id=schedule_id,
                run_id=None,
                success=False,
                message="No test definitions found",
                tests_queued=0
            )

        logger.info(f"Executing {len(test_definition_ids)} tests for schedule {schedule_id}")

        # Build environment
        environment = exec_service.build_environment(schedule)

        # Create test run record
        await exec_service.create_test_run(
            run_id=run_id,
            test_definition_ids=test_definition_ids,
            environment=environment,
            db=db,
            schedule_id=schedule_id
        )

        await db.commit()

        # Note: In Temporal, we don't queue tasks like Celery.
        # The workflow will trigger child workflows or activities for each test.
        # This activity just prepares the execution.

        logger.info(f"Successfully prepared execution of {len(test_definition_ids)} tests for run {run_id}")

        return ExecuteScheduledTestOutput(
            schedule_id=schedule_id,
            run_id=run_id,
            success=True,
            message=f"Prepared {len(test_definition_ids)} tests for execution",
            tests_queued=len(test_definition_ids),
            test_definition_ids=test_definition_ids,
            environment=environment
        )

    return await run_with_session(_execute)

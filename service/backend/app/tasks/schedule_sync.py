"""
Celery Beat Schedule Sync Tasks

Tasks for synchronizing database schedules to Celery Beat and executing scheduled tests.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid

from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.worker_db import run_async
from app.models.schedule import Schedule
from app.models.test_run import TestRun
from app.services import get_execution_service

logger = logging.getLogger(__name__)


# Create synchronous engine for Celery Beat (which doesn't support async)
sync_engine = create_engine(
    settings.DATABASE_URL.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql"),
    pool_pre_ping=True,
    pool_recycle=3600
)
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)


@celery_app.task(name="app.tasks.schedule_sync.sync_schedules_to_beat")
def sync_schedules_to_beat():
    """
    Periodic task to sync database schedules to Celery Beat.

    This task reads all active schedules from the database and updates
    the Celery Beat scheduler configuration. It runs every 5 minutes.

    Should be scheduled in Celery Beat as:
        {
            "task": "app.tasks.schedule_sync.sync_schedules_to_beat",
            "schedule": crontab(minute='*/5')
        }
    """
    try:
        logger.info("Starting schedule sync to Celery Beat")

        with SyncSessionLocal() as db:
            # Get all active schedules
            result = db.execute(
                select(Schedule).where(Schedule.is_active == True)
            )
            schedules = result.scalars().all()

            logger.info(f"Found {len(schedules)} active schedules to sync")

            # Update Celery Beat schedule
            app = celery_app
            schedule_config = {}

            for schedule in schedules:
                task_name = f"schedule_{schedule.id}"

                # Determine task to execute based on schedule type
                schedule_config[task_name] = {
                    "task": "app.tasks.schedule_sync.execute_scheduled_tests",
                    "schedule": schedule.cron_expression,
                    "args": [schedule.id],
                    "options": {
                        "expires": 300  # Task expires after 5 minutes
                    }
                }

                logger.info(f"Registered schedule '{schedule.name}' (ID: {schedule.id})")

            # Update the beat schedule
            if hasattr(app, 'conf'):
                app.conf.beat_schedule = schedule_config
                logger.info(f"Updated beat schedule with {len(schedule_config)} tasks")

        logger.info("Schedule sync completed successfully")

    except Exception as e:
        logger.error(f"Error syncing schedules to Celery Beat: {str(e)}", exc_info=True)
        raise


@celery_app.task(name="app.tasks.schedule_sync.execute_scheduled_tests")
def execute_scheduled_tests(schedule_id: int):
    """
    Execute tests for a scheduled run.

    Triggered by Celery Beat when a schedule's cron time arrives.

    Args:
        schedule_id: Schedule ID to execute
    """
    run_id = str(uuid.uuid4())
    logger.info(f"Executing scheduled tests for schedule_id={schedule_id}, run_id={run_id}")

    try:
        async def execute_async():
            async_engine = create_async_engine(settings.DATABASE_URL)
            async_session_maker = sessionmaker(
                async_engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session_maker() as db:
                # Get schedule
                result = await db.execute(
                    select(Schedule).where(Schedule.id == schedule_id)
                )
                schedule = result.scalar_one_or_none()

                if not schedule:
                    logger.error(f"Schedule {schedule_id} not found")
                    return

                if not schedule.is_active:
                    logger.info(f"Schedule {schedule_id} is not active, skipping")
                    return

                # Update last run time and calculate next run time
                schedule.last_run_time = datetime.utcnow()

                # Calculate next run time using croniter
                from croniter import croniter
                try:
                    cron = croniter(schedule.cron_expression, datetime.utcnow())
                    schedule.next_run_time = cron.get_next(datetime)
                except Exception as e:
                    logger.error(f"Failed to calculate next run time for schedule {schedule_id}: {e}")

                await db.commit()

                # Check execution limits
                can_execute = await get_execution_service().check_execution_limit(schedule, db)
                if not can_execute:
                    logger.warning(
                        f"Execution limit reached for schedule {schedule_id}, skipping"
                    )
                    return

                # Resolve target test definitions
                try:
                    test_definition_ids = await get_execution_service().resolve_target_tests(
                        schedule, db
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to resolve target tests for schedule {schedule_id}: {str(e)}"
                    )
                    return

                if not test_definition_ids:
                    logger.warning(f"No test definitions found for schedule {schedule_id}")
                    return

                logger.info(
                    f"Executing {len(test_definition_ids)} tests for schedule {schedule_id}"
                )

                # Build environment
                environment = get_execution_service().build_environment(schedule)

                # Create test run record
                await get_execution_service().create_test_run(
                    run_id=run_id,
                    test_definition_ids=test_definition_ids,
                    environment=environment,
                    db=db,
                    schedule_id=schedule_id
                )

                # Trigger execution for each test
                for test_def_id in test_definition_ids:
                    celery_app.send_task(
                        "app.tasks.test_execution.execute_test",
                        args=[test_def_id, run_id, environment]
                    )
                    logger.info(
                        f"Queued test {test_def_id} for run_id={run_id}"
                    )

                await db.commit()
                logger.info(f"Successfully queued {len(test_definition_ids)} tests")

            await async_engine.dispose()

        run_async(lambda: execute_async())

    except Exception as e:
        logger.error(
            f"Error executing scheduled tests for schedule {schedule_id}: {str(e)}",
            exc_info=True
        )
        raise


@celery_app.task(name="app.tasks.schedule_sync.check_overdue_schedules")
def check_overdue_schedules():
    """
    Check for schedules that may have missed their execution time.

    This task runs every minute and checks if any active schedules have
    next_run_time in the past. If so, it triggers execution immediately.

    Should be scheduled in Celery Beat as:
        {
            "task": "app.tasks.schedule_sync.check_overdue_schedules",
            "schedule": crontab(minute='*')
        }
    """
    try:
        import asyncio

        async def check_async():
            async_engine = create_async_engine(settings.DATABASE_URL)
            async_session_maker = sessionmaker(
                async_engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session_maker() as db:
                # DB stores timestamps as naive datetime. Keep comparisons naive to avoid
                # asyncpg errors mixing offset-aware and offset-naive datetimes.
                now = datetime.utcnow()

                # Find schedules with next_run_time in the past
                result = await db.execute(
                    select(Schedule).where(
                        Schedule.is_active == True,
                        Schedule.next_run_time <= now
                    )
                )
                overdue_schedules = result.scalars().all()

                if overdue_schedules:
                    logger.info(f"Found {len(overdue_schedules)} overdue schedules")

                    for schedule in overdue_schedules:
                        logger.warning(
                            f"Schedule '{schedule.name}' (ID: {schedule.id}) is overdue. "
                            f"Expected: {schedule.next_run_time}, Now: {now}"
                        )

                        # Trigger execution
                        execute_scheduled_tests.delay(schedule.id)

            await async_engine.dispose()

        run_async(lambda: check_async())

    except Exception as e:
        logger.error(f"Error checking overdue schedules: {str(e)}", exc_info=True)
        raise


@celery_app.task(name="app.tasks.schedule_sync.cleanup_old_test_runs")
def cleanup_old_test_runs(days_to_keep: int = 30):
    """
    Clean up old test run records to prevent database bloat.

    Args:
        days_to_keep: Number of days of history to keep (default: 30)

    Should be scheduled in Celery Beat as:
        {
            "task": "app.tasks.schedule_sync.cleanup_old_test_runs",
            "schedule": crontab(hour=2, minute=0)  # Run daily at 2 AM
        }
    """
    try:
        import asyncio
        from datetime import timedelta

        async def cleanup_async():
            async_engine = create_async_engine(settings.DATABASE_URL)
            async_session_maker = sessionmaker(
                async_engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session_maker() as db:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

                # Delete old test runs
                from sqlalchemy import delete

                result = await db.execute(
                    delete(TestRun).where(TestRun.created_at < cutoff_date)
                )
                deleted_count = result.rowcount
                await db.commit()

                logger.info(
                    f"Cleaned up {deleted_count} test runs older than {days_to_keep} days"
                )

            await async_engine.dispose()

        run_async(lambda: cleanup_async())

    except Exception as e:
        logger.error(f"Error cleaning up old test runs: {str(e)}", exc_info=True)
        raise


def setup_beat_schedule():
    """
    Configure Celery Beat with periodic tasks.

    Call this during application startup to register the periodic tasks.
    """
    from celery.schedules import crontab

    celery_app.conf.beat_schedule = {
        # Sync schedules to Celery Beat every 5 minutes
        "sync-schedules-to-beat": {
            "task": "app.tasks.schedule_sync.sync_schedules_to_beat",
            "schedule": crontab(minute='*/5'),
        },
        # Check for overdue schedules every minute
        "check-overdue-schedules": {
            "task": "app.tasks.schedule_sync.check_overdue_schedules",
            "schedule": crontab(minute='*'),
        },
        # Clean up old test runs daily at 2 AM
        "cleanup-old-test-runs": {
            "task": "app.tasks.schedule_sync.cleanup_old_test_runs",
            "schedule": crontab(hour=2, minute=0),
        },
    }

    logger.info("Celery Beat schedule configured")

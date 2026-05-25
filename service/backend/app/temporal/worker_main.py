# service/backend/app/temporal/worker_main.py
"""
Temporal Worker Entry Point.

This script starts the Temporal worker that processes workflows and activities.
"""
import asyncio
import logging
from datetime import timedelta

from temporalio.worker import Worker
from temporalio.client import Client

from app.temporal.settings import settings
from app.activities.test_activities import (
    prepare_test,
    run_browser_automation,
    save_results,
    mark_run_failed
)
from app.activities.schedule_activities import (
    get_active_schedules,
    update_schedule_next_run,
    execute_scheduled_test
)
from app.activities.maintenance_activities import (
    cleanup_old_test_runs,
    cleanup_expired_sessions,
    cleanup_audit_logs
)
from app.activities.email_activities import send_email
from app.workflows.test_execution import TestExecutionWorkflow, RetryTestWorkflow
from app.workflows.schedules import ScheduleSyncWorkflow, ScheduleExecutionWorkflow
from app.workflows.suites import SuiteExecutionWorkflow
from app.workflows.emails import EmailWorkflow
from app.workflows.maintenance import (
    CleanupTestRunsWorkflow,
    CleanupSessionsWorkflow,
    CleanupAuditLogsWorkflow
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_worker():
    """Run the Temporal worker."""
    logger.info(f"Connecting to Temporal server at {settings.host_url}")

    # Connect to Temporal server
    client = await Client.connect(
        target_host=settings.host_url,
        namespace=settings.namespace
    )

    logger.info(f"Connected to Temporal server")
    logger.info(f"Task queue: {settings.task_queue}")

    # Register activities
    activities = [
        # Test activities
        prepare_test,
        run_browser_automation,
        save_results,
        mark_run_failed,
        # Schedule activities
        get_active_schedules,
        update_schedule_next_run,
        execute_scheduled_test,
        # Maintenance activities
        cleanup_old_test_runs,
        cleanup_expired_sessions,
        cleanup_audit_logs,
        # Email activities
        send_email,
    ]

    # Register workflows
    workflows = [
        TestExecutionWorkflow,
        RetryTestWorkflow,
        ScheduleSyncWorkflow,
        ScheduleExecutionWorkflow,
        SuiteExecutionWorkflow,
        EmailWorkflow,
        CleanupTestRunsWorkflow,
        CleanupSessionsWorkflow,
        CleanupAuditLogsWorkflow,
    ]

    logger.info(f"Registered {len(workflows)} workflows and {len(activities)} activities")

    # Create and run worker
    worker = Worker(
        client=client,
        task_queue=settings.task_queue,
        workflows=workflows,
        activities=activities,
        # Activity worker options
        max_cached_workflows=200,
    )

    logger.info("Worker started, waiting for tasks...")

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")

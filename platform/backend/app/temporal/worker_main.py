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
from app.temporal.database import close_worker_engine, get_worker_session_maker
from app.core.worker_db import set_temporal_session_maker
from app.temporal.activities.test_activities import (
    prepare_test,
    run_browser_automation,
    save_results,
    mark_run_failed
)
from app.temporal.activities.schedule_activities import (
    execute_scheduled_test
)
from app.temporal.activities.maintenance_activities import (
    cleanup_old_test_runs,
    cleanup_expired_sessions,
    cleanup_audit_logs
)
from app.temporal.activities.email_activities import send_email
from app.temporal.activities.monitoring_activities import (
    collect_system_metrics,
    analyze_health_metrics,
    store_monitoring_snapshot,
    send_alert_notifications,
    generate_ai_report,
)
from app.temporal.workflows.test_execution import TestExecutionWorkflow, RetryTestWorkflow
from app.temporal.workflows.schedules import ScheduleExecutionWorkflow
from app.temporal.workflows.suites import SuiteExecutionWorkflow
from app.temporal.workflows.emails import EmailWorkflow
from app.temporal.workflows.monitoring_workflow import MonitoringAgentWorkflow
from app.temporal.workflows.maintenance import (
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

    # Set up database session maker for Temporal activities
    session_maker = get_worker_session_maker()
    set_temporal_session_maker(session_maker)
    logger.info("Database session maker configured for Temporal worker")

    # Connect to Temporal server
    client = await Client.connect(
        settings.host_url,
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
        execute_scheduled_test,
        # Maintenance activities
        cleanup_old_test_runs,
        cleanup_expired_sessions,
        cleanup_audit_logs,
        # Email activities
        send_email,
        # Monitoring activities
        collect_system_metrics,
        analyze_health_metrics,
        store_monitoring_snapshot,
        send_alert_notifications,
        generate_ai_report,
    ]

    # Register workflows
    workflows = [
        TestExecutionWorkflow,
        RetryTestWorkflow,
        ScheduleExecutionWorkflow,
        SuiteExecutionWorkflow,
        EmailWorkflow,
        MonitoringAgentWorkflow,
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
    finally:
        # Clean up database connections
        await close_worker_engine()
        logger.info("Database connections closed")


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")

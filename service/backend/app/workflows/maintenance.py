# service/backend/app/workflows/maintenance.py
"""
Workflows for maintenance tasks.
"""
import logging
from datetime import timedelta
from temporalio import workflow

from app.activities import get_default_retry_policy
from app.activities.maintenance_activities import (
    cleanup_old_test_runs,
    cleanup_expired_sessions,
    cleanup_audit_logs
)

logger = logging.getLogger(__name__)


@workflow.defn
class CleanupTestRunsWorkflow:
    """Workflow for cleaning up old test runs."""

    @workflow.run
    async def run(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """Clean up test runs older than specified days."""
        logger.info(f"Starting test run cleanup (keeping {days_to_keep} days)")

        result = await workflow.execute_activity(
            cleanup_old_test_runs,
            days_to_keep,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=get_default_retry_policy()
        )

        return result


@workflow.defn
class CleanupSessionsWorkflow:
    """Workflow for cleaning up expired sessions."""

    @workflow.run
    async def run(self) -> Dict[str, Any]:
        """Clean up expired user sessions."""
        logger.info("Starting session cleanup")

        result = await workflow.execute_activity(
            cleanup_expired_sessions,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=get_default_retry_policy()
        )

        return result


@workflow.defn
class CleanupAuditLogsWorkflow:
    """Workflow for cleaning up old audit logs."""

    @workflow.run
    async def run(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """Clean up audit logs older than specified days."""
        logger.info(f"Starting audit log cleanup (keeping {days_to_keep} days)")

        result = await workflow.execute_activity(
            cleanup_audit_logs,
            days_to_keep,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=get_default_retry_policy()
        )

        return result

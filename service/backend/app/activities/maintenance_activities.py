"""
Temporal Maintenance Activities.

Activities for cleaning up old data and expired records.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio import activity

from app.core.database import get_async_session
from app.models.auth.audit_log import AuditLog
from app.models.auth.user_session import UserSession
from app.models.test_case import TestCase
from app.models.test_run import TestRun

logger = logging.getLogger(__name__)


@activity.defn
async def cleanup_old_test_runs(days_to_keep: int = 90) -> dict:
    """Clean up test runs and related test cases older than specified days.

    Args:
        days_to_keep: Number of days of history to retain (default: 90)

    Returns:
        Dict with cleanup statistics
    """
    activity_info = activity.info()
    logger.info(
        f"Cleaning up test runs older than {days_to_keep} days "
        f"(attempt {activity_info.attempt})"
    )

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

    async with get_async_session() as session:
        try:
            # First, delete related test_cases
            test_cases_stmt = delete(TestCase).where(
                TestCase.created_at < cutoff_date
            )
            test_cases_result = await session.execute(test_cases_stmt)
            test_cases_deleted = test_cases_result.rowcount

            # Then, delete test_runs
            test_runs_stmt = delete(TestRun).where(
                TestRun.created_at < cutoff_date
            )
            test_runs_result = await session.execute(test_runs_stmt)
            test_runs_deleted = test_runs_result.rowcount

            await session.commit()

            logger.info(
                f"Cleanup completed: {test_runs_deleted} test runs, "
                f"{test_cases_deleted} test cases deleted"
            )

            return {
                "test_runs_deleted": test_runs_deleted,
                "test_cases_deleted": test_cases_deleted,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error during test run cleanup: {str(e)}")
            await session.rollback()
            raise


@activity.defn
async def cleanup_expired_sessions() -> dict:
    """Clean up expired user sessions.

    Returns:
        Dict with cleanup statistics
    """
    activity_info = activity.info()
    logger.info(
        f"Cleaning up expired sessions (attempt {activity_info.attempt})"
    )

    async with get_async_session() as session:
        try:
            # Count expired sessions
            count_query = select(UserSession).where(
                UserSession.expires_at < datetime.utcnow()
            )
            result = await session.execute(count_query)
            expired_sessions = result.scalars().all()
            count = len(expired_sessions)

            if count > 0:
                # Delete expired sessions
                delete_stmt = delete(UserSession).where(
                    UserSession.expires_at < datetime.utcnow()
                )
                await session.execute(delete_stmt)
                await session.commit()
                logger.info(f"Deleted {count} expired sessions")
            else:
                logger.info("No expired sessions to clean up")

            return {
                "sessions_deleted": count,
            }

        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
            await session.rollback()
            raise


@activity.defn
async def cleanup_audit_logs() -> dict:
    """Clean up audit logs past their retention period.

    Returns:
        Dict with cleanup statistics
    """
    activity_info = activity.info()
    logger.info(
        f"Cleaning up audit logs past retention (attempt {activity_info.attempt})"
    )

    async with get_async_session() as session:
        try:
            # Count audit logs past retention
            count_query = select(AuditLog).where(
                AuditLog.auto_delete_at < datetime.utcnow()
            )
            result = await session.execute(count_query)
            audit_logs = result.scalars().all()
            count = len(audit_logs)

            if count > 0:
                # Delete audit logs past retention
                delete_stmt = delete(AuditLog).where(
                    AuditLog.auto_delete_at < datetime.utcnow()
                )
                await session.execute(delete_stmt)
                await session.commit()
                logger.info(f"Deleted {count} audit logs past retention period")
            else:
                logger.info("No audit logs to clean up")

            return {
                "audit_logs_deleted": count,
            }

        except Exception as e:
            logger.error(f"Error during audit log cleanup: {str(e)}")
            await session.rollback()
            raise

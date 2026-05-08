from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timedelta
import logging

from app.core.database import async_session_maker
from app.models.auth.audit_log import AuditLog
from app.models.auth.user_session import UserSession
from app.models.auth.user_account import UserAccount
from app.core.config import settings

logger = logging.getLogger(__name__)


@shared_task
def cleanup_audit_logs_task():
    """
    Daily task to delete audit logs past retention period.
    Runs once per day, deletes records where auto_delete_at < NOW()
    """
    async def _cleanup():
        async with async_session_maker() as session:
            try:
                # Count logs to be deleted
                count_query = select(AuditLog).where(
                    AuditLog.auto_delete_at < datetime.utcnow()
                )
                result = await session.execute(count_query)
                count = len(result.scalars().all())

                if count > 0:
                    # Delete expired logs
                    delete_stmt = delete(AuditLog).where(
                        AuditLog.auto_delete_at < datetime.utcnow()
                    )
                    await session.execute(delete_stmt)
                    await session.commit()
                    logger.info(f"Deleted {count} audit logs past retention period")
                else:
                    logger.info("No audit logs to clean up")
            except Exception as e:
                logger.error(f"Error cleaning up audit logs: {e}")
                await session.rollback()
                raise

    import asyncio
    return asyncio.run(_cleanup())


@shared_task
def cleanup_expired_sessions_task():
    """
    Hourly task to clean up expired sessions.
    Removes sessions where expires_at < NOW()
    """
    async def _cleanup():
        async with async_session_maker() as session:
            try:
                # Count expired sessions
                count_query = select(UserSession).where(
                    UserSession.expires_at < datetime.utcnow()
                )
                result = await session.execute(count_query)
                count = len(result.scalars().all())

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
            except Exception as e:
                logger.error(f"Error cleaning up expired sessions: {e}")
                await session.rollback()
                raise

    import asyncio
    return asyncio.run(_cleanup())


@shared_task
def reset_locked_accounts_task():
    """
    Every 5 minutes, reset account lockouts that have expired.
    Sets failed_login_attempts = 0 and locked_until = NULL
    for accounts where locked_until < NOW()
    """
    async def _reset():
        async with async_session_maker() as session:
            try:
                # Find locked accounts with expired lockouts
                query = select(UserAccount).where(
                    UserAccount.locked_until < datetime.utcnow()
                )
                result = await session.execute(query)
                locked_accounts = result.scalars().all()

                count = 0
                for account in locked_accounts:
                    account.failed_login_attempts = 0
                    account.locked_until = None
                    count += 1

                if count > 0:
                    await session.commit()
                    logger.info(f"Reset lockout for {count} accounts")
                else:
                    logger.info("No locked accounts to reset")
            except Exception as e:
                logger.error(f"Error resetting locked accounts: {e}")
                await session.rollback()
                raise

    import asyncio
    return asyncio.run(_reset())

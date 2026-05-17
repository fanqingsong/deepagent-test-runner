from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timedelta
import logging

from app.core.worker_db import run_async, run_with_session
from app.models.auth.audit_log import AuditLog
from app.models.auth.user_session import UserSession
from app.models.auth.user_account import UserAccount
from app.core.config import settings

logger = logging.getLogger(__name__)


@shared_task
def cleanup_audit_logs_task():
    """Daily task to delete audit logs past retention period."""
    async def _run():
        async def _op(session: AsyncSession):
            count_query = select(AuditLog).where(
                AuditLog.auto_delete_at < datetime.utcnow()
            )
            result = await session.execute(count_query)
            count = len(result.scalars().all())

            if count > 0:
                delete_stmt = delete(AuditLog).where(
                    AuditLog.auto_delete_at < datetime.utcnow()
                )
                await session.execute(delete_stmt)
                await session.commit()
                logger.info(f"Deleted {count} audit logs past retention period")
            else:
                logger.info("No audit logs to clean up")

        await run_with_session(_op)

    return run_async(_run)


@shared_task
def cleanup_expired_sessions_task():
    """Hourly task to clean up expired sessions."""
    async def _run():
        async def _op(session: AsyncSession):
            count_query = select(UserSession).where(
                UserSession.expires_at < datetime.utcnow()
            )
            result = await session.execute(count_query)
            count = len(result.scalars().all())

            if count > 0:
                delete_stmt = delete(UserSession).where(
                    UserSession.expires_at < datetime.utcnow()
                )
                await session.execute(delete_stmt)
                await session.commit()
                logger.info(f"Deleted {count} expired sessions")
            else:
                logger.info("No expired sessions to clean up")

        await run_with_session(_op)

    return run_async(_run)


@shared_task
def reset_locked_accounts_task():
    """Every 5 minutes, reset account lockouts that have expired."""
    async def _run():
        async def _op(session: AsyncSession):
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

        await run_with_session(_op)

    return run_async(_run)

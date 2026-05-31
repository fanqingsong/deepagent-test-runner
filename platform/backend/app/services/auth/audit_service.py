"""
Audit service for logging security events.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from app.models.auth import AuditLog
from app.core.database import get_db

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing audit logs"""

    @staticmethod
    async def log_security_event(
        db: AsyncSession,
        user_id: Optional[int],
        event_type: str,
        details: Dict[str, Any],
        ip_address: str,
        user_agent: str = None
    ) -> bool:
        """
        Log a security event to the audit log.

        Args:
            db: Database session
            user_id: User ID (None for system events)
            event_type: Type of security event
            details: Event details as dictionary
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            True if successful, False otherwise
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                event_type=event_type,
                event_metadata=details,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.utcnow()
            )
            db.add(audit_log)
            await db.commit()

            logger.info(f"Audit log created: {event_type} for user {user_id}")
            return True

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create audit log: {str(e)}")
            return False

    @staticmethod
    async def get_user_audit_logs(
        db: AsyncSession,
        user_id: int,
        limit: int = 100
    ) -> list:
        """
        Get audit logs for a specific user.

        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        try:
            query = select(AuditLog).where(
                AuditLog.user_id == user_id
            ).order_by(
                AuditLog.created_at.desc()
            ).limit(limit)

            result = await db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get audit logs for user {user_id}: {str(e)}")
            return []

    @staticmethod
    async def cleanup_old_audit_logs(
        db: AsyncSession,
        days_old: int = 90
    ) -> int:
        """
        Delete audit logs older than specified days.

        Args:
            db: Database session
            days_old: Delete logs older than this many days

        Returns:
            Number of logs deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            query = select(AuditLog).where(
                AuditLog.created_at < cutoff_date,
                AuditLog.auto_delete_at.isnot(None)
            )

            result = await db.execute(query)
            logs_to_delete = result.scalars().all()

            count = len(logs_to_delete)

            for log in logs_to_delete:
                await db.delete(log)

            await db.commit()

            logger.info(f"Deleted {count} old audit logs (older than {days_old} days)")
            return count

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to cleanup old audit logs: {str(e)}")
            return 0

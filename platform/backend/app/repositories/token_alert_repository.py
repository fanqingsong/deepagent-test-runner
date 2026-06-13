"""
Token Alert Repository Implementation

SQLAlchemy implementation of TokenAlert repository following async patterns.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.token_alert import TokenAlert
from app.repositories.interfaces.token_alert_repository_interface import ITokenAlertRepository

logger = logging.getLogger(__name__)


class SQLAlchemyTokenAlertRepository(ITokenAlertRepository):
    """
    SQLAlchemy implementation of TokenAlert repository.

    Handles all database operations for TokenAlert model using async SQLAlchemy patterns.
    Provides proper error handling, logging, and transaction management.
    """

    def __init__(self):
        """Initialize the repository."""
        self._model_class = TokenAlert

    async def create(
        self,
        alert: Any,
        db_session: AsyncSession
    ) -> TokenAlert:
        """
        Create a new token alert.

        Args:
            alert: TokenAlertCreate schema with alert data
            db_session: Database session

        Returns:
            Created TokenAlert object

        Raises:
            ValueError: If validation fails
        """
        try:
            new_alert = TokenAlert(
                alert_type=alert.get("alert_type"),
                severity=alert.get("severity", "warning"),
                budget_id=alert.get("budget_id"),
                quota_id=alert.get("quota_id"),
                user_id=alert.get("user_id"),
                threshold_type=alert.get("threshold_type", "percentage"),
                threshold_value=alert.get("threshold_value", 0),
                current_value=alert.get("current_value", 0),
                metrics_snapshot=alert.get("metrics_snapshot", {}),
                message=alert.get("message", ""),
                details=alert.get("details", {}),
                enforcement_action=alert.get("enforcement_action"),
                enforcement_result=alert.get("enforcement_result", {})
            )

            db_session.add(new_alert)
            await db_session.flush()
            await db_session.refresh(new_alert)

            logger.info(f"Created token alert {new_alert.id} of type '{new_alert.alert_type}'")
            return new_alert

        except Exception as e:
            logger.error(f"Error creating token alert: {e}")
            await db_session.rollback()
            raise

    async def get_by_id(self, alert_id: int, db_session: AsyncSession) -> Optional[TokenAlert]:
        """
        Retrieve a token alert by its primary key ID.

        Args:
            alert_id: Primary key ID
            db_session: Database session

        Returns:
            TokenAlert object or None if not found
        """
        try:
            stmt = select(TokenAlert).where(TokenAlert.id == alert_id)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting alert by ID {alert_id}: {e}")
            return None

    async def get_all(
        self,
        db_session: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[TokenAlert]:
        """
        Retrieve all token alerts.

        Args:
            db_session: Database session
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of TokenAlert objects, ordered by created_at DESC
        """
        try:
            stmt = select(TokenAlert).order_by(
                desc(TokenAlert.created_at)
            ).offset(offset).limit(limit)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting all alerts: {e}")
            return []

    async def get_active_alerts(
        self,
        db_session: AsyncSession,
        budget_id: Optional[int] = None,
        quota_id: Optional[int] = None,
        user_id: Optional[int] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[TokenAlert]:
        """
        Retrieve active (unacknowledged) alerts.

        Args:
            db_session: Database session
            budget_id: Optional budget ID filter
            quota_id: Optional quota ID filter
            user_id: Optional user ID filter
            severity: Optional severity filter
            limit: Maximum number of records to return

        Returns:
            List of active TokenAlert objects
        """
        try:
            stmt = select(TokenAlert).where(TokenAlert.is_acknowledged == False)

            if budget_id:
                stmt = stmt.where(TokenAlert.budget_id == budget_id)
            if quota_id:
                stmt = stmt.where(TokenAlert.quota_id == quota_id)
            if user_id:
                stmt = stmt.where(TokenAlert.user_id == user_id)
            if severity:
                stmt = stmt.where(TokenAlert.severity == severity)

            stmt = stmt.order_by(desc(TokenAlert.created_at)).limit(limit)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []

    async def get_recent_alerts(
        self,
        budget_id: Optional[int] = None,
        quota_id: Optional[int] = None,
        alert_type: Optional[str] = None,
        since: Optional[datetime] = None,
        db_session: AsyncSession = None,
        limit: int = 10
    ) -> List[TokenAlert]:
        """
        Retrieve recent alerts within a time period.

        Args:
            budget_id: Optional budget ID filter
            quota_id: Optional quota ID filter
            alert_type: Optional alert type filter
            since: Start time for recent alerts
            db_session: Database session
            limit: Maximum number of records to return

        Returns:
            List of recent TokenAlert objects
        """
        try:
            stmt = select(TokenAlert)

            if budget_id:
                stmt = stmt.where(TokenAlert.budget_id == budget_id)
            if quota_id:
                stmt = stmt.where(TokenAlert.quota_id == quota_id)
            if alert_type:
                stmt = stmt.where(TokenAlert.alert_type == alert_type)
            if since:
                stmt = stmt.where(TokenAlert.created_at >= since)

            stmt = stmt.order_by(desc(TokenAlert.created_at)).limit(limit)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []

    async def get_alerts_since(
        self,
        since: datetime,
        db_session: AsyncSession,
        budget_id: Optional[int] = None,
        quota_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 100
    ) -> List[TokenAlert]:
        """
        Retrieve alerts created since a specific time.

        Args:
            since: Start time
            db_session: Database session
            budget_id: Optional budget ID filter
            quota_id: Optional quota ID filter
            user_id: Optional user ID filter
            limit: Maximum number of records to return

        Returns:
            List of TokenAlert objects
        """
        try:
            stmt = select(TokenAlert).where(TokenAlert.created_at >= since)

            if budget_id:
                stmt = stmt.where(TokenAlert.budget_id == budget_id)
            if quota_id:
                stmt = stmt.where(TokenAlert.quota_id == quota_id)
            if user_id:
                stmt = stmt.where(TokenAlert.user_id == user_id)

            stmt = stmt.order_by(desc(TokenAlert.created_at)).limit(limit)

            result = await db_session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting alerts since {since}: {e}")
            return []

    async def acknowledge(
        self,
        alert_id: int,
        user_id: int,
        db_session: AsyncSession
    ) -> TokenAlert:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            user_id: User ID acknowledging
            db_session: Database session

        Returns:
            Updated TokenAlert object

        Raises:
            ValueError: If alert not found
        """
        try:
            alert = await self.get_by_id(alert_id, db_session)
            if not alert:
                raise ValueError(f"Alert not found: {alert_id}")

            # Acknowledge using model method
            alert.acknowledge(user_id)

            await db_session.flush()
            await db_session.refresh(alert)

            logger.info(f"Acknowledged alert {alert_id} by user {user_id}")
            return alert

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            await db_session.rollback()
            raise

    async def resolve(
        self,
        alert_id: int,
        db_session: AsyncSession
    ) -> TokenAlert:
        """
        Resolve an alert.

        Args:
            alert_id: Alert ID
            db_session: Database session

        Returns:
            Updated TokenAlert object

        Raises:
            ValueError: If alert not found
        """
        try:
            alert = await self.get_by_id(alert_id, db_session)
            if not alert:
                raise ValueError(f"Alert not found: {alert_id}")

            # Resolve using model method
            alert.resolve()

            await db_session.flush()
            await db_session.refresh(alert)

            logger.info(f"Resolved alert {alert_id}")
            return alert

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
            await db_session.rollback()
            raise

    async def update(
        self,
        alert_id: int,
        updates: Dict[str, Any],
        db_session: AsyncSession
    ) -> TokenAlert:
        """
        Update a token alert.

        Args:
            alert_id: Primary key ID
            updates: Dictionary of fields to update
            db_session: Database session

        Returns:
            Updated TokenAlert object

        Raises:
            ValueError: If alert not found
        """
        try:
            alert = await self.get_by_id(alert_id, db_session)
            if not alert:
                raise ValueError(f"Alert not found: {alert_id}")

            for field, value in updates.items():
                if hasattr(alert, field):
                    setattr(alert, field, value)

            await db_session.flush()
            await db_session.refresh(alert)

            logger.info(f"Updated token alert {alert_id}")
            return alert

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating alert {alert_id}: {e}")
            await db_session.rollback()
            raise

    async def delete(self, alert_id: int, db_session: AsyncSession) -> bool:
        """
        Delete a token alert by its ID.

        Args:
            alert_id: Primary key ID
            db_session: Database session

        Returns:
            True if deleted, False if not found
        """
        try:
            alert = await self.get_by_id(alert_id, db_session)
            if not alert:
                return False

            await db_session.delete(alert)
            await db_session.flush()

            logger.info(f"Deleted token alert {alert_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting alert {alert_id}: {e}")
            await db_session.rollback()
            return False

    async def count(
        self,
        db_session: AsyncSession,
        acknowledged: Optional[bool] = None
    ) -> int:
        """
        Count total token alerts.

        Args:
            db_session: Database session
            acknowledged: Optional acknowledgment status filter

        Returns:
            Total count of token alerts
        """
        try:
            stmt = select(func.count(TokenAlert.id))

            if acknowledged is not None:
                stmt = stmt.where(TokenAlert.is_acknowledged == acknowledged)

            result = await db_session.execute(stmt)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting alerts: {e}")
            return 0

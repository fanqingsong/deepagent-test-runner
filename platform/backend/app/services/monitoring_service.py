"""
Monitoring Service

Handles monitoring data queries and alert management.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func as sql_func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import AgentMonitoring, AgentAlert, AlertConfiguration
from app.models.user import User

logger = logging.getLogger(__name__)


class MonitoringService:
    """
    Service for managing system monitoring data.

    Responsible for:
    - Querying current monitoring status
    - Managing alerts (acknowledge, resolve, list)
    - Fetching monitoring reports
    - Managing alert configurations
    """

    def __init__(self, db_session=None):
        """
        Initialize Monitoring Service.

        Args:
            db_session: Async database session
        """
        self.db = db_session

    async def get_current_status(self) -> Dict[str, Any]:
        """
        Get the current monitoring status from the latest snapshot.

        Returns:
            dict: Current monitoring status with metrics and alerts
        """
        stmt = select(AgentMonitoring).order_by(desc(AgentMonitoring.check_time)).limit(1)
        result = await self.db.execute(stmt)
        latest = result.scalar_one_or_none()

        if not latest:
            return {
                "status": "unknown",
                "last_check": None,
                "metrics": None,
                "active_alerts": 0,
            }

        # Count active (unacknowledged) alerts
        # Note: acknowledged is stored as Integer (0/1), not boolean
        active_alerts_stmt = select(sql_func.count()).select_from(AgentAlert).where(
            AgentAlert.acknowledged == 0
        )
        active_alerts_result = await self.db.execute(active_alerts_stmt)
        active_alerts = active_alerts_result.scalar() or 0

        return {
            "status": latest.status,
            "last_check": latest.check_time.isoformat(),
            "metrics": latest.metrics,
            "active_alerts": active_alerts,
            "report_summary": latest.report_summary,
        }

    async def get_active_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get active (unacknowledged) alerts.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            list: Active alerts with details
        """
        # acknowledged is stored as Integer (0/1), not boolean
        stmt = (
            select(AgentAlert)
            .where(AgentAlert.acknowledged == 0)
            .order_by(desc(AgentAlert.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        alerts = result.scalars().all()

        return [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "metrics_snapshot": alert.metrics_snapshot,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in alerts
        ]

    async def get_alert_history(
        self,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get alert history with optional filters.

        Args:
            alert_type: Filter by alert type
            severity: Filter by severity
            acknowledged: Filter by acknowledgment status
            limit: Maximum number of alerts to return

        Returns:
            list: Alert history
        """
        stmt = select(AgentAlert)

        if alert_type:
            stmt = stmt.where(AgentAlert.alert_type == alert_type)
        if severity:
            stmt = stmt.where(AgentAlert.severity == severity)
        if acknowledged is not None:
            # acknowledged is stored as Integer (0/1), not boolean
            stmt = stmt.where(AgentAlert.acknowledged == (1 if acknowledged else 0))

        stmt = stmt.order_by(desc(AgentAlert.created_at)).limit(limit)

        result = await self.db.execute(stmt)
        alerts = result.scalars().all()

        return [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "acknowledged": bool(alert.acknowledged),
                "acknowledged_by": alert.acknowledged_by,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "created_at": alert.created_at.isoformat(),
            }
            for alert in alerts
        ]

    async def acknowledge_alert(
        self, alert_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID to acknowledge
            user_id: User ID acknowledging the alert

        Returns:
            dict: Updated alert data, or None if not found
        """
        stmt = select(AgentAlert).where(AgentAlert.id == alert_id)
        result = await self.db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        # acknowledged is stored as Integer (0/1), not boolean
        alert.acknowledged = 1
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Alert {alert_id} acknowledged by user {user_id}")

        return {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "acknowledged": True,
            "acknowledged_by": alert.acknowledged_by,
            "acknowledged_at": alert.acknowledged_at.isoformat(),
        }

    async def resolve_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """
        Mark an alert as resolved.

        Args:
            alert_id: Alert ID to resolve

        Returns:
            dict: Updated alert data, or None if not found
        """
        stmt = select(AgentAlert).where(AgentAlert.id == alert_id)
        result = await self.db.execute(stmt)
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.resolved_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Alert {alert_id} marked as resolved")

        return {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "resolved_at": alert.resolved_at.isoformat(),
        }

    async def get_monitoring_reports(
        self, hours: int = 24, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get monitoring reports (snapshots) from the specified time range.

        Args:
            hours: Number of hours of history to include
            limit: Maximum number of reports to return

        Returns:
            list: Monitoring reports
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        stmt = (
            select(AgentMonitoring)
            .where(AgentMonitoring.check_time >= cutoff)
            .order_by(desc(AgentMonitoring.check_time))
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        reports = result.scalars().all()

        return [
            {
                "id": report.id,
                "check_time": report.check_time.isoformat(),
                "status": report.status,
                "metrics": report.metrics,
                "alerts_generated": report.alerts_generated,
                "report_summary": report.report_summary,
                "created_at": report.created_at.isoformat(),
            }
            for report in reports
        ]

    async def get_alert_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get alert statistics for the specified time range.

        Args:
            hours: Number of hours of history to include

        Returns:
            dict: Alert statistics
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Total alerts
        total_stmt = select(sql_func.count()).select_from(AgentAlert).where(
            AgentAlert.created_at >= cutoff
        )
        total_result = await self.db.execute(total_stmt)
        total = total_result.scalar() or 0

        # Critical alerts
        critical_stmt = select(sql_func.count()).select_from(AgentAlert).where(
            AgentAlert.created_at >= cutoff
        ).where(AgentAlert.severity == "critical")
        critical_result = await self.db.execute(critical_stmt)
        critical = critical_result.scalar() or 0

        # Warning alerts
        warning_stmt = select(sql_func.count()).select_from(AgentAlert).where(
            AgentAlert.created_at >= cutoff
        ).where(AgentAlert.severity == "warning")
        warning_result = await self.db.execute(warning_stmt)
        warning = warning_result.scalar() or 0

        # By alert type
        by_type_stmt = (
            select(
                AgentAlert.alert_type,
                sql_func.count().label("count"),
            )
            .where(AgentAlert.created_at >= cutoff)
            .group_by(AgentAlert.alert_type)
        )
        by_type_result = await self.db.execute(by_type_stmt)
        by_type = {row.alert_type: row.count for row in by_type_result.all()}

        return {
            "total": total,
            "critical": critical,
            "warning": warning,
            "by_type": by_type,
            "time_range_hours": hours,
        }

    async def get_alert_configurations(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get alert configurations.

        Args:
            enabled_only: If True, only return enabled configurations

        Returns:
            list: Alert configurations
        """
        stmt = select(AlertConfiguration)

        if enabled_only:
            # enabled is stored as Integer (0/1), not boolean
            stmt = stmt.where(AlertConfiguration.enabled == 1)

        stmt = stmt.order_by(AlertConfiguration.created_at.desc())

        result = await self.db.execute(stmt)
        configs = result.scalars().all()

        return [
            {
                "id": config.id,
                "name": config.name,
                "alert_type": config.alert_type,
                "condition_json": config.condition_json,
                "severity": config.severity,
                "enabled": bool(config.enabled),
                "cooldown_seconds": config.cooldown_seconds,
                "created_by": config.created_by,
                "created_at": config.created_at.isoformat(),
            }
            for config in configs
        ]

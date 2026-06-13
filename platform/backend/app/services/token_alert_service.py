"""
Token Alert Service

Manages token alert operations following SOLID principles.
Handles alert checking, notification delivery, acknowledgment tracking, and cooldown management.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.result_helpers import (
    service_success, service_error, not_found,
    validation_error, database_error
)
from app.core.error_codes import ErrorCode
from app.core.interfaces.metrics_collector_interface import IMetricsCollector
from app.models.token_alert import TokenAlert
from app.models.token_budget import TokenBudget
from app.models.token_quota import TokenQuota
from app.models.user import User
from app.repositories.interfaces.token_alert_repository_interface import ITokenAlertRepository
from app.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)


class TokenAlertService:
    """
    Service for managing token alert operations.

    Responsibilities:
    - Check alert thresholds after usage recording
    - Generate alerts for threshold violations
    - Send notifications (UI, email, webhook)
    - Track alert acknowledgments
    - Manage alert cooldowns
    - Provide alert history and analytics

    Following SOLID principles:
    - Single Responsibility: Only handles alert operations
    - Open/Closed: Extensible through notification strategies
    - Liskov Substitution: Implements service interface properly
    - Interface Segregation: Focused, minimal interface
    - Dependency Inversion: Depends on repository interfaces
    """

    def __init__(
        self,
        alert_repository: Optional[ITokenAlertRepository] = None,
        metrics_collector: Optional[IMetricsCollector] = None
    ):
        """
        Initialize Token Alert Service.

        Args:
            alert_repository: Token alert repository (created if not provided)
            metrics_collector: Optional metrics collector for instrumentation
        """
        self.alert_repository = alert_repository or RepositoryFactory.get_token_alert_repository()
        self.metrics_collector = metrics_collector
        self._record_metric = self._get_metric_recorder()

        # Cooldown periods for alert types (in hours)
        self.alert_cooldowns = {
            "warning": 1,       # 1 hour cooldown for warning alerts
            "critical": 0.5,    # 30 minutes for critical
            "emergency": 0,     # No cooldown for emergency alerts
            "exceeded": 0       # No cooldown for exceeded alerts
        }

    def _get_metric_recorder(self):
        """Get metric recording function if metrics collector is available."""
        if self.metrics_collector:
            def record_metric(operation: str, duration_ms: float = 0):
                if duration_ms > 0:
                    self.metrics_collector.record_timing(operation, duration_ms)
                else:
                    self.metrics_collector.record_counter(f"token_alert.{operation}")
            return record_metric
        return None

    async def check_and_trigger_alerts(
        self,
        db: AsyncSession,
        budget_id: Optional[int] = None,
        quota_id: Optional[int] = None
    ) -> Any:
        """
        Check thresholds and trigger alerts if violated.

        Args:
            budget_id: Optional budget ID to check
            quota_id: Optional quota ID to check
            db: Database session

        Returns:
            ServiceSuccess with triggered alerts list or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            triggered_alerts = []

            # Check budget alerts if budget_id provided
            if budget_id:
                budget_alerts = await self._check_budget_alerts(budget_id, db)
                triggered_alerts.extend(budget_alerts)

            # Check quota alerts if quota_id provided
            if quota_id:
                quota_alerts = await self._check_quota_alerts(quota_id, db)
                triggered_alerts.extend(quota_alerts)

            result_data = {
                "budget_id": budget_id,
                "quota_id": quota_id,
                "triggered_alerts_count": len(triggered_alerts),
                "triggered_alerts": [
                    {
                        "alert_id": alert.id,
                        "alert_type": alert.alert_type,
                        "severity": alert.severity,
                        "message": alert.message
                    }
                    for alert in triggered_alerts
                ]
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("check_and_trigger_alerts", duration_ms)
                self.metrics_collector.record_counter("token_alert.triggered", len(triggered_alerts))

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error checking and triggering alerts: {e}")
            if self._record_metric:
                self._record_metric("check_and_trigger_alerts_error")
            return database_error(
                message=f"Failed to check and trigger alerts: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def _check_budget_alerts(self, budget_id: int, db: AsyncSession) -> List[TokenAlert]:
        """Check and create alerts for a budget."""
        from app.repositories.token_budget_repository import SQLAlchemyTokenBudgetRepository
        budget_repo = SQLAlchemyTokenBudgetRepository()

        budget = await budget_repo.get_by_id(budget_id, db)
        if not budget:
            return []

        triggered_alerts = []
        triggered_thresholds = budget.check_threshold_alerts()

        # Map thresholds to alert types and severities
        threshold_mapping = {
            "emergency": ("budget_exceeded", "emergency"),
            "critical": ("budget_warning", "critical"),
            "warning": ("budget_warning", "warning")
        }

        for threshold in triggered_thresholds:
            alert_type, severity = threshold_mapping.get(threshold, ("budget_warning", "warning"))

            # Check cooldown
            if await self._is_in_cooldown(budget_id, alert_type, db):
                logger.info(f"Alert {alert_type} for budget {budget_id} is in cooldown, skipping")
                continue

            # Create alert
            alert = await self.alert_repository.create(
                {
                    "alert_type": alert_type,
                    "severity": severity,
                    "budget_id": budget_id,
                    "threshold_type": "percentage",
                    "threshold_value": budget.alert_thresholds.get(threshold, 0),
                    "current_value": budget.usage_percentage,
                    "metrics_snapshot": {
                        "total_tokens": budget.total_tokens,
                        "used_tokens": budget.used_tokens,
                        "remaining_tokens": budget.remaining_tokens,
                        "usage_percentage": budget.usage_percentage
                    },
                    "message": f"Budget '{budget.name}' has exceeded {threshold}% threshold ({budget.usage_percentage:.2f}%)",
                    "details": {
                        "budget_name": budget.name,
                        "scope_type": budget.scope_type,
                        "scope_id": budget.scope_id,
                        "threshold_type": threshold
                    }
                },
                db
            )

            if alert:
                triggered_alerts.append(alert)

        return triggered_alerts

    async def _check_quota_alerts(self, quota_id: int, db: AsyncSession) -> List[TokenAlert]:
        """Check and create alerts for a quota."""
        from app.repositories.token_quota_repository import SQLAlchemyTokenQuotaRepository
        quota_repo = SQLAlchemyTokenQuotaRepository()

        quota = await quota_repo.get_by_id(quota_id, db)
        if not quota:
            return []

        triggered_alerts = []
        triggered_thresholds = quota.check_threshold_alerts()

        # Map thresholds to alert types and severities
        threshold_mapping = {
            "emergency": ("quota_exceeded", "emergency"),
            "critical": ("quota_warning", "critical"),
            "warning": ("quota_warning", "warning")
        }

        for threshold in triggered_thresholds:
            alert_type, severity = threshold_mapping.get(threshold, ("quota_warning", "warning"))

            # Check cooldown
            if await self._is_in_cooldown(quota_id, alert_type, db):
                logger.info(f"Alert {alert_type} for quota {quota_id} is in cooldown, skipping")
                continue

            # Create alert
            alert = await self.alert_repository.create(
                {
                    "alert_type": alert_type,
                    "severity": severity,
                    "quota_id": quota_id,
                    "user_id": quota.user_id,
                    "threshold_type": "percentage",
                    "threshold_value": quota.alert_thresholds.get(threshold, 0),
                    "current_value": quota.usage_percentage,
                    "metrics_snapshot": {
                        "total_tokens": quota.total_tokens,
                        "used_tokens": quota.used_tokens,
                        "remaining_tokens": quota.remaining_tokens,
                        "usage_percentage": quota.usage_percentage
                    },
                    "message": f"Quota '{quota.name}' has exceeded {threshold}% threshold ({quota.usage_percentage:.2f}%)",
                    "details": {
                        "quota_name": quota.name,
                        "user_id": quota.user_id,
                        "threshold_type": threshold
                    }
                },
                db
            )

            if alert:
                triggered_alerts.append(alert)

        return triggered_alerts

    async def _is_in_cooldown(
        self,
        resource_id: int,
        alert_type: str,
        db: AsyncSession
    ) -> bool:
        """Check if an alert type is in cooldown period for a resource."""
        cooldown_hours = self.alert_cooldowns.get(alert_type, 0)
        if cooldown_hours == 0:
            return False

        cooldown_cutoff = datetime.utcnow() - timedelta(hours=cooldown_hours)

        # Check if similar alert was created recently
        recent_alerts = await self.alert_repository.get_recent_alerts(
            budget_id=resource_id if "budget" in alert_type else None,
            quota_id=resource_id if "quota" in alert_type else None,
            alert_type=alert_type,
            since=cooldown_cutoff,
            db_session=db
        )

        return len(recent_alerts) > 0

    async def send_alert_notifications(
        self,
        alert_id: int,
        db: AsyncSession,
        channels: Optional[List[str]] = None
    ) -> Any:
        """
        Send notifications for an alert through specified channels.

        Args:
            alert_id: Alert ID
            db: Database session
            channels: List of notification channels (default: ["ui"])

        Returns:
            ServiceSuccess with notification results or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            if channels is None:
                channels = ["ui"]

            alert = await self.alert_repository.get_by_id(alert_id, db)

            if not alert:
                return not_found(
                    resource="TokenAlert",
                    identifier=str(alert_id)
                )

            notification_results = {}

            # UI notification (always stored in DB)
            if "ui" in channels:
                notification_results["ui"] = {
                    "sent": True,
                    "message": "UI notification available in dashboard"
                }
                alert.mark_notification_sent("ui", success=True)

            # Email notification (placeholder for future implementation)
            if "email" in channels:
                # TODO: Implement email sending logic
                notification_results["email"] = {
                    "sent": False,
                    "message": "Email notifications not yet implemented"
                }
                alert.mark_notification_sent("email", success=False, error="Not implemented")

            # Webhook notification (placeholder for future implementation)
            if "webhook" in channels:
                # TODO: Implement webhook sending logic
                notification_results["webhook"] = {
                    "sent": False,
                    "message": "Webhook notifications not yet implemented"
                }
                alert.mark_notification_sent("webhook", success=False, error="Not implemented")

            result_data = {
                "alert_id": alert.id,
                "channels_requested": channels,
                "notification_results": notification_results,
                "total_sent": sum(1 for r in notification_results.values() if r.get("sent", False)),
                "total_failed": sum(1 for r in notification_results.values() if not r.get("sent", True))
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("send_alert_notifications", duration_ms)
                self.metrics_collector.record_counter("token_alert.notifications_sent", result_data["total_sent"])
                self.metrics_collector.record_counter("token_alert.notifications_failed", result_data["total_failed"])

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error sending alert notifications: {e}")
            if self._record_metric:
                self._record_metric("send_alert_notifications_error")
            return database_error(
                message=f"Failed to send alert notifications: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def acknowledge_alert(
        self,
        alert_id: int,
        user_id: int,
        db: AsyncSession
    ) -> Any:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            user_id: User ID acknowledging the alert
            db: Database session

        Returns:
            ServiceSuccess with acknowledgment info or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            alert = await self.alert_repository.get_by_id(alert_id, db)

            if not alert:
                return not_found(
                    resource="TokenAlert",
                    identifier=str(alert_id)
                )

            if alert.is_acknowledged:
                return validation_error(
                    "Alert is already acknowledged",
                    error_code=ErrorCode.INVALID_STATE_TRANSITION
                )

            # Acknowledge the alert
            await self.alert_repository.acknowledge(alert_id, user_id, db)

            result_data = {
                "alert_id": alert.id,
                "acknowledged_by": user_id,
                "acknowledged_at": datetime.utcnow().isoformat(),
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("acknowledge_alert", duration_ms)
                self.metrics_collector.record_counter("token_alert.acknowledged")

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            if self._record_metric:
                self._record_metric("acknowledge_alert_error")
            return database_error(
                message=f"Failed to acknowledge alert: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def get_active_alerts(
        self,
        db: AsyncSession,
        budget_id: Optional[int] = None,
        quota_id: Optional[int] = None,
        user_id: Optional[int] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> Any:
        """
        Get active (unacknowledged) alerts.

        Args:
            db: Database session
            budget_id: Optional budget ID filter
            quota_id: Optional quota ID filter
            user_id: Optional user ID filter
            severity: Optional severity filter
            limit: Maximum number of alerts to return

        Returns:
            ServiceSuccess with active alerts list or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            alerts = await self.alert_repository.get_active_alerts(
                db_session=db,
                budget_id=budget_id,
                quota_id=quota_id,
                user_id=user_id,
                severity=severity,
                limit=limit
            )

            alerts_data = []
            for alert in alerts:
                alerts_data.append({
                    "alert_id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "budget_id": alert.budget_id,
                    "quota_id": alert.quota_id,
                    "user_id": alert.user_id,
                    "threshold_value": alert.threshold_value,
                    "current_value": alert.current_value,
                    "is_acknowledged": alert.is_acknowledged,
                    "created_at": alert.created_at.isoformat(),
                    "is_critical": alert.is_critical
                })

            result_data = {
                "total_active_alerts": len(alerts_data),
                "alerts": alerts_data,
                "filters": {
                    "budget_id": budget_id,
                    "quota_id": quota_id,
                    "user_id": user_id,
                    "severity": severity
                }
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("get_active_alerts", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            if self._record_metric:
                self._record_metric("get_active_alerts_error")
            return database_error(
                message=f"Failed to get active alerts: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def get_alert_history(
        self,
        db: AsyncSession,
        budget_id: Optional[int] = None,
        quota_id: Optional[int] = None,
        user_id: Optional[int] = None,
        days_back: int = 30,
        limit: int = 100
    ) -> Any:
        """
        Get alert history for analytics.

        Args:
            db: Database session
            budget_id: Optional budget ID filter
            quota_id: Optional quota ID filter
            user_id: Optional user ID filter
            days_back: Number of days to look back
            limit: Maximum number of alerts to return

        Returns:
            ServiceSuccess with alert history or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            since = datetime.utcnow() - timedelta(days=days_back)

            alerts = await self.alert_repository.get_alerts_since(
                since=since,
                db_session=db,
                budget_id=budget_id,
                quota_id=quota_id,
                user_id=user_id,
                limit=limit
            )

            # Group by alert type and severity
            summary = {
                "total_alerts": len(alerts),
                "by_type": {},
                "by_severity": {},
                "acknowledged": 0,
                "unacknowledged": 0
            }

            alerts_data = []
            for alert in alerts:
                alerts_data.append({
                    "alert_id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "message": alert.message,
                    "is_acknowledged": alert.is_acknowledged,
                    "acknowledged_by": alert.acknowledged_by,
                    "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                    "created_at": alert.created_at.isoformat()
                })

                # Update summary
                if alert.alert_type not in summary["by_type"]:
                    summary["by_type"][alert.alert_type] = 0
                summary["by_type"][alert.alert_type] += 1

                if alert.severity not in summary["by_severity"]:
                    summary["by_severity"][alert.severity] = 0
                summary["by_severity"][alert.severity] += 1

                if alert.is_acknowledged:
                    summary["acknowledged"] += 1
                else:
                    summary["unacknowledged"] += 1

            result_data = {
                "summary": summary,
                "alerts": alerts_data,
                "period": {
                    "days_back": days_back,
                    "since": since.isoformat(),
                    "until": datetime.utcnow().isoformat()
                }
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("get_alert_history", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            if self._record_metric:
                self._record_metric("get_alert_history_error")
            return database_error(
                message=f"Failed to get alert history: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

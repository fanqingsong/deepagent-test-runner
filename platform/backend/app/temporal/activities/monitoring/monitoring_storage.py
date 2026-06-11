"""
Monitoring Storage Activities

Store monitoring snapshots and send alert notifications.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from temporalio import activity

from app.models.monitoring import AgentAlert
from app.temporal.activities.monitoring.monitoring_models import (
    AlertInfo,
    SendAlertNotificationsInput,
    SendAlertNotificationsOutput,
    StoreMonitoringSnapshotInput,
    StoreMonitoringSnapshotOutput,
)
from app.temporal.database import get_worker_session

logger = logging.getLogger(__name__)


@activity.defn
async def store_monitoring_snapshot(input: StoreMonitoringSnapshotInput) -> StoreMonitoringSnapshotOutput:
    """Store monitoring snapshot to database.

    Creates a record in agent_monitoring table with:
    - Check time
    - Overall status
    - Metrics (JSONB)
    - Alerts generated (JSONB)
    - Report summary
    """
    from app.services.monitoring_storage import save_monitoring_snapshot

    # Build unified metrics dict from input
    unified_metrics = {
        "test_health": input.metrics.test_health or {},
        "agent_performance": input.metrics.agent_performance or {},
        "resource_usage": input.metrics.resource_usage or {},
        "schedule_status": input.metrics.schedule_status or {},
    }

    # Use the centralized storage service
    snapshot_id = await save_monitoring_snapshot(unified_metrics, input.status)

    if snapshot_id is None:
        logger.error("Failed to store monitoring snapshot")
        raise Exception("Failed to store monitoring snapshot")

    logger.info(f"Stored monitoring snapshot ID {snapshot_id} with status {input.status}")

    return StoreMonitoringSnapshotOutput(
        monitoring_id=snapshot_id,
        check_time=datetime.utcnow(),
        status=input.status,
    )


@activity.defn
async def send_alert_notifications(input: SendAlertNotificationsInput) -> SendAlertNotificationsOutput:
    """Send alert notifications via configured channels.

    For now, stores alerts to database. In future, will send:
    - Email notifications
    - Webhook calls
    - System notifications
    """
    async with get_worker_session() as session:
        notification_details = []

        for alert in input.alerts:
            # Store alert to database
            agent_alert = AgentAlert(
                alert_type=alert.alert_type,
                severity=alert.severity,
                title=alert.title,
                description=alert.description,
                metrics_snapshot=alert.metrics_snapshot,
            )

            session.add(agent_alert)
            await session.flush()

            notification_details.append({
                "alert_id": agent_alert.id,
                "type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
            })

        await session.commit()

        logger.info(f"Stored {len(input.alerts)} alerts to database")

        # TODO: Send email notifications
        # TODO: Send webhook notifications

        return SendAlertNotificationsOutput(
            notifications_sent=len(input.alerts),
            notification_details=notification_details,
        )

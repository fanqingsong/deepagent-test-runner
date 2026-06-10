"""
Monitoring Agent Workflow

Temporal workflow for continuous system health monitoring.
Runs periodically to collect metrics, analyze health, and send alerts.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict

from temporalio import workflow
from temporalio.workflow import query

from app.temporal.activities import get_default_retry_policy
from app.temporal.activities.monitoring_activities import (
    CollectSystemMetricsInput,
    CollectSystemMetricsOutput,
    AnalyzeHealthMetricsInput,
    AnalyzeHealthMetricsOutput,
    StoreMonitoringSnapshotInput,
    StoreMonitoringSnapshotOutput,
    SendAlertNotificationsInput,
    SendAlertNotificationsOutput,
    collect_system_metrics,
    analyze_health_metrics,
    store_monitoring_snapshot,
    send_alert_notifications,
)

logger = logging.getLogger(__name__)


# Default timeouts
DEFAULT_CHECK_TIMEOUT = 300  # 5 minutes
DEFAULT_ANALYSIS_TIMEOUT = 120  # 2 minutes
DEFAULT_STORAGE_TIMEOUT = 120  # 2 minutes
DEFAULT_NOTIFICATION_TIMEOUT = 300  # 5 minutes


@dataclass
class MonitoringConfig:
    """Configuration for the monitoring workflow."""
    time_range_hours: int = 24  # Time window for metrics collection
    check_interval_seconds: int = 300  # How often to run checks (5 minutes)
    enabled: bool = True


@workflow.defn(sandboxed=False)
class MonitoringAgentWorkflow:
    """
    Continuous monitoring workflow that observes system health.

    This workflow runs in a loop, periodically:
    1. Collecting system metrics (test health, agent performance, resources)
    2. Analyzing metrics for risk detection
    3. Storing monitoring snapshots
    4. Sending alert notifications when risks are detected

    The workflow is designed to run continuously as a Temporal Schedule.
    """

    def __init__(self) -> None:
        self._status: str = "initializing"
        self._last_check_time: datetime = None
        self._check_count: int = 0
        self._alerts_generated: int = 0

    @workflow.run
    async def run(self, config: MonitoringConfig) -> Dict[str, Any]:
        """
        Run the monitoring agent loop.

        Args:
            config: Monitoring configuration

        Returns:
            dict: Final workflow status summary
        """
        logger.info("MonitoringAgentWorkflow started")
        self._status = "running"

        if not config.enabled:
            logger.info("Monitoring is disabled in config, exiting")
            return {"status": "disabled", "message": "Monitoring disabled"}

        try:
            while True:
                check_start = workflow.now()

                # Step 1: Collect system metrics
                logger.info(f"Starting monitoring check #{self._check_count + 1}")
                self._status = "collecting_metrics"

                metrics_output: CollectSystemMetricsOutput = await workflow.execute_activity(
                    collect_system_metrics,
                    CollectSystemMetricsInput(time_range_hours=config.time_range_hours),
                    start_to_close_timeout=DEFAULT_CHECK_TIMEOUT,
                    retry_policy=get_default_retry_policy(),
                )

                logger.info(f"Collected metrics at {metrics_output.collected_at}")

                # Step 2: Analyze metrics for alerts
                self._status = "analyzing"

                analysis_output: AnalyzeHealthMetricsOutput = await workflow.execute_activity(
                    analyze_health_metrics,
                    AnalyzeHealthMetricsInput(metrics=metrics_output.metrics),
                    start_to_close_timeout=DEFAULT_ANALYSIS_TIMEOUT,
                    retry_policy=get_default_retry_policy(),
                )

                overall_status = analysis_output.overall_status
                alerts_count = len(analysis_output.alerts)

                logger.info(
                    f"Analysis complete: status={overall_status}, alerts={alerts_count}"
                )

                # Step 3: Send notifications if alerts detected
                if alerts_count > 0:
                    self._status = "sending_notifications"

                    notification_output: SendAlertNotificationsOutput = await workflow.execute_activity(
                        send_alert_notifications,
                        SendAlertNotificationsInput(alerts=analysis_output.alerts),
                        start_to_close_timeout=DEFAULT_NOTIFICATION_TIMEOUT,
                        retry_policy=get_default_retry_policy(),
                    )

                    self._alerts_generated += notification_output.notifications_sent
                    logger.info(f"Sent {notification_output.notifications_sent} alert notifications")

                # Step 4: Store monitoring snapshot
                self._status = "storing_snapshot"

                snapshot_output: StoreMonitoringSnapshotOutput = await workflow.execute_activity(
                    store_monitoring_snapshot,
                    StoreMonitoringSnapshotInput(
                        metrics=metrics_output.metrics,
                        alerts=analysis_output.alerts,
                        status=overall_status,
                    ),
                    start_to_close_timeout=DEFAULT_STORAGE_TIMEOUT,
                    retry_policy=get_default_retry_policy(),
                )

                # Step 5: Generate AI report (async, non-blocking)
                self._status = "generating_report"

                try:
                    from app.temporal.activities.monitoring_activities import (
                        generate_ai_report,
                        GenerateAIReportInput,
                    )

                    await workflow.execute_activity(
                        generate_ai_report,
                        GenerateAIReportInput(
                            snapshot_id=snapshot_output.monitoring_id,
                            force_regeneration=False,
                        ),
                        start_to_close_timeout=DEFAULT_ANALYSIS_TIMEOUT,
                        retry_policy=get_default_retry_policy(),
                    )
                    logger.info(f"AI report generated for snapshot {snapshot_output.monitoring_id}")
                except Exception as e:
                    logger.warning(f"Failed to generate AI report for snapshot {snapshot_output.monitoring_id}: {e}")
                    # Continue even if report generation fails

                # Update workflow state
                self._last_check_time = metrics_output.collected_at
                self._check_count += 1
                self._status = overall_status

                logger.info(
                    f"Monitoring check #{self._check_count} complete. "
                    f"Stored snapshot ID {snapshot_output.monitoring_id}, "
                    f"status={overall_status}"
                )

                # Wait for next check interval
                await asyncio.sleep(config.check_interval_seconds)

        except asyncio.CancelledError:
            logger.info("MonitoringAgentWorkflow cancelled")
            self._status = "cancelled"
            raise
        except Exception as e:
            logger.error(f"MonitoringAgentWorkflow error: {e}", exc_info=True)
            self._status = "error"
            return {
                "status": "error",
                "error": str(e),
                "check_count": self._check_count,
                "alerts_generated": self._alerts_generated,
            }

    @workflow.query
    def get_status(self) -> Dict[str, Any]:
        """Query the current status of the monitoring workflow."""
        return {
            "status": self._status,
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None,
            "check_count": self._check_count,
            "alerts_generated": self._alerts_generated,
        }

    @workflow.query
    def is_running(self) -> bool:
        """Query if the monitoring workflow is currently running."""
        return self._status in ("running", "collecting_metrics", "analyzing", "storing_snapshot", "sending_notifications")

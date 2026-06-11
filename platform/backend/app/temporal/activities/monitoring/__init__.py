"""
Monitoring Activities Package

Temporal activities for system health monitoring and alerting.
Re-exports all activities for backward compatibility.
"""

# Re-export data models
from app.temporal.activities.monitoring.monitoring_models import (
    AlertInfo,
    AnalyzeHealthMetricsInput,
    AnalyzeHealthMetricsOutput,
    CollectSystemMetricsInput,
    CollectSystemMetricsOutput,
    GenerateAIReportInput,
    GenerateAIReportOutput,
    SendAlertNotificationsInput,
    SendAlertNotificationsOutput,
    StoreMonitoringSnapshotInput,
    StoreMonitoringSnapshotOutput,
    SystemMetrics,
)

# Re-export activities
from app.temporal.activities.monitoring.monitoring_collection import collect_system_metrics
from app.temporal.activities.monitoring.monitoring_analysis import analyze_health_metrics
from app.temporal.activities.monitoring.monitoring_storage import (
    send_alert_notifications,
    store_monitoring_snapshot,
)
from app.temporal.activities.monitoring.monitoring_reports import generate_ai_report

__all__ = [
    # Models
    "SystemMetrics",
    "AlertInfo",
    "CollectSystemMetricsInput",
    "CollectSystemMetricsOutput",
    "AnalyzeHealthMetricsInput",
    "AnalyzeHealthMetricsOutput",
    "StoreMonitoringSnapshotInput",
    "StoreMonitoringSnapshotOutput",
    "SendAlertNotificationsInput",
    "SendAlertNotificationsOutput",
    "GenerateAIReportInput",
    "GenerateAIReportOutput",
    # Activities
    "collect_system_metrics",
    "analyze_health_metrics",
    "store_monitoring_snapshot",
    "send_alert_notifications",
    "generate_ai_report",
]

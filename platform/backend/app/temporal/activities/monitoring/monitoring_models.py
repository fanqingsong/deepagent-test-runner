"""
Monitoring Data Models

Input/output dataclasses for monitoring activities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SystemMetrics:
    """System health metrics."""
    test_health: Dict[str, Any] = field(default_factory=dict)
    agent_performance: Dict[str, Any] = field(default_factory=dict)
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    schedule_status: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectSystemMetricsInput:
    """Input for collect_system_metrics activity."""
    time_range_hours: int = 24


@dataclass
class CollectSystemMetricsOutput:
    """Output from collect_system_metrics activity."""
    metrics: SystemMetrics
    collected_at: datetime


@dataclass
class AlertInfo:
    """Information about a generated alert."""
    alert_type: str
    severity: str
    title: str
    description: str
    metrics_snapshot: Dict[str, Any]


@dataclass
class AnalyzeHealthMetricsInput:
    """Input for analyze_health_metrics activity."""
    metrics: SystemMetrics


@dataclass
class AnalyzeHealthMetricsOutput:
    """Output from analyze_health_metrics activity."""
    alerts: List[AlertInfo] = field(default_factory=list)
    overall_status: str = "normal"  # normal, warning, critical
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StoreMonitoringSnapshotInput:
    """Input for store_monitoring_snapshot activity."""
    metrics: SystemMetrics
    alerts: List[AlertInfo]
    status: str
    report_summary: Optional[str] = None


@dataclass
class StoreMonitoringSnapshotOutput:
    """Output from store_monitoring_snapshot activity."""
    monitoring_id: int
    check_time: datetime
    status: str


@dataclass
class SendAlertNotificationsInput:
    """Input for send_alert_notifications activity."""
    alerts: List[AlertInfo]


@dataclass
class SendAlertNotificationsOutput:
    """Output from send_alert_notifications activity."""
    notifications_sent: int
    notification_details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class GenerateAIReportInput:
    """Input for generate_ai_report activity."""
    snapshot_id: int
    force_regeneration: bool = False


@dataclass
class GenerateAIReportOutput:
    """Output from generate_ai_report activity."""
    success: bool
    report_summary: Optional[str] = None
    error: Optional[str] = None
    snapshot_id: int = 0

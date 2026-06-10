"""
Monitoring Activities

Temporal activities for system health monitoring and alerting.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.temporal.activities import get_default_retry_policy
from app.temporal.database import get_worker_session
from app.models.monitoring import AgentMonitoring, AgentAlert
from temporalio import activity

logger = logging.getLogger(__name__)


# Input/Output Models for Activities


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


# Activities


@activity.defn
async def collect_system_metrics(input: CollectSystemMetricsInput) -> CollectSystemMetricsOutput:
    """Collect system health metrics from the database.

    Queries:
    - Test runs health (failure rates, recent runs)
    - Agent performance (from llm_usage)
    - Resource usage (token consumption)
    - Schedule status (missed runs, active schedules)
    """
    from app.services.monitoring_collector import collect_all_metrics

    # Use the new centralized collector service
    all_metrics = await collect_all_metrics()

    collected_at = datetime.utcnow()
    metrics = SystemMetrics()

    # Map to the existing structure
    metrics.test_health = all_metrics.get("test_execution", {})
    metrics.agent_performance = all_metrics.get("llm_performance", {})
    metrics.resource_usage = all_metrics.get("resources", {})
    metrics.schedule_status = all_metrics.get("test_execution", {}).get("schedules", {})

    logger.info(f"Collected system metrics at {collected_at}")

    return CollectSystemMetricsOutput(
        metrics=metrics,
        collected_at=collected_at,
    )


async def _collect_test_health(session: AsyncSession, hours: int) -> Dict[str, Any]:
    """Collect test execution health metrics."""
    from app.models.test_run import TestRun
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Total runs in time range
    total_runs_result = await session.execute(
        select(sql_func.count()).select_from(TestRun).where(TestRun.created_at >= cutoff)
    )
    total_runs = total_runs_result.scalar() or 0

    # Failed runs
    failed_runs_result = await session.execute(
        select(sql_func.count())
        .select_from(TestRun)
        .where(TestRun.created_at >= cutoff)
        .where(TestRun.status == "failed")
    )
    failed_runs = failed_runs_result.scalar() or 0

    # Calculate failure rate
    failure_rate = (failed_runs / total_runs * 100) if total_runs > 0 else 0

    # Get recent failures (last 10)
    recent_failures_result = await session.execute(
        select(TestRun)
        .where(TestRun.status == "failed")
        .where(TestRun.created_at >= cutoff)
        .order_by(TestRun.created_at.desc())
        .limit(10)
    )
    recent_failures = recent_failures_result.scalars().all()

    return {
        "total_runs": total_runs,
        "failed_runs": failed_runs,
        "failure_rate": round(failure_rate, 2),
        "recent_failures": [
            {"id": str(r.id), "test_definition_id": str(r.test_definition_id), "created_at": r.created_at.isoformat()}
            for r in recent_failures
        ],
    }


async def _collect_agent_performance(session: AsyncSession, hours: int) -> Dict[str, Any]:
    """Collect LLM agent performance metrics."""
    from app.models.llm_usage import LlmUsage
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Average duration by agent type
    avg_duration_result = await session.execute(
        select(
            LlmUsage.agent_type,
            sql_func.avg(LlmUsage.duration_ms).label("avg_duration"),
            sql_func.count().label("call_count"),
        )
        .where(LlmUsage.created_at >= cutoff)
        .group_by(LlmUsage.agent_type)
    )
    agent_stats = []
    for row in avg_duration_result.all():
        agent_stats.append({
            "agent_type": row.agent_type,
            "avg_duration_ms": round(row.avg_duration or 0, 2),
            "call_count": row.call_count,
        })

    # Total calls
    total_calls_result = await session.execute(
        select(sql_func.count()).select_from(LlmUsage).where(LlmUsage.created_at >= cutoff)
    )
    total_calls = total_calls_result.scalar() or 0

    return {
        "total_calls": total_calls,
        "by_agent": agent_stats,
    }


async def _collect_resource_usage(session: AsyncSession, hours: int) -> Dict[str, Any]:
    """Collect resource usage metrics (tokens, etc.)."""
    from app.models.llm_usage import LlmUsage
    from datetime import timedelta
    import os

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Total tokens used
    tokens_result = await session.execute(
        select(sql_func.sum(LlmUsage.total_tokens))
        .select_from(LlmUsage)
        .where(LlmUsage.created_at >= cutoff)
    )
    total_tokens = tokens_result.scalar() or 0

    # Get daily budget from env
    daily_budget = int(os.getenv("MONITORING_TOKEN_BUDGET_DAILY", "1000000"))

    # Calculate budget usage percentage
    budget_pct = (total_tokens / daily_budget * 100) if daily_budget > 0 else 0

    return {
        "total_tokens": total_tokens,
        "daily_budget": daily_budget,
        "budget_usage_percent": round(budget_pct, 2),
    }


async def _collect_schedule_status(session: AsyncSession) -> Dict[str, Any]:
    """Collect schedule execution status."""
    from app.models.schedule import Schedule

    # Total active schedules
    active_schedules_result = await session.execute(
        select(sql_func.count())
        .select_from(Schedule)
        .where(Schedule.is_active == True)
    )
    active_schedules = active_schedules_result.scalar() or 0

    return {
        "active_schedules": active_schedules,
    }


@activity.defn
async def analyze_health_metrics(input: AnalyzeHealthMetricsInput) -> AnalyzeHealthMetricsOutput:
    """Analyze health metrics and detect alerts.

    Checks for:
    - High failure rates
    - Slow agent response times
    - Token budget overruns
    - Schedule issues
    """
    alerts = []
    metrics = input.metrics
    analysis_timestamp = datetime.utcnow()

    # Check test failure rate
    test_health = metrics.test_health or {}
    failure_rate = test_health.get("failure_rate", 0)
    total_runs = test_health.get("total_runs", 0)

    if total_runs >= 5 and failure_rate >= 50:
        alerts.append(
            AlertInfo(
                alert_type="high_failure_rate",
                severity="critical",
                title=f"Test failure rate at {failure_rate}%",
                description=f"{test_health.get('failed_runs', 0)} out of {total_runs} test runs failed in the monitoring period.",
                metrics_snapshot={"test_health": test_health},
            )
        )
    elif total_runs >= 3 and failure_rate >= 20:
        alerts.append(
            AlertInfo(
                alert_type="elevated_failure_rate",
                severity="warning",
                title=f"Test failure rate elevated at {failure_rate}%",
                description=f"{test_health.get('failed_runs', 0)} out of {total_runs} test runs failed.",
                metrics_snapshot={"test_health": test_health},
            )
        )

    # Check agent performance
    agent_perf = metrics.agent_performance or {}
    for agent_stat in agent_perf.get("by_agent", []):
        avg_duration = agent_stat.get("avg_duration_ms", 0)
        if avg_duration > 30000:  # 30 seconds
            alerts.append(
                AlertInfo(
                    alert_type="agent_slow_response",
                    severity="warning",
                    title=f"{agent_stat['agent_type']} slow response time",
                    description=f"Average response time of {avg_duration/1000:.1f}s exceeds 30s threshold.",
                    metrics_snapshot={"agent": agent_stat},
                )
            )

    # Check token budget
    resources = metrics.resource_usage or {}
    budget_pct = resources.get("budget_usage_percent", 0)

    if budget_pct >= 95:
        alerts.append(
            AlertInfo(
                alert_type="token_budget_critical",
                severity="critical",
                title=f"Token budget at {budget_pct}%",
                description=f"Token usage ({resources.get('total_tokens', 0)}) is at {budget_pct}% of daily budget.",
                metrics_snapshot={"resource_usage": resources},
            )
        )
    elif budget_pct >= 80:
        alerts.append(
            AlertInfo(
                alert_type="token_budget_warning",
                severity="warning",
                title=f"Token budget at {budget_pct}%",
                description=f"Token usage ({resources.get('total_tokens', 0)}) is at {budget_pct}% of daily budget.",
                metrics_snapshot={"resource_usage": resources},
            )
        )

    # Determine overall status
    overall_status = "normal"
    for alert in alerts:
        if alert.severity == "critical":
            overall_status = "critical"
            break
        elif alert.severity == "warning" and overall_status != "critical":
            overall_status = "warning"

    logger.info(f"Analysis complete: {overall_status} status, {len(alerts)} alerts")

    return AnalyzeHealthMetricsOutput(
        alerts=alerts,
        overall_status=overall_status,
        analysis_timestamp=analysis_timestamp,
    )


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

    # Use the new centralized storage service
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


# AI Report Generation Activities


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


@activity.defn
async def generate_ai_report(input: GenerateAIReportInput) -> GenerateAIReportOutput:
    """Generate AI-powered monitoring report using the reporter agent.

    Args:
        input: Contains snapshot_id and optional force_regeneration flag

    Returns:
        Output with success status and report summary
    """
    from app.services.monitoring_report_service import generate_daily_report

    try:
        logger.info(f"Generating AI report for snapshot {input.snapshot_id}")

        result = await generate_daily_report(snapshot_id=input.snapshot_id)

        if result.get("success"):
            return GenerateAIReportOutput(
                success=True,
                report_summary=result.get("report"),
                snapshot_id=input.snapshot_id,
            )
        else:
            return GenerateAIReportOutput(
                success=False,
                error=result.get("error", "Unknown error"),
                snapshot_id=input.snapshot_id,
            )

    except Exception as e:
        logger.error(f"Failed to generate AI report for snapshot {input.snapshot_id}: {e}", exc_info=True)
        return GenerateAIReportOutput(
            success=False,
            error=str(e),
            snapshot_id=input.snapshot_id,
        )

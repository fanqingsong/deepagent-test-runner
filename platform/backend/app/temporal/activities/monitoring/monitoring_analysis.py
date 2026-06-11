"""
Monitoring Analysis Activity

Analyze health metrics and detect alerts.
"""

import logging
from datetime import datetime

from temporalio import activity

from app.temporal.activities.monitoring.monitoring_models import (
    AlertInfo,
    AnalyzeHealthMetricsInput,
    AnalyzeHealthMetricsOutput,
)

logger = logging.getLogger(__name__)


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

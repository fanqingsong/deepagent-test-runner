"""
Monitoring Collection Activity

Collect system health metrics from the database.
"""

import logging
from datetime import datetime

from temporalio import activity

from app.temporal.activities.monitoring.monitoring_models import (
    CollectSystemMetricsInput,
    CollectSystemMetricsOutput,
    SystemMetrics,
)

logger = logging.getLogger(__name__)


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

    # Use the centralized collector service
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

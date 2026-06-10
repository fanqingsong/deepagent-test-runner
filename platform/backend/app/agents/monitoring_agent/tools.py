"""
Monitoring Agent Tools

Tools for the DeepAgent monitoring reporter to access system data.
"""

import logging
from typing import Any, Dict

from app.services.monitoring_storage import (
    get_latest_snapshot,
    get_historical_metrics,
    get_snapshot_for_comparison,
)

logger = logging.getLogger(__name__)


def get_current_metrics() -> Dict[str, Any]:
    """
    Get the latest monitoring snapshot.

    Returns:
        Dict with latest system metrics or error info
    """
    import asyncio

    snapshot = asyncio.run(get_latest_snapshot())

    if snapshot is None:
        return {
            "error": "No monitoring snapshots available",
            "metrics": None,
        }

    return {
        "snapshot_id": snapshot.get("id"),
        "check_time": snapshot.get("check_time"),
        "status": snapshot.get("status"),
        "metrics": snapshot.get("metrics"),
        "report_summary": snapshot.get("report_summary"),
    }


def get_historical_trends(days: int = 7) -> Dict[str, Any]:
    """
    Get historical monitoring data for trend analysis.

    Args:
        days: Number of days of history to retrieve

    Returns:
        Dict with historical metrics and trend analysis
    """
    import asyncio

    snapshots = asyncio.run(get_historical_metrics(days=days))

    if not snapshots:
        return {
            "error": "No historical data available",
            "snapshots": [],
        }

    # Calculate basic trends
    if len(snapshots) >= 2:
        latest = snapshots[0]
        previous = snapshots[-1]  # Oldest snapshot

        latest_status = latest.get("metrics", {})
        previous_status = previous.get("metrics", {})

        # Test health trends
        latest_runs = latest_status.get("test_execution", {}).get("test_runs_24h", {})
        previous_runs = previous_status.get("test_execution", {}).get("test_runs_24h", {})

        latest_pass_rate = latest_runs.get("pass_rate", 0)
        previous_pass_rate = previous_runs.get("pass_rate", 0)

        pass_rate_change = latest_pass_rate - previous_pass_rate

        # LLM trends
        latest_llm = latest_status.get("llm_performance", {}).get("token_usage_24h", {})
        previous_llm = previous_status.get("llm_performance", {}).get("token_usage_24h", {})

        latest_tokens = latest_llm.get("total_tokens", 0)
        previous_tokens = previous_llm.get("total_tokens", 0)

        token_change = latest_tokens - previous_tokens
        token_pct_change = (token_change / previous_tokens * 100) if previous_tokens > 0 else 0

        return {
            "snapshots_count": len(snapshots),
            "time_range_days": days,
            "trends": {
                "test_pass_rate": {
                    "current": latest_pass_rate,
                    "previous": previous_pass_rate,
                    "change": round(pass_rate_change, 2),
                    "direction": "up" if pass_rate_change > 0 else "down" if pass_rate_change < 0 else "stable",
                },
                "token_usage": {
                    "current": latest_tokens,
                    "previous": previous_tokens,
                    "change": token_change,
                    "percent_change": round(token_pct_change, 2),
                    "direction": "up" if token_change > 0 else "down" if token_change < 0 else "stable",
                },
            },
        }

    return {
        "snapshots_count": len(snapshots),
        "time_range_days": days,
        "trends": None,
        "message": "Not enough data for trend analysis",
    }


def get_active_alerts() -> Dict[str, Any]:
    """
    Get current active (unacknowledged) alerts.

    Returns:
        Dict with active alerts information
    """
    from app.core.database import sync_session_maker
    from app.models.monitoring import AgentAlert
    from sqlalchemy import select, desc
    import asyncio

    # Use sync DB for agent tool context
    def _get_alerts():
        db = sync_session_maker()

        try:
            # acknowledged is stored as Integer (0/1), not boolean
            stmt = (
                select(AgentAlert)
                .where(AgentAlert.acknowledged == 0)
                .order_by(desc(AgentAlert.created_at))
                .limit(20)
            )
            result = db.execute(stmt)
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
        finally:
            db.close()

    alerts = _get_alerts()

    return {
        "active_alerts_count": len(alerts),
        "alerts": alerts,
    }


def get_comparison_data(hours_ago: int = 24) -> Dict[str, Any]:
    """
    Get snapshot data from a specific time ago for comparison.

    Args:
        hours_ago: How many hours back to look

    Returns:
        Dict with comparison snapshot data
    """
    import asyncio

    snapshot = asyncio.run(get_snapshot_for_comparison(hours_ago=hours_ago))

    if snapshot is None:
        return {
            "error": f"No comparison snapshot available for {hours_ago}h ago",
            "snapshot": None,
        }

    return {
        "hours_ago": hours_ago,
        "snapshot": snapshot,
    }

"""
Monitoring Report Service

Orchestrates AI-powered report generation using the monitoring reporter agent.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from app.agents.monitoring_agent import get_monitoring_reporter_agent
from app.services.monitoring_storage import update_snapshot_report

logger = logging.getLogger(__name__)


async def generate_daily_report(snapshot_id: int) -> Dict[str, Any]:
    """
    Generate an AI-powered daily monitoring report.

    Args:
        snapshot_id: ID of the monitoring snapshot to generate report for

    Returns:
        Dict with report generation result
    """
    logger.info(f"Generating daily report for snapshot {snapshot_id}")

    try:
        # Get the reporter agent
        agent = await get_monitoring_reporter_agent()

        # Generate the report with context
        # DeepAgent expects a dict with 'messages' key, not a string
        prompt = f"""Generate a comprehensive monitoring report for the current system state.

Use your available tools to:
1. Get the latest metrics (current snapshot)
2. Analyze historical trends (7-day comparison)
3. Check for active alerts
4. Provide actionable recommendations

Focus on clarity and actionable insights. Include specific numbers and percentages."""

        # Invoke the agent with proper state format
        response = await agent.ainvoke({"messages": [prompt]})

        # Extract the report content from the response
        # DeepAgent returns a dict with 'messages' key containing the response
        if isinstance(response, dict):
            messages = response.get("messages", [])
            if messages:
                # Get the last message content
                last_message = messages[-1]
                if hasattr(last_message, 'content'):
                    report_content = last_message.content
                elif isinstance(last_message, dict) and 'content' in last_message:
                    report_content = last_message['content']
                else:
                    report_content = str(last_message)
            else:
                report_content = str(response)
        else:
            report_content = str(response)

        # Save the report to the snapshot
        updated = await update_snapshot_report(snapshot_id, report_content)

        if updated:
            logger.info(f"Successfully generated and saved report for snapshot {snapshot_id}")
            return {
                "success": True,
                "snapshot_id": snapshot_id,
                "report": report_content,
                "generated_at": datetime.utcnow().isoformat(),
            }
        else:
            logger.warning(f"Report generated but failed to save for snapshot {snapshot_id}")
            return {
                "success": False,
                "error": "Failed to save report to database",
                "report": report_content,
            }

    except Exception as e:
        logger.error(f"Failed to generate report for snapshot {snapshot_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "snapshot_id": snapshot_id,
        }


async def generate_report_summary(metrics: Dict[str, Any], status: str) -> str:
    """
    Generate a quick summary for a monitoring snapshot without full agent invocation.

    Args:
        metrics: Collected metrics dictionary
        status: Overall system status

    Returns:
        Generated summary text
    """
    # Extract key metrics
    test_health = metrics.get("test_execution", {}).get("test_runs_24h", {})
    llm_perf = metrics.get("llm_performance", {})
    resources = metrics.get("resources", {})
    alerts = metrics.get("active_alerts", 0)

    total_runs = test_health.get("total", 0)
    pass_rate = test_health.get("pass_rate", 0.0) * 100
    failed_runs = test_health.get("failed", 0)

    # Build a simple summary
    summary_parts = []

    if status == "normal":
        summary_parts.append(f"System is healthy.")
    elif status == "warning":
        summary_parts.append(f"System needs attention.")
    else:
        summary_parts.append(f"System has critical issues.")

    if total_runs > 0:
        summary_parts.append(
            f" {total_runs} test runs completed with {pass_rate:.0f}% pass rate."
        )

    if failed_runs > 0:
        summary_parts.append(f" {failed_runs} tests failed.")

    if alerts > 0:
        summary_parts.append(f" {alerts} active alerts.")

    return "".join(summary_parts)

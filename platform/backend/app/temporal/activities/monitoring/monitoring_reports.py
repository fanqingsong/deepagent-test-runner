"""
Monitoring Report Generation Activity

Generate AI-powered monitoring reports.
"""

import logging

from temporalio import activity

from app.temporal.activities.monitoring.monitoring_models import (
    GenerateAIReportInput,
    GenerateAIReportOutput,
)

logger = logging.getLogger(__name__)


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

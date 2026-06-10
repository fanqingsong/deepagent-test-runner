# service/backend/app/temporal/client.py
from datetime import timedelta
from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleState
from app.temporal.settings import settings
from app.temporal.workflows.monitoring_workflow import MonitoringAgentWorkflow, MonitoringConfig
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

_client: Optional[Client] = None

async def get_temporal_client() -> Client:
    """
    Get or create the Temporal client singleton.

    Returns:
        Client: Connected Temporal client instance

    Raises:
        RuntimeError: If client connection fails
    """
    global _client

    if _client is None:
        try:
            _client = await Client.connect(
                settings.host_url,
                namespace=settings.namespace
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to Temporal server at {settings.host_url}: {e}"
            )

    return _client

async def close_temporal_client() -> None:
    """Close the Temporal client connection."""
    global _client

    if _client is not None:
        await _client.close()
        _client = None


async def start_monitoring_schedule(
    schedule_id: str = "monitoring-agent-schedule",
    enabled: bool = None,
    check_interval_seconds: int = None,
    time_range_hours: int = None,
) -> dict:
    """
    Start the Monitoring Agent workflow as a Temporal Schedule.

    Creates a cron-based schedule that runs the monitoring workflow
    at the specified interval to collect metrics, analyze health,
    and send alerts.

    Args:
        schedule_id: Unique identifier for the schedule
        enabled: Whether monitoring is enabled (from env var MONITORING_ENABLED)
        check_interval_seconds: How often to run checks (from env var MONITORING_CHECK_INTERVAL)
        time_range_hours: Time window for metrics collection (default: 24 hours)

    Returns:
        dict: Schedule creation result with schedule ID and info

    Raises:
        RuntimeError: If Temporal connection fails or schedule creation fails
    """
    client = await get_temporal_client()

    # Get configuration from environment variables
    is_enabled = enabled if enabled is not None else os.getenv("MONITORING_ENABLED", "true").lower() == "true"
    interval = check_interval_seconds or int(os.getenv("MONITORING_CHECK_INTERVAL", "300"))  # 5 minutes default
    hours = time_range_hours or int(os.getenv("MONITORING_TIME_RANGE_HOURS", "24"))  # 24 hours default

    if not is_enabled:
        logger.info("Monitoring is disabled (MONITORING_ENABLED=false)")
        return {
            "schedule_id": schedule_id,
            "enabled": False,
            "message": "Monitoring is disabled",
        }

    try:
        # Delete existing schedule if it exists
        try:
            handle = client.get_schedule_handle(schedule_id)
            await handle.delete()
            logger.info(f"Deleted existing monitoring schedule: {schedule_id}")
        except Exception:
            # Schedule doesn't exist, that's fine
            pass

        # Create schedule config
        monitoring_config = MonitoringConfig(
            time_range_hours=hours,
            check_interval_seconds=interval,
            enabled=True,
        )

        # Create the schedule
        # Note: We use a cron expression that runs every N minutes
        # For 5 minutes: "*/5 * * * *" (every 5 minutes)
        cron_minutes = interval // 60
        cron_expression = f"*/{max(1, cron_minutes)} * * * *"

        await client.create_schedule(
            schedule_id,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    MonitoringAgentWorkflow.run,
                    args=[monitoring_config],
                    id=f"{schedule_id}-run",
                    task_queue=settings.task_queue,
                ),
                spec=ScheduleSpec(cron_expressions=[cron_expression]),
                state=ScheduleState(paused=False),
            ),
        )

        logger.info(
            f"Created monitoring schedule '{schedule_id}' with cron '{cron_expression}' "
            f"(every {interval}s, {hours}h time range)"
        )

        return {
            "schedule_id": schedule_id,
            "enabled": True,
            "cron_expression": cron_expression,
            "check_interval_seconds": interval,
            "time_range_hours": hours,
            "message": "Monitoring schedule created successfully",
        }

    except Exception as e:
        logger.error(f"Failed to create monitoring schedule: {e}")
        raise RuntimeError(f"Failed to create monitoring schedule: {e}")


async def stop_monitoring_schedule(
    schedule_id: str = "monitoring-agent-schedule",
) -> dict:
    """
    Stop the Monitoring Agent Temporal Schedule.

    Args:
        schedule_id: The schedule ID to stop

    Returns:
        dict: Schedule deletion result

    Raises:
        RuntimeError: If Temporal connection fails or schedule deletion fails
    """
    client = await get_temporal_client()

    try:
        handle = client.get_schedule_handle(schedule_id)
        await handle.delete()

        logger.info(f"Stopped monitoring schedule: {schedule_id}")

        return {
            "schedule_id": schedule_id,
            "message": "Monitoring schedule stopped successfully",
        }

    except Exception as e:
        logger.error(f"Failed to stop monitoring schedule: {e}")
        raise RuntimeError(f"Failed to stop monitoring schedule: {e}")


async def get_monitoring_schedule_status(
    schedule_id: str = "monitoring-agent-schedule",
) -> dict:
    """
    Get the status of the Monitoring Agent Schedule.

    Args:
        schedule_id: The schedule ID to check

    Returns:
        dict: Schedule status information

    Raises:
        RuntimeError: If Temporal connection fails or schedule fetch fails
    """
    client = await get_temporal_client()

    try:
        handle = client.get_schedule_handle(schedule_id)
        desc = await handle.describe()

        # Extract next action times
        upcoming = []
        for t in (desc.info.next_action_times or []):
            upcoming.append(t.isoformat() if hasattr(t, "isoformat") else str(t))

        return {
            "schedule_id": schedule_id,
            "exists": True,
            "paused": desc.schedule.state.paused,
            "note": desc.schedule.state.note,
            "next_action_times": upcoming,
        }

    except Exception as e:
        # Schedule doesn't exist
        logger.info(f"Monitoring schedule '{schedule_id}' does not exist: {e}")
        return {
            "schedule_id": schedule_id,
            "exists": False,
            "message": "Monitoring schedule not found",
        }

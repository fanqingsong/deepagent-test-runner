"""
Temporal Schedule Service

Wraps Temporal Schedule API for cron-based test execution.
DB is source of truth; Temporal is the execution engine.
All methods gracefully handle Temporal unavailability.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    ScheduleState,
    ScheduleUpdate,
)

from app.temporal import get_temporal_client
from app.temporal.workflows.schedules import ScheduleExecutionWorkflow

logger = logging.getLogger(__name__)

TASK_QUEUE = "unified-backend-task-queue"


def _schedule_id(db_id: int) -> str:
    return f"schedule-{db_id}"


async def _get_client() -> Optional[Client]:
    try:
        return await get_temporal_client()
    except Exception as e:
        logger.warning("Temporal client unavailable: %s", e)
        return None


async def create(
    schedule_id: int,
    cron_expression: str,
    test_definition_id: str,
    is_active: bool = True,
) -> bool:
    """Create a Temporal Schedule for the given DB schedule."""
    client = await _get_client()
    if not client:
        logger.warning("Skipping Temporal schedule creation for %d (unavailable)", schedule_id)
        return False

    try:
        await client.create_schedule(
            _schedule_id(schedule_id),
            Schedule(
                action=ScheduleActionStartWorkflow(
                    ScheduleExecutionWorkflow.run,
                    args=[schedule_id, test_definition_id],
                    id=f"schedule-exec-{schedule_id}",
                    task_queue=TASK_QUEUE,
                ),
                spec=ScheduleSpec(cron_expressions=[cron_expression]),
                state=ScheduleState(paused=not is_active),
            ),
        )
        logger.info("Created Temporal schedule %s (cron=%s)", _schedule_id(schedule_id), cron_expression)
        return True
    except Exception as e:
        logger.error("Failed to create Temporal schedule for %d: %s", schedule_id, e)
        return False


async def update(
    schedule_id: int,
    cron_expression: str,
    test_definition_id: str,
    is_active: bool,
) -> bool:
    """Update an existing Temporal Schedule."""
    client = await _get_client()
    if not client:
        return False

    try:
        handle = client.get_schedule_handle(_schedule_id(schedule_id))

        async def _updater(input) -> ScheduleUpdate:
            return ScheduleUpdate(
                schedule=Schedule(
                    action=ScheduleActionStartWorkflow(
                        ScheduleExecutionWorkflow.run,
                        args=[schedule_id, test_definition_id],
                        id=f"schedule-exec-{schedule_id}",
                        task_queue=TASK_QUEUE,
                    ),
                    spec=ScheduleSpec(cron_expressions=[cron_expression]),
                    state=ScheduleState(paused=not is_active),
                ),
            )

        await handle.update(_updater)
        logger.info("Updated Temporal schedule %s", _schedule_id(schedule_id))
        return True
    except Exception as e:
        logger.error("Failed to update Temporal schedule for %d: %s", schedule_id, e)
        return False


async def pause(schedule_id: int) -> bool:
    """Pause a Temporal Schedule (when DB schedule is set inactive)."""
    client = await _get_client()
    if not client:
        return False

    try:
        handle = client.get_schedule_handle(_schedule_id(schedule_id))
        await handle.pause(note="Disabled by user")
        logger.info("Paused Temporal schedule %s", _schedule_id(schedule_id))
        return True
    except Exception as e:
        logger.error("Failed to pause Temporal schedule for %d: %s", schedule_id, e)
        return False


async def unpause(schedule_id: int) -> bool:
    """Unpause a Temporal Schedule (when DB schedule is set active)."""
    client = await _get_client()
    if not client:
        return False

    try:
        handle = client.get_schedule_handle(_schedule_id(schedule_id))
        await handle.unpause(note="Enabled by user")
        logger.info("Unpaused Temporal schedule %s", _schedule_id(schedule_id))
        return True
    except Exception as e:
        logger.error("Failed to unpause Temporal schedule for %d: %s", schedule_id, e)
        return False


async def delete(schedule_id: int) -> bool:
    """Delete a Temporal Schedule."""
    client = await _get_client()
    if not client:
        return False

    try:
        handle = client.get_schedule_handle(_schedule_id(schedule_id))
        await handle.delete()
        logger.info("Deleted Temporal schedule %s", _schedule_id(schedule_id))
        return True
    except Exception as e:
        logger.error("Failed to delete Temporal schedule for %d: %s", schedule_id, e)
        return False


async def describe(schedule_id: int) -> Optional[Dict[str, Any]]:
    """Get schedule description from Temporal for observability.

    Returns dict with recent_actions, next_action_times, paused, note,
    or None if Temporal is unavailable or schedule doesn't exist.
    """
    client = await _get_client()
    if not client:
        return None

    try:
        handle = client.get_schedule_handle(_schedule_id(schedule_id))
        desc = await handle.describe()

        recent = []
        for action in (desc.info.recent_actions or []):
            entry = {
                "schedule_time": action.actual_at.isoformat() if action.actual_at else None,
                "started_time": action.start_time.isoformat() if action.start_time else None,
            }
            if action.action:
                a = action.action
                entry["workflow_id"] = getattr(a, "workflow_id", None)
                entry["run_id"] = getattr(a, "run_id", None)
            recent.append(entry)

        upcoming = []
        for t in (desc.info.next_action_times or []):
            upcoming.append(t.isoformat() if hasattr(t, "isoformat") else str(t))

        return {
            "schedule_id": schedule_id,
            "paused": desc.schedule.state.paused,
            "note": desc.schedule.state.note,
            "recent_actions": recent,
            "next_action_times": upcoming,
        }
    except Exception as e:
        logger.warning("Failed to describe Temporal schedule for %d: %s", schedule_id, e)
        return None


async def reconcile(schedules: List[Dict[str, Any]]) -> Dict[str, int]:
    """Reconcile DB schedules with Temporal. Called on startup.

    Creates missing Temporal schedules for active DB records.
    Pauses Temporal schedules for inactive DB records.
    """
    created = 0
    paused = 0
    skipped = 0
    errors = 0

    for s in schedules:
        sid = s["id"]
        is_active = s["is_active"]
        cron = s["cron_expression"]
        test_def_id = str(s.get("test_definition_id") or s.get("test_definition_ids", [""])[0] or "")
        if not test_def_id:
            skipped += 1
            continue

        existing = await describe(sid)
        if existing is None:
            ok = await create(sid, cron, test_def_id, is_active)
            if ok:
                created += 1
            else:
                errors += 1
        else:
            if is_active and existing.get("paused"):
                await unpause(sid)
            elif not is_active and not existing.get("paused"):
                await pause(sid)
                paused += 1

    logger.info(
        "Schedule reconciliation: created=%d, paused=%d, skipped=%d, errors=%d",
        created, paused, skipped, errors,
    )
    return {"created": created, "paused": paused, "skipped": skipped, "errors": errors}

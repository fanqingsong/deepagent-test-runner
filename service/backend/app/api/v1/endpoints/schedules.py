"""
Schedules API Endpoints

Schedule CRUD + Temporal cron execution + observability.
DB is source of truth; Temporal is the execution engine.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models.schedule import Schedule
from app.models.test_run import TestRun
from app.models.user import User
from app.schemas.schedules import (
    ScheduleCreate,
    ScheduleHistoryResponse,
    ScheduleResponse,
    ScheduleToggle,
    ScheduleUpdate,
)
from app.services import temporal_schedule_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _schedule_to_response(s: Schedule) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "schedule_type": s.schedule_type,
        "test_definition_ids": s.test_definition_ids or [],
        "test_definition_id": s.test_definition_id,
        "test_suite_id": s.test_suite_id,
        "tag_filter": s.tag_filter,
        "preset_type": s.preset_type,
        "cron_expression": s.cron_expression,
        "timezone": s.timezone,
        "environment_overrides": s.environment_overrides or {},
        "is_active": s.is_active,
        "allow_concurrent": s.allow_concurrent,
        "max_retries": s.max_retries,
        "retry_interval_seconds": s.retry_interval_seconds,
        "run_config_id": s.run_config_id,
        "next_run_time": s.next_run_time.isoformat() if s.next_run_time else None,
        "last_run_time": s.last_run_time.isoformat() if s.last_run_time else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "created_by": s.created_by,
    }


def _resolve_test_definition_id(schedule: Schedule) -> Optional[str]:
    if schedule.schedule_type == "suite" and schedule.test_suite_id:
        return str(schedule.test_suite_id)
    if schedule.test_definition_id:
        return str(schedule.test_definition_id)
    if schedule.test_definition_ids:
        return str(schedule.test_definition_ids[0])
    return None


# --- CRUD ---


@router.post("/")
async def create_schedule(
    body: ScheduleCreate,
    current_user: User = Depends(RequirePermission("manage:schedules")),
    db: AsyncSession = Depends(get_db),
):
    schedule = Schedule(
        name=body.name,
        schedule_type=body.schedule_type,
        test_definition_ids=body.test_definition_ids or [],
        test_definition_id=body.test_definition_id,
        test_suite_id=body.test_suite_id,
        tag_filter=body.tag_filter,
        preset_type=body.preset_type,
        cron_expression=body.cron_expression,
        timezone=body.timezone,
        environment_overrides=body.environment_overrides,
        is_active=body.is_active,
        allow_concurrent=body.allow_concurrent,
        max_retries=body.max_retries,
        retry_interval_seconds=body.retry_interval_seconds,
        run_config_id=body.run_config_id,
        created_by=current_user.id,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    test_def_id = _resolve_test_definition_id(schedule)
    if test_def_id:
        await temporal_schedule_service.create(
            schedule.id, schedule.cron_expression, test_def_id, schedule.is_active
        )

    return _schedule_to_response(schedule)


@router.get("/")
async def list_schedules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).order_by(desc(Schedule.created_at)))
    schedules = result.scalars().all()
    return [_schedule_to_response(s) for s in schedules]


@router.get("/active")
async def list_active_schedules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Schedule)
        .where(Schedule.is_active == True)
        .order_by(desc(Schedule.created_at))
    )
    schedules = result.scalars().all()
    return [_schedule_to_response(s) for s in schedules]


@router.get("/presets")
async def list_presets(
    current_user: User = Depends(get_current_user),
):
    presets = [
        {"type": "hourly", "name": "Hourly", "cron": "0 * * * *", "description": "Run every hour"},
        {"type": "daily", "name": "Daily", "cron": "0 2 * * *", "description": "Run daily at 2:00 AM"},
        {"type": "weekly", "name": "Weekly", "cron": "0 2 * * 1", "description": "Run weekly on Monday at 2:00 AM"},
        {"type": "biweekly", "name": "Bi-weekly", "cron": "0 2 1,15 * *", "description": "Run on 1st and 15th at 2:00 AM"},
        {"type": "monthly", "name": "Monthly", "cron": "0 2 1 * *", "description": "Run monthly on the 1st at 2:00 AM"},
    ]
    return {"presets": presets}


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return _schedule_to_response(schedule)


@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    body: ScheduleUpdate,
    current_user: User = Depends(RequirePermission("manage:schedules")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)
    await db.commit()
    await db.refresh(schedule)

    test_def_id = _resolve_test_definition_id(schedule)
    if test_def_id:
        await temporal_schedule_service.update(
            schedule.id, schedule.cron_expression, test_def_id, schedule.is_active
        )

    return _schedule_to_response(schedule)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(RequirePermission("manage:schedules")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    await db.delete(schedule)
    await db.commit()

    await temporal_schedule_service.delete(schedule_id)

    return {"message": f"Schedule {schedule_id} deleted"}


# --- Toggle / Trigger ---


@router.put("/toggle/{schedule_id}")
async def toggle_schedule(
    schedule_id: int,
    body: ScheduleToggle,
    current_user: User = Depends(RequirePermission("manage:schedules")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    schedule.is_active = body.is_active
    await db.commit()
    await db.refresh(schedule)

    if body.is_active:
        await temporal_schedule_service.unpause(schedule_id)
    else:
        await temporal_schedule_service.pause(schedule_id)

    return _schedule_to_response(schedule)


@router.post("/trigger/{schedule_id}")
async def trigger_schedule(
    schedule_id: int,
    current_user: User = Depends(RequirePermission("execute:schedule")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    if not schedule.is_active:
        raise HTTPException(status_code=400, detail=f"Schedule {schedule_id} is not active")

    test_def_id = _resolve_test_definition_id(schedule)
    if not test_def_id:
        raise HTTPException(status_code=400, detail="Schedule has no valid test definitions")

    from app.workflows.schedules import ScheduleExecutionWorkflow
    from app.temporal import get_temporal_client

    client = await get_temporal_client()
    handle = await client.start_workflow(
        ScheduleExecutionWorkflow.run,
        args=[schedule_id, test_def_id],
        id=f"schedule-execution-{schedule_id}-{datetime.utcnow().timestamp()}",
        task_queue="unified-backend-task-queue",
    )

    return {
        "status": "started",
        "schedule_id": schedule_id,
        "workflow_id": handle.id,
        "run_id": handle.run_id,
    }


# --- Observability ---


@router.get("/{schedule_id}/history")
async def get_schedule_history(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    temporal_info = await temporal_schedule_service.describe(schedule_id)

    recent_actions = []
    if temporal_info:
        recent_actions = temporal_info.get("recent_actions", [])

    next_action_times = temporal_info.get("next_action_times", []) if temporal_info else []
    paused = temporal_info.get("paused", not schedule.is_active) if temporal_info else not schedule.is_active

    return {
        "schedule_id": schedule_id,
        "name": schedule.name,
        "cron_expression": schedule.cron_expression,
        "is_active": schedule.is_active,
        "paused": paused,
        "recent_actions": recent_actions,
        "next_action_times": next_action_times,
    }


@router.get("/{schedule_id}/runs")
async def get_schedule_runs(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
):
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    test_def_ids = schedule.test_definition_ids or []
    if not test_def_ids:
        return {"schedule_id": schedule_id, "runs": []}

    runs_result = await db.execute(
        select(TestRun)
        .where(TestRun.test_definition_id.in_(test_def_ids))
        .order_by(desc(TestRun.created_at))
        .limit(limit)
    )
    runs = runs_result.scalars().all()

    return {
        "schedule_id": schedule_id,
        "runs": [
            {
                "id": r.id,
                "test_definition_id": r.test_definition_id,
                "status": r.status,
                "total_tests": r.total_tests,
                "passed": r.passed,
                "failed": r.failed,
                "total_duration_ms": r.total_duration_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "start_time": r.start_time.isoformat() if r.start_time else None,
                "end_time": r.end_time.isoformat() if hasattr(r, "end_time") and r.end_time else None,
            }
            for r in runs
        ],
    }


# --- Sync / Reconciliation ---


@router.post("/sync")
async def sync_schedules(
    current_user: User = Depends(RequirePermission("manage:schedules")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Schedule))
    schedules = result.scalars().all()
    schedule_dicts = [
        {
            "id": s.id,
            "is_active": s.is_active,
            "cron_expression": s.cron_expression,
            "test_definition_id": s.test_definition_id,
            "test_definition_ids": s.test_definition_ids or [],
            "test_suite_id": s.test_suite_id,
        }
        for s in schedules
    ]
    reconciliation = await temporal_schedule_service.reconcile(schedule_dicts)
    return {"status": "completed", "reconciliation": reconciliation}

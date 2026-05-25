"""
Schedules API Endpoints

Schedule management for test execution using Temporal workflows.
This replaces the Celery Beat schedule synchronization with Temporal-based scheduling.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models.schedule import Schedule
from app.models.user import User
from app.temporal import get_temporal_client
from app.workflows.schedules import ScheduleSyncWorkflow

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/sync")
async def sync_schedules(
    current_user: User = Depends(RequirePermission("manage:schedules")),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger schedule synchronization with Temporal.

    This endpoint initiates the ScheduleSyncWorkflow to:
    - Fetch all active schedules from database
    - Calculate next run times for each schedule
    - Ensure Temporal schedules are properly configured

    Returns:
        Sync results with counts of processed schedules
    """
    try:
        logger.info("Manual schedule sync triggered by user %s", current_user.id)

        # Get Temporal client
        client = await get_temporal_client()

        # Start ScheduleSyncWorkflow
        result = await client.start_workflow(
            ScheduleSyncWorkflow.run,
            id=f"schedule-sync-manual-{datetime.utcnow().timestamp()}",
            task_queue="temporal-worker-task-queue",
        )

        logger.info("ScheduleSyncWorkflow started: %s", result)

        return {
            "status": "started",
            "workflow_id": result.id,
            "run_id": result.run_id,
            "message": "Schedule synchronization workflow started",
        }

    except Exception as e:
        logger.error("Failed to start schedule sync workflow: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync schedules: {str(e)}",
        )


@router.get("/active")
async def list_active_schedules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all active schedules from the database.

    Returns:
        List of active schedules with their configuration and next run times
    """
    try:
        result = await db.execute(
            select(Schedule).where(Schedule.is_active == True)
        )
        schedules = result.scalars().all()

        schedule_list = []
        for schedule in schedules:
            schedule_list.append({
                "id": schedule.id,
                "name": schedule.name,
                "schedule_type": schedule.schedule_type,
                "cron_expression": schedule.cron_expression,
                "timezone": schedule.timezone,
                "is_active": schedule.is_active,
                "last_run_time": schedule.last_run_time.isoformat() if schedule.last_run_time else None,
                "next_run_time": schedule.next_run_time.isoformat() if schedule.next_run_time else None,
                "test_definition_id": schedule.test_definition_id,
                "test_suite_id": schedule.test_suite_id,
                "test_definition_ids": schedule.test_definition_ids,
                "max_retries": schedule.max_retries,
                "retry_interval_seconds": schedule.retry_interval_seconds,
                "timeout_seconds": schedule.timeout_seconds,
                "environment_overrides": schedule.environment_overrides,
                "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
                "created_by": schedule.created_by,
            })

        return {
            "total": len(schedule_list),
            "schedules": schedule_list,
        }

    except Exception as e:
        logger.error("Failed to fetch active schedules: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch schedules: {str(e)}",
        )


@router.post("/trigger/{schedule_id}")
async def trigger_schedule_execution(
    schedule_id: int,
    current_user: User = Depends(RequirePermission("execute:schedule")),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger execution of a specific schedule.

    This endpoint initiates the ScheduleExecutionWorkflow for the specified schedule,
    bypassing the normal cron scheduling. Useful for testing or immediate execution.

    Args:
        schedule_id: Schedule ID to execute

    Returns:
        Execution results with run IDs and status
    """
    try:
        # Load schedule from database
        result = await db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found",
            )

        if not schedule.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Schedule {schedule_id} is not active",
            )

        logger.info("Manual execution triggered for schedule %s by user %s", schedule_id, current_user.id)

        # Get Temporal client
        client = await get_temporal_client()

        # Resolve test definition ID based on schedule type
        if schedule.schedule_type == "suite" and schedule.test_suite_id:
            # For suite schedules, use the suite's test definitions
            test_definition_id = str(schedule.test_suite_id)
        elif schedule.test_definition_id:
            # For single test schedules
            test_definition_id = str(schedule.test_definition_id)
        elif schedule.test_definition_ids and len(schedule.test_definition_ids) > 0:
            # For schedules with multiple test definitions, use the first one
            test_definition_id = str(schedule.test_definition_ids[0])
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Schedule {schedule_id} has no valid test definitions",
            )

        # Import ScheduleExecutionWorkflow
        from app.workflows.schedules import ScheduleExecutionWorkflow

        # Start ScheduleExecutionWorkflow
        workflow_result = await client.start_workflow(
            ScheduleExecutionWorkflow.run,
            args=[schedule_id, test_definition_id],
            id=f"schedule-execution-{schedule_id}-{datetime.utcnow().timestamp()}",
            task_queue="temporal-worker-task-queue",
        )

        logger.info("ScheduleExecutionWorkflow started: %s", workflow_result)

        return {
            "status": "started",
            "schedule_id": schedule_id,
            "workflow_id": workflow_result.id,
            "run_id": workflow_result.run_id,
            "message": f"Schedule {schedule_id} execution workflow started",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to trigger schedule execution: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger schedule execution: {str(e)}",
        )


@router.get("/status/{schedule_id}")
async def get_schedule_status(
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the current status of a specific schedule.

    Returns:
        Schedule details including execution history and next run time
    """
    try:
        result = await db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found",
            )

        return {
            "id": schedule.id,
            "name": schedule.name,
            "schedule_type": schedule.schedule_type,
            "cron_expression": schedule.cron_expression,
            "timezone": schedule.timezone,
            "is_active": schedule.is_active,
            "last_run_time": schedule.last_run_time.isoformat() if schedule.last_run_time else None,
            "next_run_time": schedule.next_run_time.isoformat() if schedule.next_run_time else None,
            "test_definition_id": schedule.test_definition_id,
            "test_suite_id": schedule.test_suite_id,
            "test_definition_ids": schedule.test_definition_ids,
            "max_retries": schedule.max_retries,
            "retry_interval_seconds": schedule.retry_interval_seconds,
            "timeout_seconds": schedule.timeout_seconds,
            "environment_overrides": schedule.environment_overrides,
            "created_at": schedule.created_at.isoformat() if schedule.created_at else None,
            "created_by": schedule.created_by,
            "updated_at": schedule.updated_at.isoformat() if schedule.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get schedule status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schedule status: {str(e)}",
        )


@router.put("/toggle/{schedule_id}")
async def toggle_schedule_active(
    schedule_id: int,
    is_active: bool,
    current_user: User = Depends(RequirePermission("manage:schedules")),
    db: AsyncSession = Depends(get_db),
):
    """
    Toggle a schedule's active status.

    This enables or disables a schedule without deleting it.
    When disabled, the schedule will not be executed by Temporal.

    Args:
        schedule_id: Schedule ID to toggle
        is_active: New active status (True/False)

    Returns:
        Updated schedule details
    """
    try:
        result = await db.execute(
            select(Schedule).where(Schedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule with ID {schedule_id} not found",
            )

        # Update schedule status
        schedule.is_active = is_active
        await db.commit()
        await db.refresh(schedule)

        logger.info(
            "Schedule %s status changed to %s by user %s",
            schedule_id, is_active, current_user.id
        )

        return {
            "id": schedule.id,
            "name": schedule.name,
            "is_active": schedule.is_active,
            "message": f"Schedule {schedule_id} {'enabled' if is_active else 'disabled'}",
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to toggle schedule status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle schedule status: {str(e)}",
        )

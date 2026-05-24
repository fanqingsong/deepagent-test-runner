"""
Schedules API Endpoints

Test execution schedule management.
"""

from typing import List, Optional
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.celery_app import celery_app
from app.models.schedule import Schedule
from app.models.test_run import TestRun
from app.schemas.schedules import (
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
    ScheduleToggle,
    SchedulePresetsResponse,
    SchedulePreset,
    ScheduleTriggerResponse
)
from app.services import get_schedule_manager, get_execution_service
from app.core.security import verify_token

router = APIRouter()

# Schedule presets
SCHEDULE_PRESETS = [
    SchedulePreset(
        type="hourly",
        name="Hourly",
        cron="0 * * * *",
        description="Run every hour at minute 0"
    ),
    SchedulePreset(
        type="daily_midnight",
        name="Daily (Midnight)",
        cron="0 0 * * *",
        description="Run daily at midnight"
    ),
    SchedulePreset(
        type="daily_noon",
        name="Daily (Noon)",
        cron="0 12 * * *",
        description="Run daily at noon (12:00)"
    ),
    SchedulePreset(
        type="weekly_monday",
        name="Weekly (Monday)",
        cron="0 0 * * 1",
        description="Run every Monday at midnight"
    ),
    SchedulePreset(
        type="weekly_friday",
        name="Weekly (Friday)",
        cron="0 0 * * 5",
        description="Run every Friday at midnight"
    ),
    SchedulePreset(
        type="monthly_1st",
        name="Monthly (1st)",
        cron="0 0 1 * *",
        description="Run on the 1st of every month at midnight"
    ),
    SchedulePreset(
        type="business_hours",
        name="Business Hours",
        cron="0 9-17 * * 1-5",
        description="Run every hour from 9am to 5pm, Monday to Friday"
    ),
]


@router.post("/", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new test execution schedule.

    - **name**: Schedule name
    - **schedule_type**: Type of schedule (single/suite/tag_filter)
    - **test_definition_id**: Test definition ID (for single type)
    - **test_suite_id**: Test suite ID (for suite type)
    - **tag_filter**: Tag filter (for tag_filter type)
    - **preset_type**: Optional preset schedule type
    - **cron_expression**: Cron expression for scheduling
    - **timezone**: Timezone for schedule (default: UTC)
    - **environment_overrides**: Environment variable overrides
    - **is_active**: Whether the schedule is active
    - **allow_concurrent**: Allow concurrent executions
    - **max_retries**: Maximum number of retries (0-10)
    - **retry_interval_seconds**: Seconds between retries (10-3600)
    """
    # Check if schedule with same name exists
    existing = await db.execute(
        select(Schedule).where(Schedule.name == schedule_data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Schedule with name '{schedule_data.name}' already exists"
        )

    # Validate cron expression
    try:
        get_schedule_manager().validate_cron(schedule_data.cron_expression)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Calculate next run time
    try:
        next_run_time = get_schedule_manager().parse_cron_expression(
            schedule_data.cron_expression,
            schedule_data.timezone
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression or timezone: {str(e)}"
        )

    # Get user ID from token
    user_id = int(current_user["sub"]) if current_user.get("provider") == "local" else None

    # Convert test_definition_id to test_definition_ids array
    test_definition_ids = []
    if schedule_data.test_definition_id:
        test_definition_ids = [schedule_data.test_definition_id]
    elif schedule_data.test_definition_ids:
        test_definition_ids = schedule_data.test_definition_ids

    # Create schedule
    schedule = Schedule(
        name=schedule_data.name,
        schedule_type=schedule_data.schedule_type,
        test_definition_ids=test_definition_ids,
        test_definition_id=schedule_data.test_definition_id,
        test_suite_id=schedule_data.test_suite_id,
        tag_filter=schedule_data.tag_filter,
        preset_type=schedule_data.preset_type,
        cron_expression=schedule_data.cron_expression,
        timezone=schedule_data.timezone,
        environment_overrides=schedule_data.environment_overrides,
        is_active=schedule_data.is_active,
        allow_concurrent=schedule_data.allow_concurrent,
        max_retries=schedule_data.max_retries,
        retry_interval_seconds=schedule_data.retry_interval_seconds,
        next_run_time=next_run_time,
        created_by=str(user_id) if user_id else "system"
    )

    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    # Sync to Celery Beat
    if schedule.is_active:
        try:
            await get_schedule_manager().sync_schedules(db)
        except Exception as e:
            # Log but don't fail the request
            pass

    return schedule


@router.get("/", response_model=List[ScheduleResponse])
async def list_schedules(
    skip: int = Query(0, ge=0, description="Number of schedules to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of schedules to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    schedule_type: Optional[str] = Query(None, description="Filter by schedule type"),
    current_user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """
    List all schedules with optional filters.

    Admin users see all schedules, regular users only see their own.

    - **skip**: Number of schedules to skip (for pagination)
    - **limit**: Number of schedules to return (max 1000)
    - **is_active**: Filter by active status
    - **schedule_type**: Filter by schedule type (single/suite/tag_filter)
    """
    query = select(Schedule)

    # Apply role-based filtering
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local":
        # Regular local users only see their own schedules
        query = query.where(Schedule.created_by == str(current_user["sub"]))

    # Apply filters
    if is_active is not None:
        query = query.where(Schedule.is_active == is_active)
    if schedule_type is not None:
        query = query.where(Schedule.schedule_type == schedule_type)

    # Order by created_at descending
    query = query.order_by(Schedule.created_at.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    schedules = result.scalars().all()

    return schedules


@router.get("/count", status_code=status.HTTP_200_OK)
async def count_schedules(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    schedule_type: Optional[str] = Query(None, description="Filter by schedule type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get total count of schedules matching filters.

    - **is_active**: Filter by active status
    - **schedule_type**: Filter by schedule type
    """
    query = select(func.count(Schedule.id))

    if is_active is not None:
        query = query.where(Schedule.is_active == is_active)
    if schedule_type is not None:
        query = query.where(Schedule.schedule_type == schedule_type)

    result = await db.execute(query)
    count = result.scalar()

    return {"count": count}


@router.get("/presets", response_model=SchedulePresetsResponse)
async def list_schedule_presets():
    """
    Get available schedule presets.

    Returns a list of predefined schedule options with their cron expressions.
    """
    return SchedulePresetsResponse(presets=SCHEDULE_PRESETS)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    current_user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific schedule by ID.

    - **schedule_id**: Schedule ID
    """
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    # Check permission: regular users can only view their own schedules
    is_admin = current_user.get("is_admin", False)
    if not is_admin and current_user.get("provider") == "local":
        if schedule.created_by != str(current_user["sub"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this schedule"
            )

    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a schedule.

    - **schedule_id**: Schedule ID
    - **schedule_data**: Schedule fields to update
    """
    # Get existing schedule
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    # Check for name conflict
    if schedule_data.name is not None and schedule_data.name != schedule.name:
        existing = await db.execute(
            select(Schedule).where(
                Schedule.name == schedule_data.name,
                Schedule.id != schedule_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Schedule with name '{schedule_data.name}' already exists"
            )

    # Update fields
    update_data = schedule_data.model_dump(exclude_unset=True)

    # Handle test_definition_ids conversion
    if "test_definition_id" in update_data or "test_definition_ids" in update_data:
        test_definition_ids = []
        if update_data.get("test_definition_id"):
            test_definition_ids = [update_data["test_definition_id"]]
        elif update_data.get("test_definition_ids"):
            test_definition_ids = update_data["test_definition_ids"]
        update_data["test_definition_ids"] = test_definition_ids

    # Validate cron expression if provided
    if "cron_expression" in update_data:
        try:
            get_schedule_manager().validate_cron(update_data["cron_expression"])
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Recalculate next run time
        timezone_val = update_data.get("timezone", schedule.timezone)
        try:
            update_data["next_run_time"] = get_schedule_manager().parse_cron_expression(
                update_data["cron_expression"],
                timezone_val
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression or timezone: {str(e)}"
            )

    # Validate schedule_type and target configuration
    if "schedule_type" in update_data:
        schedule_type = update_data["schedule_type"]
        if schedule_type == "single" and update_data.get("test_definition_id") is None:
            if schedule.test_definition_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="schedule_type=single requires test_definition_id"
                )
        elif schedule_type == "suite" and update_data.get("test_suite_id") is None:
            if schedule.test_suite_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="schedule_type=suite requires test_suite_id"
                )
        elif schedule_type == "tag_filter" and update_data.get("tag_filter") is None:
            if schedule.tag_filter is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="schedule_type=tag_filter requires tag_filter"
                )

    # Apply updates
    for field, value in update_data.items():
        setattr(schedule, field, value)

    schedule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(schedule)

    # Sync to Celery Beat
    try:
        await get_schedule_manager().sync_schedules(db)
    except Exception as e:
        # Log but don't fail the request
        pass

    return schedule


@router.patch("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: int,
    toggle_data: ScheduleToggle,
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle schedule active status.

    - **schedule_id**: Schedule ID
    - **is_active**: New active status
    """
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    schedule.is_active = toggle_data.is_active
    schedule.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(schedule)

    # Sync to Celery Beat
    try:
        await get_schedule_manager().sync_schedules(db)
    except Exception as e:
        # Log but don't fail the request
        pass

    return schedule


@router.post("/{schedule_id}/trigger", response_model=ScheduleTriggerResponse)
async def trigger_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger a schedule execution.

    - **schedule_id**: Schedule ID to trigger
    """
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    # Check execution limits
    can_execute = await get_execution_service().check_execution_limit(schedule, db)
    if not can_execute:
        # Make this endpoint idempotent for UX: if there's already a pending/running run,
        # return that run_id instead of failing with 429.
        existing_stmt = (
            select(TestRun)
            .where(
                TestRun.schedule_id == schedule.id,
                TestRun.status.in_(["pending", "running"]),
            )
            .order_by(TestRun.created_at.desc())
            .limit(1)
        )
        existing_result = await db.execute(existing_stmt)
        existing_run = existing_result.scalar_one_or_none()
        if existing_run:
            return ScheduleTriggerResponse(
                run_id=existing_run.run_id,
                status=existing_run.status,
            )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Execution limit reached or another execution is in progress"
        )

    # Resolve target test definitions
    try:
        test_definition_ids = await get_execution_service().resolve_target_tests(schedule, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to resolve target tests: {str(e)}"
        )

    if not test_definition_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No test definitions found for this schedule"
        )

    # Generate run ID
    run_id = str(uuid.uuid4())

    # Build environment
    environment = get_execution_service().build_environment(schedule)

    # Create test run record
    await get_execution_service().create_test_run(
        run_id=run_id,
        test_definition_ids=test_definition_ids,
        environment=environment,
        db=db,
        schedule_id=schedule.id
    )

    # Trigger execution for each test
    for test_def_id in test_definition_ids:
        celery_app.send_task(
            "app.tasks.test_execution.execute_test",
            args=[test_def_id, run_id, environment]
        )

    return ScheduleTriggerResponse(
        run_id=run_id,
        status="pending"
    )


@router.get("/{schedule_id}/history", status_code=status.HTTP_200_OK)
async def get_schedule_history(
    schedule_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get execution history for a schedule.

    - **schedule_id**: Schedule ID
    - **skip**: Number of records to skip
    - **limit**: Number of records to return (max 500)
    """
    # Verify schedule exists
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    # Get execution history
    query = select(TestRun).where(TestRun.schedule_id == schedule_id)
    query = query.order_by(TestRun.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    test_runs = result.scalars().all()

    return {
        "schedule_id": schedule_id,
        "total_runs": len(test_runs),
        "history": [
            {
                "run_id": run.run_id,
                "status": run.status,
                "total_tests": run.total_tests,
                "passed": run.passed,
                "failed": run.failed,
                "skipped": run.skipped,
                "start_time": run.start_time,
                "end_time": run.end_time,
                "total_duration": run.total_duration,
                "retry_count": run.retry_count,
                "created_at": run.created_at
            }
            for run in test_runs
        ]
    }


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a schedule.

    - **schedule_id**: Schedule ID
    """
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule with ID {schedule_id} not found"
        )

    # Delete associated test runs
    await db.execute(
        delete(TestRun).where(TestRun.schedule_id == schedule_id)
    )

    # Delete schedule
    await db.execute(
        delete(Schedule).where(Schedule.id == schedule_id)
    )

    await db.commit()

    # Sync to Celery Beat
    try:
        await get_schedule_manager().sync_schedules(db)
    except Exception as e:
        # Log but don't fail the request
        pass

    return None

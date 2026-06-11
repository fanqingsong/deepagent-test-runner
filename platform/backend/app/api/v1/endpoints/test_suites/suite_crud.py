"""
Test Suite CRUD Endpoints

Create, read, update, delete, and resolve test suites.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models.schedule import Schedule
from app.models.test_suite import TestSuite
from app.models.user import User
from app.schemas.test_suites import TestSuiteCreate, TestSuiteResponse, TestSuiteUpdate
from app.services.suite_service import SuiteService
from app.api.v1.endpoints.test_suites.suite_schedule_helper import sync_suite_schedule

router = APIRouter()


@router.post("/", response_model=TestSuiteResponse, status_code=status.HTTP_201_CREATED)
async def create_test_suite(
    suite_data: TestSuiteCreate,
    current_user: User = Depends(RequirePermission("create:suite")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new test suite with execution configuration."""
    # Auto-populate test_definition_ids from suite_entries if not provided
    if not suite_data.test_definition_ids and suite_data.suite_entries:
        suite_data.test_definition_ids = [
            e.test_definition_id for e in suite_data.suite_entries
        ]

    suite = TestSuite(
        name=suite_data.name,
        description=suite_data.description,
        test_definition_ids=suite_data.test_definition_ids,
        tags=suite_data.tags,
        execution_mode=suite_data.execution_mode,
        max_concurrency=suite_data.max_concurrency,
        fail_strategy=suite_data.fail_strategy,
        retry_config=suite_data.retry_config,
        environment_vars=suite_data.environment_vars,
        suite_entries=[e.model_dump() for e in suite_data.suite_entries],
        is_dynamic=suite_data.is_dynamic,
        dynamic_tag_rule=suite_data.dynamic_tag_rule,
        setup_test_id=suite_data.setup_test_id,
        teardown_test_id=suite_data.teardown_test_id,
        schedule_enabled=suite_data.schedule_enabled,
        cron_expression=suite_data.cron_expression,
        timezone=suite_data.timezone,
        schedule_allow_concurrent=suite_data.schedule_allow_concurrent,
        schedule_max_retries=suite_data.schedule_max_retries,
        schedule_retry_interval=suite_data.schedule_retry_interval,
        created_by=str(current_user.id),
    )

    db.add(suite)
    await db.flush()
    await sync_suite_schedule(db, suite)
    await db.commit()
    await db.refresh(suite)

    return suite


@router.get("/", response_model=List[TestSuiteResponse])
async def list_test_suites(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's test suites, newest first."""
    limit = min(limit, 1000)

    result = await db.execute(
        select(TestSuite)
        .where(TestSuite.created_by == str(current_user.id))
        .order_by(TestSuite.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/marketplace", response_model=List[TestSuiteResponse])
async def list_published_suites(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch approved test suites for marketplace display."""
    limit = min(limit, 1000)

    query = select(TestSuite).where(TestSuite.review_status == "approved")

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (TestSuite.name.ilike(search_pattern)) |
            (TestSuite.description.ilike(search_pattern))
        )

    query = query.order_by(TestSuite.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{suite_id}", response_model=TestSuiteResponse)
async def get_test_suite(
    suite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific test suite by ID."""
    result = await db.execute(
        select(TestSuite).where(TestSuite.id == suite_id)
    )
    suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with ID {suite_id} not found",
        )

    return suite


@router.put("/{suite_id}", response_model=TestSuiteResponse)
async def update_test_suite(
    suite_id: int,
    suite_data: TestSuiteUpdate,
    current_user: User = Depends(RequirePermission("update:suite")),
    db: AsyncSession = Depends(get_db),
):
    """Update a test suite. Only updates fields that are provided."""
    result = await db.execute(
        select(TestSuite).where(TestSuite.id == suite_id)
    )
    suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with ID {suite_id} not found",
        )

    update_fields = [
        "name", "description", "test_definition_ids", "tags",
        "execution_mode", "max_concurrency", "fail_strategy",
        "retry_config", "environment_vars",
        "is_dynamic", "dynamic_tag_rule",
        "setup_test_id", "teardown_test_id",
        "schedule_enabled", "cron_expression", "timezone",
        "schedule_allow_concurrent", "schedule_max_retries",
        "schedule_retry_interval",
    ]

    content_changed = False
    for field in update_fields:
        value = getattr(suite_data, field, None)
        if value is not None:
            if getattr(suite, field) != value:
                content_changed = True
            setattr(suite, field, value)

    if suite_data.suite_entries is not None:
        suite.suite_entries = [e.model_dump() for e in suite_data.suite_entries]
        if not suite_data.test_definition_ids:
            suite.test_definition_ids = [
                e.test_definition_id for e in suite_data.suite_entries
            ]
        content_changed = True

    # Reset review status if content changed on an approved suite
    if content_changed and suite.review_status == "approved":
        suite.review_status = "pending_review"
        suite.reviewed_by = None
        suite.reviewed_at = None
        suite.rejection_reason = None

    await sync_suite_schedule(db, suite)
    await db.commit()
    await db.refresh(suite)

    return suite


@router.delete("/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_suite(
    suite_id: int,
    current_user: User = Depends(RequirePermission("delete:suite")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a test suite."""
    result = await db.execute(
        select(TestSuite).where(TestSuite.id == suite_id)
    )
    suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with ID {suite_id} not found",
        )

    # Delete linked schedule if exists
    if suite.schedule_id:
        sched_result = await db.execute(
            select(Schedule).where(Schedule.id == suite.schedule_id)
        )
        linked_schedule = sched_result.scalar_one_or_none()
        if linked_schedule:
            await db.delete(linked_schedule)

    await db.delete(suite)
    await db.commit()

    return None


@router.post("/{suite_id}/copy", response_model=TestSuiteResponse)
async def copy_test_suite(
    suite_id: int,
    current_user: User = Depends(RequirePermission("create:suite")),
    db: AsyncSession = Depends(get_db),
):
    """Copy an existing test suite to create a new one in the user's workspace."""
    result = await db.execute(
        select(TestSuite).where(TestSuite.id == suite_id)
    )
    suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with ID {suite_id} not found",
        )

    # Create a copy with updated metadata
    new_suite = TestSuite(
        name=f"{suite.name} (Copy)",
        description=suite.description,
        test_definition_ids=suite.test_definition_ids,
        tags=suite.tags,
        execution_mode=suite.execution_mode,
        max_concurrency=suite.max_concurrency,
        fail_strategy=suite.fail_strategy,
        retry_config=suite.retry_config,
        environment_vars=suite.environment_vars,
        suite_entries=suite.suite_entries,
        is_dynamic=suite.is_dynamic,
        dynamic_tag_rule=suite.dynamic_tag_rule,
        setup_test_id=suite.setup_test_id,
        teardown_test_id=suite.teardown_test_id,
        schedule_enabled=False,  # Disable schedule for copied suite
        cron_expression=None,
        timezone=None,
        schedule_allow_concurrent=None,
        schedule_max_retries=None,
        schedule_retry_interval=None,
        review_status="draft",  # Reset to draft
        reviewed_by=None,
        reviewed_at=None,
        rejection_reason=None,
        created_by=str(current_user.id),
    )

    db.add(new_suite)
    await db.commit()
    await db.refresh(new_suite)

    return new_suite


@router.get("/{suite_id}/resolve", response_model=List[dict])
async def resolve_dynamic_suite(
    suite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview resolved entries for a dynamic or static suite."""
    result = await db.execute(
        select(TestSuite).where(TestSuite.id == suite_id)
    )
    suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with ID {suite_id} not found",
        )

    svc = SuiteService(db)
    entries = svc.resolve_suite_entries(suite)
    if not entries and suite.is_dynamic:
        entries = await svc.resolve_dynamic_suite(suite)

    return entries

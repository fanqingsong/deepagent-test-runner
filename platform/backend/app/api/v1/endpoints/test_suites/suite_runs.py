"""
Test Suite Execution Endpoints

Trigger, list, get details, and cancel suite runs.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models.suite_run import SuiteRun
from app.models.test_suite import TestSuite
from app.models.user import User
from app.schemas.suite_runs import (
    SuiteRunListResponse,
    SuiteRunResponse,
    SuiteRunTriggerRequest,
    SuiteRunTriggerResponse,
)
from app.services.suite_service import SuiteService

router = APIRouter()


@router.post("/{suite_id}/run", response_model=SuiteRunTriggerResponse)
async def trigger_suite_run(
    suite_id: int,
    body: Optional[SuiteRunTriggerRequest] = None,
    current_user: User = Depends(RequirePermission("execute:suite")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a suite execution. Only approved suites can be executed."""
    result = await db.execute(
        select(TestSuite).where(TestSuite.id == suite_id)
    )
    suite = result.scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail=f"Test suite {suite_id} not found")
    if suite.review_status != "approved":
        raise HTTPException(
            status_code=403,
            detail="Suite must be approved before execution. Submit it for review first.",
        )

    svc = SuiteService(db)

    body = body or SuiteRunTriggerRequest()
    suite_run = await svc.create_suite_run(
        suite_id=suite_id,
        triggered_by="manual",
        environment_overrides=body.environment,
    )

    # Dispatch via Temporal
    await svc.execute_suite(suite_run.id)

    return SuiteRunTriggerResponse(run_id=suite_run.run_id, status="pending")


@router.get("/{suite_id}/runs", response_model=List[SuiteRunListResponse])
async def list_suite_runs(
    suite_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List runs for a test suite, newest first."""
    svc = SuiteService(db)
    runs = await svc.list_suite_runs(suite_id, skip=skip, limit=limit)
    return runs


@router.get("/runs/{run_id}", response_model=SuiteRunResponse)
async def get_suite_run_detail(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get suite run detail with all entries."""
    svc = SuiteService(db)
    suite_run = await svc.get_suite_run_with_entries(run_id)

    if not suite_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suite run {run_id} not found",
        )

    return suite_run


@router.post("/runs/{run_id}/cancel", response_model=SuiteRunResponse)
async def cancel_suite_run(
    run_id: str,
    current_user: User = Depends(RequirePermission("execute:suite")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running suite run."""
    svc = SuiteService(db)

    result = await db.execute(
        select(SuiteRun).where(SuiteRun.run_id == run_id)
    )
    suite_run = result.scalar_one_or_none()

    if not suite_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suite run {run_id} not found",
        )

    await svc.cancel_suite_run(suite_run.id)

    # Reload with entries for response
    full_run = await svc.get_suite_run_with_entries(run_id)
    return full_run

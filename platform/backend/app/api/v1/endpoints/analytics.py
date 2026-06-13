"""
Analytics API Endpoints
Provides data analysis and dashboard statistics
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService
from app.core.security import get_current_user
from app.models.user import User
from app.core.container import Container, Provide, inject

router = APIRouter()


# Provider function for AnalyticsService with database session
@inject
def get_analytics_service_with_db(
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
) -> AnalyticsService:
    """
    Get AnalyticsService with database session.

    This ensures the singleton service gets the request-scoped database session.
    """
    # The service is a singleton from the container, but we pass db to each method call
    return analytics


@router.get("/dashboard")
@inject
async def get_dashboard_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard summary statistics

    Returns aggregated test statistics including:
    - Total runs, passed, failed, skipped counts
    - Average duration
    - Success/failure rates
    """
    is_admin = current_user.is_admin or current_user.has_role("admin")
    user_id = None if is_admin else current_user.id

    summary = await analytics.get_dashboard_summary(
        days=days,
        user_id=user_id,
        is_admin=is_admin,
        db=db
    )

    by_day = await analytics.get_test_runs_by_day(
        days=days,
        user_id=user_id,
        is_admin=is_admin,
        db=db
    )

    total_definitions = await analytics.get_total_test_definitions(
        user_id=user_id,
        is_admin=is_admin,
        db=db
    )

    return {
        "summary": summary,
        "byDay": by_day,
        "totalDefinitions": total_definitions,
        "days": days
    }


@router.get("/test-runs")
@inject
async def get_test_runs(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of runs to return"),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent test runs with test definition names

    Returns test runs ordered by creation date (newest first).
    Non-admin users only see their own test runs.
    """
    is_admin = current_user.is_admin or current_user.has_role("admin")
    user_id = None if is_admin else current_user.id

    runs = await analytics.get_recent_test_runs(
        limit=limit,
        user_id=user_id,
        is_admin=is_admin,
        db=db
    )

    return runs


@router.get("/test-runs/{run_id}")
@inject
async def get_test_run_details(
    run_id: str,
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed test cases for a specific test run

    Returns all test cases with their individual results.
    """
    test_cases = await analytics.get_test_cases_for_run(
        run_id=run_id,
        db=db
    )

    return test_cases


@router.get("/suite-dashboard")
@inject
async def get_suite_dashboard(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
):
    """Get suite-centric dashboard data."""
    is_admin = current_user.is_admin or current_user.has_role("admin")
    user_id = None if is_admin else current_user.id

    summary = await analytics.get_suite_dashboard_summary(
        days=days, user_id=user_id, is_admin=is_admin, db=db
    )
    suites = await analytics.get_suites_with_latest_run(
        user_id=user_id, is_admin=is_admin, db=db
    )

    return {"summary": summary, "suites": suites}


@router.get("/suite-runs/timeline/{suite_id}")
@inject
async def get_suite_run_timeline(
    suite_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
):
    """Get run timeline for a specific suite."""
    timeline = await analytics.get_suite_run_timeline(
        suite_id=suite_id, limit=limit, db=db
    )
    return timeline


@router.get("/suite-runs/{run_id}/entries")
@inject
async def get_suite_run_entries(
    run_id: str,
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
):
    """Get suite run entries with test case details."""
    detail = await analytics.get_suite_run_with_test_cases(
        run_id=run_id,
        db=db
    )
    if not detail:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Suite run {run_id} not found")
    return detail


@router.get("/slowest-tests")
@inject
async def get_slowest_tests(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of tests to return"),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
):
    """
    Get slowest tests by average duration

    Returns tests with the highest average execution time.
    Only includes passed test runs for accurate averages.
    """
    tests = await analytics.get_slowest_tests(
        limit=limit,
        db=db
    )

    return tests


@router.get("/flaky-tests")
@inject
async def get_flaky_tests(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
):
    """
    Get flaky tests (tests with both passes and failures)

    Returns tests with high failure rates, indicating instability.
    Only includes tests with at least 2 runs and at least 1 failure.
    """
    tests = await analytics.get_flaky_tests(
        days=days,
        db=db
    )

    return tests


@router.get("/failure-patterns")
@inject
async def get_failure_patterns(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of patterns to return"),
    current_user: User = Depends(get_current_user),
    analytics: AnalyticsService = Depends(Provide[Container.analytics_service]),
    db: AsyncSession = Depends(get_db)
):
    """
    Get common failure patterns

    Returns the most frequent error messages to help identify
    recurring issues and failure patterns.
    """
    patterns = await analytics.get_failure_patterns(
        limit=limit,
        db=db
    )

    return patterns

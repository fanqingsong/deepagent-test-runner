"""
Analytics API Endpoints
Provides data analysis and dashboard statistics
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService
from app.core.security import verify_token

router = APIRouter()
analytics_service = AnalyticsService()


@router.get("/dashboard")
async def get_dashboard_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Get dashboard summary statistics

    Returns aggregated test statistics including:
    - Total runs, passed, failed, skipped counts
    - Average duration
    - Success/failure rates
    """
    is_admin = current_user.get("is_admin", False) or (current_user.get("roles") and 'admin' in current_user.get("roles", []))
    user_id = int(current_user.get("sub")) if not is_admin and current_user.get("provider") == "local" else None

    summary = await analytics_service.get_dashboard_summary(
        db=db,
        days=days,
        user_id=user_id,
        is_admin=is_admin
    )

    by_day = await analytics_service.get_test_runs_by_day(
        db=db,
        days=days,
        user_id=user_id,
        is_admin=is_admin
    )

    total_definitions = await analytics_service.get_total_test_definitions(
        db=db,
        user_id=user_id,
        is_admin=is_admin
    )

    return {
        "summary": summary,
        "byDay": by_day,
        "totalDefinitions": total_definitions,
        "days": days
    }


@router.get("/test-runs")
async def get_test_runs(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of runs to return"),
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent test runs with test definition names

    Returns test runs ordered by creation date (newest first).
    Non-admin users only see their own test runs.
    """
    is_admin = current_user.get("is_admin", False) or (current_user.get("roles") and 'admin' in current_user.get("roles", []))
    user_id = int(current_user.get("sub")) if not is_admin and current_user.get("provider") == "local" else None

    runs = await analytics_service.get_recent_test_runs(
        db=db,
        limit=limit,
        user_id=user_id,
        is_admin=is_admin
    )

    return runs


@router.get("/test-runs/{run_id}")
async def get_test_run_details(
    run_id: str,
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed test cases for a specific test run

    Returns all test cases with their individual results.
    """
    test_cases = await analytics_service.get_test_cases_for_run(
        db=db,
        run_id=run_id
    )

    return test_cases


@router.get("/slowest-tests")
async def get_slowest_tests(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of tests to return"),
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Get slowest tests by average duration

    Returns tests with the highest average execution time.
    Only includes passed test runs for accurate averages.
    """
    tests = await analytics_service.get_slowest_tests(
        db=db,
        limit=limit
    )

    return tests


@router.get("/flaky-tests")
async def get_flaky_tests(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Get flaky tests (tests with both passes and failures)

    Returns tests with high failure rates, indicating instability.
    Only includes tests with at least 2 runs and at least 1 failure.
    """
    tests = await analytics_service.get_flaky_tests(
        db=db,
        days=days
    )

    return tests


@router.get("/failure-patterns")
async def get_failure_patterns(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of patterns to return"),
    current_user: dict = Depends(lambda: {}),  # Make public for development
    db: AsyncSession = Depends(get_db)
):
    """
    Get common failure patterns

    Returns the most frequent error messages to help identify
    recurring issues and failure patterns.
    """
    patterns = await analytics_service.get_failure_patterns(
        db=db,
        limit=limit
    )

    return patterns

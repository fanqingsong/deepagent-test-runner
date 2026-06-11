"""
Pending Review Endpoints

Lists pending reviews for tests, suites, and versions.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models.test_definition import TestDefinition
from app.models.test_suite import TestSuite
from app.models.test_suite_version import TestSuiteVersion
from app.models.test_version import TestVersion
from app.models.user import User
from app.schemas.review import PendingReviewListResponse, ReviewItemResponse

router = APIRouter()


@router.get("/tests", response_model=list[ReviewItemResponse])
async def list_pending_tests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    """List all test versions pending review."""
    stmt = (
        select(TestVersion, TestDefinition)
        .join(TestDefinition, TestVersion.test_definition_id == TestDefinition.id)
        .where(TestVersion.review_status == "pending_review")
        .order_by(TestVersion.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        ReviewItemResponse(
            id=v.id,
            type="test",
            name=(v.snapshot or {}).get("name", td.name),
            description=(v.snapshot or {}).get("description", td.description),
            review_status=v.review_status,
            created_by=v.created_by,
            created_at=v.created_at,
            reviewed_by=str(v.reviewed_by) if v.reviewed_by else None,
            reviewed_at=v.reviewed_at,
            rejection_reason=v.rejection_reason,
            version_id=v.id,
            version_number=v.version,
        )
        for v, td in rows
    ]


@router.get("/suites", response_model=list[ReviewItemResponse])
async def list_pending_suites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    """List all test suites pending review."""
    stmt = (
        select(TestSuite)
        .where(TestSuite.review_status == "pending_review")
        .order_by(TestSuite.updated_at.desc())
    )
    result = await db.execute(stmt)
    suites = result.scalars().all()
    return [
        ReviewItemResponse(
            id=s.id,
            type="suite",
            name=s.name,
            description=s.description,
            review_status=s.review_status,
            created_by=s.created_by,
            created_at=s.created_at,
            reviewed_by=s.reviewed_by,
            reviewed_at=s.reviewed_at,
            rejection_reason=s.rejection_reason,
        )
        for s in suites
    ]


@router.get("", response_model=PendingReviewListResponse)
async def list_all_pending(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all pending reviews (tests and suites) for the current user."""
    tests_resp = []
    if current_user.is_admin or current_user.has_permission("review:test"):
        stmt = (
            select(TestVersion, TestDefinition)
            .join(TestDefinition, TestVersion.test_definition_id == TestDefinition.id)
            .where(TestVersion.review_status == "pending_review")
            .order_by(TestVersion.created_at.desc())
        )
        result = await db.execute(stmt)
        for v, td in result.all():
            tests_resp.append(
                ReviewItemResponse(
                    id=v.id,
                    type="test",
                    name=(v.snapshot or {}).get("name", td.name),
                    description=(v.snapshot or {}).get("description", td.description),
                    review_status=v.review_status,
                    created_by=v.created_by,
                    created_at=v.created_at,
                    reviewed_by=str(v.reviewed_by) if v.reviewed_by else None,
                    reviewed_at=v.reviewed_at,
                    rejection_reason=v.rejection_reason,
                    version_id=v.id,
                    version_number=v.version,
                )
            )

    suites_resp = []
    if current_user.is_admin or current_user.has_permission("review:suite"):
        # Query both TestSuite and TestSuiteVersion for pending reviews
        # First, get TestSuite entries with pending review
        suite_stmt = (
            select(TestSuite)
            .where(TestSuite.review_status == "pending_review")
            .order_by(TestSuite.updated_at.desc())
        )
        suite_result = await db.execute(suite_stmt)
        for s in suite_result.scalars().all():
            suites_resp.append(
                ReviewItemResponse(
                    id=s.id,
                    type="suite",
                    name=s.name,
                    description=s.description,
                    review_status=s.review_status,
                    created_by=s.created_by,
                    created_at=s.created_at,
                    reviewed_by=s.reviewed_by,
                    reviewed_at=s.reviewed_at,
                    rejection_reason=s.rejection_reason,
                )
            )

        # Second, get TestSuiteVersion entries with pending review
        suite_version_stmt = (
            select(TestSuiteVersion, TestSuite)
            .join(TestSuite, TestSuiteVersion.test_suite_id == TestSuite.id)
            .where(TestSuiteVersion.review_status == "pending_review")
            .order_by(TestSuiteVersion.created_at.desc())
        )
        suite_version_result = await db.execute(suite_version_stmt)
        for sv, s in suite_version_result.all():
            suite_name = (sv.snapshot or {}).get("name", s.name)
            suites_resp.append(
                ReviewItemResponse(
                    id=sv.id,
                    type="suite_version",
                    name=suite_name,
                    description=(sv.snapshot or {}).get("description", sv.change_description or s.description),
                    review_status=sv.review_status,
                    created_by=sv.created_by,
                    created_at=sv.created_at,
                    reviewed_by=str(sv.reviewed_by) if sv.reviewed_by else None,
                    reviewed_at=sv.reviewed_at,
                    rejection_reason=sv.rejection_reason,
                    version_id=sv.id,
                    version_number=sv.version,
                )
            )

    return PendingReviewListResponse(tests=tests_resp, suites=suites_resp)

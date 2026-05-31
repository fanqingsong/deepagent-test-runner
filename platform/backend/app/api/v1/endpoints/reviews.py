"""
Reviews API Endpoints — Admin approval workflow for tests, suites, and versions.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models.test_definition import TestDefinition
from app.models.test_suite import TestSuite
from app.models.test_version import TestVersion
from app.models.user import User
from app.schemas.review import (
    PendingReviewListResponse,
    ReviewActionRequest,
    ReviewItemResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pending/tests", response_model=list[ReviewItemResponse])
async def list_pending_tests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
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


@router.get("/pending/suites", response_model=list[ReviewItemResponse])
async def list_pending_suites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
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


@router.get("/pending", response_model=PendingReviewListResponse)
async def list_all_pending(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
        stmt = (
            select(TestSuite)
            .where(TestSuite.review_status == "pending_review")
            .order_by(TestSuite.updated_at.desc())
        )
        result = await db.execute(stmt)
        for s in result.scalars().all():
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

    return PendingReviewListResponse(tests=tests_resp, suites=suites_resp)


@router.post("/versions/{version_id}/approve")
async def approve_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    stmt = select(TestVersion).where(TestVersion.id == version_id)
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    if version.review_status != "pending_review":
        raise HTTPException(status_code=400, detail="Version is not pending review")

    version.review_status = "approved"
    version.reviewed_by = current_user.id
    version.reviewed_at = datetime.utcnow()
    version.rejection_reason = None

    td_stmt = select(TestDefinition).where(TestDefinition.id == version.test_definition_id)
    td_result = await db.execute(td_stmt)
    test_def = td_result.scalar_one_or_none()
    if test_def:
        test_def.review_status = "approved"
        test_def.reviewed_by = current_user.id
        test_def.reviewed_at = datetime.utcnow()
        test_def.is_draft = False
        test_def.plan_generation_status = "approved"

    from app.models.app import App
    app_stmt = select(App).where(App.test_definition_id == version.test_definition_id)
    app_result = await db.execute(app_stmt)
    app = app_result.scalar_one_or_none()
    if app:
        app.status = "published"

    await db.commit()

    return {
        "status": "approved",
        "version_id": version.id,
        "version": version.version,
        "reviewed_by": current_user.id,
    }


@router.post("/versions/{version_id}/reject")
async def reject_version(
    version_id: int,
    data: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    stmt = select(TestVersion).where(TestVersion.id == version_id)
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    if version.review_status != "pending_review":
        raise HTTPException(status_code=400, detail="Version is not pending review")

    version.review_status = "rejected"
    version.reviewed_by = current_user.id
    version.reviewed_at = datetime.utcnow()
    version.rejection_reason = data.reason

    from app.models.app import App
    app_stmt = select(App).where(App.test_definition_id == version.test_definition_id)
    app_result = await db.execute(app_stmt)
    app = app_result.scalar_one_or_none()
    if app:
        app.status = "passed"

    await db.commit()

    return {
        "status": "rejected",
        "version_id": version.id,
        "version": version.version,
        "rejection_reason": data.reason,
    }


@router.post("/tests/{test_def_id}/approve")
async def approve_test(
    test_def_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    stmt = select(TestDefinition).where(TestDefinition.id == test_def_id)
    result = await db.execute(stmt)
    test_def = result.scalar_one_or_none()
    if not test_def:
        raise HTTPException(status_code=404, detail="Test definition not found")
    if test_def.review_status != "pending_review":
        raise HTTPException(status_code=400, detail="Test is not pending review")

    test_def.review_status = "approved"
    test_def.reviewed_by = current_user.id
    test_def.reviewed_at = datetime.utcnow()
    test_def.rejection_reason = None
    test_def.is_draft = False
    test_def.plan_generation_status = "approved"
    await db.commit()

    return {"status": "approved", "test_definition_id": test_def.id, "reviewed_by": current_user.id}


@router.post("/tests/{test_def_id}/reject")
async def reject_test(
    test_def_id: int,
    data: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    stmt = select(TestDefinition).where(TestDefinition.id == test_def_id)
    result = await db.execute(stmt)
    test_def = result.scalar_one_or_none()
    if not test_def:
        raise HTTPException(status_code=404, detail="Test definition not found")
    if test_def.review_status != "pending_review":
        raise HTTPException(status_code=400, detail="Test is not pending review")

    test_def.review_status = "rejected"
    test_def.reviewed_by = current_user.id
    test_def.reviewed_at = datetime.utcnow()
    test_def.rejection_reason = data.reason
    await db.commit()

    return {"status": "rejected", "test_definition_id": test_def.id, "rejection_reason": data.reason}


@router.post("/suites/{suite_id}/approve")
async def approve_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    stmt = select(TestSuite).where(TestSuite.id == suite_id)
    result = await db.execute(stmt)
    suite = result.scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    if suite.review_status != "pending_review":
        raise HTTPException(status_code=400, detail="Suite is not pending review")

    suite.review_status = "approved"
    suite.reviewed_by = str(current_user.id)
    suite.reviewed_at = datetime.utcnow()
    suite.rejection_reason = None
    await db.commit()

    return {"status": "approved", "suite_id": suite.id, "reviewed_by": str(current_user.id)}


@router.post("/suites/{suite_id}/reject")
async def reject_suite(
    suite_id: int,
    data: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    stmt = select(TestSuite).where(TestSuite.id == suite_id)
    result = await db.execute(stmt)
    suite = result.scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="Test suite not found")
    if suite.review_status != "pending_review":
        raise HTTPException(status_code=400, detail="Suite is not pending review")

    suite.review_status = "rejected"
    suite.reviewed_by = str(current_user.id)
    suite.reviewed_at = datetime.utcnow()
    suite.rejection_reason = data.reason
    await db.commit()

    return {"status": "rejected", "suite_id": suite.id, "rejection_reason": data.reason}

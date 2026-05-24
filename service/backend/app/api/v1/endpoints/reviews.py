"""
Reviews API Endpoints — Admin approval workflow for tests and suites.
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
        select(TestDefinition)
        .where(TestDefinition.review_status == "pending_review")
        .order_by(TestDefinition.updated_at.desc())
    )
    result = await db.execute(stmt)
    tests = result.scalars().all()
    return [
        ReviewItemResponse(
            id=t.id,
            type="test",
            name=t.name,
            description=t.description,
            review_status=t.review_status,
            created_by=str(t.created_by) if t.created_by else None,
            created_at=t.created_at,
            reviewed_by=str(t.reviewed_by) if t.reviewed_by else None,
            reviewed_at=t.reviewed_at,
            rejection_reason=t.rejection_reason,
        )
        for t in tests
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
            select(TestDefinition)
            .where(TestDefinition.review_status == "pending_review")
            .order_by(TestDefinition.updated_at.desc())
        )
        result = await db.execute(stmt)
        for t in result.scalars().all():
            tests_resp.append(
                ReviewItemResponse(
                    id=t.id,
                    type="test",
                    name=t.name,
                    description=t.description,
                    review_status=t.review_status,
                    created_by=str(t.created_by) if t.created_by else None,
                    created_at=t.created_at,
                    reviewed_by=str(t.reviewed_by) if t.reviewed_by else None,
                    reviewed_at=t.reviewed_at,
                    rejection_reason=t.rejection_reason,
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

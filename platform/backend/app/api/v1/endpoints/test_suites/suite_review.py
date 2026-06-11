"""
Test Suite Review Endpoints

Submit suites for admin review.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models.test_suite import TestSuite
from app.models.user import User

router = APIRouter()


@router.post("/{suite_id}/submit")
async def submit_suite_for_review(
    suite_id: int,
    current_user: User = Depends(RequirePermission("update:suite")),
    db: AsyncSession = Depends(get_db),
):
    """Submit a test suite for admin review."""
    result = await db.execute(
        select(TestSuite).where(TestSuite.id == suite_id)
    )
    suite = result.scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail=f"Test suite {suite_id} not found")
    if suite.review_status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail=f"Suite status is '{suite.review_status}', cannot submit")

    suite.review_status = "pending_review"
    suite.rejection_reason = None
    await db.commit()

    return {"suite_id": suite.id, "review_status": "pending_review"}

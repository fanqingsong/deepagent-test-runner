"""
Test Suite Review Endpoints

Handles approval, rejection, and publishing of test suites and suite versions.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.models.test_suite import TestSuite
from app.models.test_suite_version import TestSuiteVersion
from app.models.test_definition import TestDefinition
from app.models.test_version import TestVersion
from app.models.user import User
from app.schemas.review import ReviewActionRequest

router = APIRouter()


# ------------------------------------------------------------------
# Test Suite Review Endpoints
# ------------------------------------------------------------------

@router.get("/{suite_id}/detail")
async def get_suite_detail(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    """Get full details for a suite review."""
    stmt = select(TestSuite).where(TestSuite.id == suite_id)
    result = await db.execute(stmt)
    suite = result.scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")

    return {
        "id": suite.id,
        "type": "suite",
        "name": suite.name,
        "description": suite.description,
        "review_status": suite.review_status,
        "created_by": suite.created_by,
        "created_at": suite.created_at,
        "reviewed_by": suite.reviewed_by,
        "reviewed_at": suite.reviewed_at,
        "rejection_reason": suite.rejection_reason,
        "test_ids": suite.test_definition_ids,
    }


@router.post("/{suite_id}/approve")
async def approve_suite(
    suite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    """Approve a test suite."""
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


@router.post("/{suite_id}/reject")
async def reject_suite(
    suite_id: int,
    data: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    """Reject a test suite."""
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


# ------------------------------------------------------------------
# Test Definition Review Endpoints (direct, not via versions)
# ------------------------------------------------------------------

@router.post("/tests/{test_def_id}/approve")
async def approve_test(
    test_def_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    """Approve a test definition directly (not via version)."""
    from app.models.test_workspace import TestWorkspace

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

    workspace_stmt = select(TestWorkspace).where(TestWorkspace.test_definition_id == test_def.id)
    workspace_result = await db.execute(workspace_stmt)
    workspace = workspace_result.scalar_one_or_none()
    if workspace:
        workspace.status = "approved"

    await db.commit()

    return {"status": "approved", "test_definition_id": test_def.id, "reviewed_by": current_user.id}


@router.post("/tests/{test_def_id}/reject")
async def reject_test(
    test_def_id: int,
    data: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    """Reject a test definition directly and create a new draft version."""
    from app.models.test_workspace import TestWorkspace

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

    workspace_stmt = select(TestWorkspace).where(TestWorkspace.test_definition_id == test_def.id)
    workspace_result = await db.execute(workspace_stmt)
    workspace = workspace_result.scalar_one_or_none()
    if workspace:
        workspace.status = "draft"

    # Create a new draft version from latest snapshot
    latest_version_stmt = (
        select(TestVersion)
        .where(TestVersion.test_definition_id == test_def.id)
        .order_by(TestVersion.version.desc(), TestVersion.id.desc())
        .limit(1)
    )
    latest_version = (await db.execute(latest_version_stmt)).scalar_one_or_none()
    new_draft = TestVersion(
        test_definition_id=test_def.id,
        version=0,
        snapshot=latest_version.snapshot if latest_version else {},
        change_description="New draft after rejection",
        review_status="draft",
        created_by="system",
    )
    db.add(new_draft)

    await db.commit()

    return {"status": "rejected", "test_definition_id": test_def.id, "rejection_reason": data.reason}


# ------------------------------------------------------------------
# Suite Version Review Endpoints
# ------------------------------------------------------------------

@router.get("/suite-versions/{version_id}/detail")
async def get_suite_version_detail(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    """Get full details for a suite version review."""
    stmt = (
        select(TestSuiteVersion, TestSuite)
        .join(TestSuite, TestSuiteVersion.test_suite_id == TestSuite.id)
        .where(TestSuiteVersion.id == version_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Suite version not found")

    sv, s = row

    return {
        "id": sv.id,
        "type": "suite_version",
        "name": (sv.snapshot or {}).get("name", s.name),
        "description": (sv.snapshot or {}).get("description", sv.change_description or s.description),
        "review_status": sv.review_status,
        "created_by": sv.created_by,
        "created_at": sv.created_at,
        "reviewed_by": str(sv.reviewed_by) if sv.reviewed_by else None,
        "reviewed_at": sv.reviewed_at,
        "rejection_reason": sv.rejection_reason,
        "version_id": sv.id,
        "version_number": sv.version,
        "snapshot": sv.snapshot,
        "change_description": sv.change_description,
        "test_suite_id": sv.test_suite_id,
    }


@router.post("/suite-versions/{version_id}/approve")
async def approve_suite_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    """Approve a suite version."""
    stmt = select(TestSuiteVersion).where(TestSuiteVersion.id == version_id)
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Suite version not found")
    if version.review_status != "pending_review":
        raise HTTPException(status_code=400, detail="Suite version is not pending review")

    version.review_status = "approved"
    version.reviewed_by = current_user.id
    version.reviewed_at = datetime.utcnow()
    version.rejection_reason = None

    await db.commit()

    return {
        "status": "approved",
        "version_id": version.id,
        "version": version.version,
        "reviewed_by": current_user.id,
    }


@router.post("/suite-versions/{version_id}/publish")
async def publish_suite_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    """Publish an approved suite version to the Marketplace."""
    stmt = select(TestSuiteVersion).where(TestSuiteVersion.id == version_id)
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Suite version not found")
    if version.review_status != "approved":
        raise HTTPException(status_code=400, detail="Suite version must be approved before publishing")

    version.review_status = "published"
    version.reviewed_by = current_user.id
    version.reviewed_at = datetime.utcnow()

    await db.commit()

    return {
        "status": "published",
        "version_id": version.id,
        "version": version.version,
        "published_by": current_user.id,
    }


@router.post("/suite-versions/{version_id}/reject")
async def reject_suite_version(
    version_id: int,
    data: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:suite")),
):
    """Reject a suite version."""
    stmt = select(TestSuiteVersion).where(TestSuiteVersion.id == version_id)
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Suite version not found")
    if version.review_status != "pending_review":
        raise HTTPException(status_code=400, detail="Suite version is not pending review")

    version.review_status = "rejected"
    version.reviewed_by = current_user.id
    version.reviewed_at = datetime.utcnow()
    version.rejection_reason = data.reason

    await db.commit()

    return {
        "status": "rejected",
        "version_id": version.id,
        "version": version.version,
        "rejection_reason": data.reason,
    }

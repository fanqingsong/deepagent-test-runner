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
from app.models.test_suite_version import TestSuiteVersion
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

    from app.models.test_workspace import TestWorkspace
    workspace_stmt = select(TestWorkspace).where(TestWorkspace.test_definition_id == version.test_definition_id)
    workspace_result = await db.execute(workspace_stmt)
    workspace = workspace_result.scalar_one_or_none()
    if workspace:
        workspace.status = "approved"

    await db.commit()

    return {
        "status": "approved",
        "version_id": version.id,
        "version": version.version,
        "reviewed_by": current_user.id,
    }


@router.post("/versions/{version_id}/publish")
async def publish_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    """Publish an approved version to the Marketplace."""
    stmt = select(TestVersion).where(TestVersion.id == version_id)
    result = await db.execute(stmt)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    if version.review_status != "approved":
        raise HTTPException(status_code=400, detail="Version must be approved before publishing")

    version.review_status = "published"
    version.reviewed_by = current_user.id
    version.reviewed_at = datetime.utcnow()

    td_stmt = select(TestDefinition).where(TestDefinition.id == version.test_definition_id)
    td_result = await db.execute(td_stmt)
    test_def = td_result.scalar_one_or_none()
    if test_def:
        test_def.review_status = "published"
        test_def.is_draft = False

    from app.models.test_workspace import TestWorkspace
    workspace_stmt = select(TestWorkspace).where(TestWorkspace.test_definition_id == version.test_definition_id)
    workspace_result = await db.execute(workspace_stmt)
    workspace = workspace_result.scalar_one_or_none()
    if workspace:
        workspace.status = "published"

    await db.commit()

    return {
        "status": "published",
        "version_id": version.id,
        "version": version.version,
        "published_by": current_user.id,
    }


@router.get("/versions/{version_id}/detail")
async def get_version_detail(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    """Get full details for a version review including snapshot content."""
    stmt = (
        select(TestVersion, TestDefinition)
        .join(TestDefinition, TestVersion.test_definition_id == TestDefinition.id)
        .where(TestVersion.id == version_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Version not found")

    v, td = row

    return {
        "id": v.id,
        "type": "test_version",
        "name": (v.snapshot or {}).get("name", td.name),
        "description": (v.snapshot or {}).get("description", td.description),
        "review_status": v.review_status,
        "created_by": v.created_by,
        "created_at": v.created_at,
        "reviewed_by": str(v.reviewed_by) if v.reviewed_by else None,
        "reviewed_at": v.reviewed_at,
        "rejection_reason": v.rejection_reason,
        "version_id": v.id,
        "version_number": v.version,
        "snapshot": v.snapshot,
        "change_description": v.change_description,
        "test_definition_id": v.test_definition_id,
        "playwright_script": td.playwright_script,
        "script_status": td.script_status,
    }


@router.get("/suites/{suite_id}/detail")
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


@router.get("/approved")
async def list_approved(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    """List approved versions ready for publishing."""
    stmt = (
        select(TestVersion, TestDefinition)
        .join(TestDefinition, TestVersion.test_definition_id == TestDefinition.id)
        .where(TestVersion.review_status == "approved")
        .order_by(TestVersion.reviewed_at.desc())
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

    td_stmt = select(TestDefinition).where(TestDefinition.id == version.test_definition_id)
    td_result = await db.execute(td_stmt)
    test_def = td_result.scalar_one_or_none()
    if test_def:
        test_def.review_status = "rejected"
        test_def.rejection_reason = data.reason

    from app.models.test_workspace import TestWorkspace
    workspace_stmt = select(TestWorkspace).where(TestWorkspace.test_definition_id == version.test_definition_id)
    workspace_result = await db.execute(workspace_stmt)
    workspace = workspace_result.scalar_one_or_none()
    if workspace:
        workspace.status = "draft"

    # Create a new draft version from the rejected snapshot
    new_draft = TestVersion(
        test_definition_id=version.test_definition_id,
        version=0,
        snapshot=version.snapshot,
        change_description=f"New draft after rejection of v{version.version}",
        review_status="draft",
        created_by="system",
    )
    db.add(new_draft)

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

    from app.models.test_workspace import TestWorkspace
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

    from app.models.test_workspace import TestWorkspace
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


# Suite Version Review Endpoints

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

"""
Test Version Review Endpoints

Handles approval, rejection, and publishing of test versions.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.models.test_definition import TestDefinition
from app.models.test_version import TestVersion
from app.models.test_workspace import TestWorkspace
from app.models.user import User
from app.schemas.review import ReviewActionRequest, ReviewItemResponse

router = APIRouter()


@router.get("/approved", response_model=list[ReviewItemResponse])
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


@router.get("/{version_id}/detail")
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


@router.post("/{version_id}/approve")
async def approve_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    """Approve a test version for publishing."""
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


@router.post("/{version_id}/publish")
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


@router.post("/{version_id}/reject")
async def reject_version(
    version_id: int,
    data: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("review:test")),
):
    """Reject a test version and create a new draft."""
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

"""
Suite Versions API Endpoints

Operations for viewing and restoring test suite versions.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models import TestSuite, TestSuiteVersion
from app.models.user import User
from app.schemas import TestSuiteResponse, TestSuiteVersionSnapshot
from app.services.suite_version_service import SuiteVersionService

router = APIRouter()


@router.get("/test-suite/{test_suite_id}", response_model=List[TestSuiteVersionSnapshot])
async def list_suite_versions(
    test_suite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all versions of a test suite."""
    result = await db.execute(
        select(TestSuite).where(TestSuite.id == test_suite_id)
    )
    suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with id {test_suite_id} not found"
        )

    svc = SuiteVersionService(db)
    versions = await svc.list_versions(test_suite_id)
    return versions


@router.post("/test-suite/{test_suite_id}/restore/{version_id}", response_model=TestSuiteResponse)
async def restore_suite_version(
    test_suite_id: int,
    version_id: int,
    current_user: User = Depends(RequirePermission("update:suite")),
    db: AsyncSession = Depends(get_db)
):
    """Restore a test suite to a specific version."""
    svc = SuiteVersionService(db)
    try:
        suite = await svc.restore_version(test_suite_id, version_id)
        return suite
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{version_id}/submit", response_model=TestSuiteVersionSnapshot)
async def submit_suite_version_for_review(
    version_id: int,
    current_user: User = Depends(RequirePermission("update:suite")),
    db: AsyncSession = Depends(get_db)
):
    """Submit a suite version for review."""
    result = await db.execute(
        select(TestSuiteVersion).where(TestSuiteVersion.id == version_id)
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suite version {version_id} not found"
        )

    svc = SuiteVersionService(db)
    try:
        updated_version = await svc.submit_for_review(version.test_suite_id, version_id)
        return updated_version
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/test-suite/{test_suite_id}/create-draft", response_model=TestSuiteVersionSnapshot)
async def create_draft_from_suite_version(
    test_suite_id: int,
    from_version_id: int = None,
    current_user: User = Depends(RequirePermission("update:suite")),
    db: AsyncSession = Depends(get_db)
):
    """Create a draft version from an existing suite version."""
    result = await db.execute(
        select(TestSuite).where(TestSuite.id == test_suite_id)
    )
    suite = result.scalar_one_or_none()

    if not suite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test suite with id {test_suite_id} not found"
        )

    svc = SuiteVersionService(db)

    # Check if draft already exists
    versions = await svc.list_versions(test_suite_id)
    existing_draft = next((v for v in versions if v.review_status == "draft"), None)
    if existing_draft:
        return existing_draft

    # If from_version_id is provided, use that version
    # Otherwise use the latest version
    if from_version_id:
        result = await db.execute(
            select(TestSuiteVersion).where(TestSuiteVersion.id == from_version_id)
        )
        from_version = result.scalar_one_or_none()
        if not from_version or from_version.test_suite_id != test_suite_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source version {from_version_id} not found for this suite"
            )
        source_snapshot = from_version.snapshot
    else:
        # Use current suite state as snapshot
        source_snapshot = TestSuiteResponse.model_validate(suite).model_dump()

    # Create draft version
    draft_version = await svc.create_version(
        test_suite_id=test_suite_id,
        snapshot=source_snapshot,
        change_description="Created draft from existing version",
        created_by=str(current_user.id),
    )
    return draft_version

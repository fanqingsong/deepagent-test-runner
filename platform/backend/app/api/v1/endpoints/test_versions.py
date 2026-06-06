"""
Test Versions API Endpoints

Operations for viewing and restoring test definition versions.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models import TestDefinition, TestVersion
from app.models.user import User
from app.schemas import TestDefinitionResponse, TestVersionSnapshot

router = APIRouter()


@router.get("/test-definition/{test_definition_id}", response_model=List[TestVersionSnapshot])
async def list_test_versions(
    test_definition_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all versions of a test definition."""
    result = await db.execute(
        select(TestDefinition).where(TestDefinition.id == test_definition_id)
    )
    test_def = result.scalar_one_or_none()

    if not test_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definition with id {test_definition_id} not found"
        )

    result = await db.execute(
        select(TestVersion)
        .where(TestVersion.test_definition_id == test_definition_id)
        .order_by(TestVersion.version.desc())
    )
    versions = result.scalars().all()

    return versions


@router.get("/{version_id}", response_model=TestVersionSnapshot)
async def get_test_version(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific test version snapshot."""
    result = await db.execute(select(TestVersion).where(TestVersion.id == version_id))
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test version with id {version_id} not found"
        )

    return version


@router.post("/test-definition/{test_definition_id}/restore/{version_id}", response_model=TestDefinitionResponse)
async def restore_test_version(
    test_definition_id: int,
    version_id: int,
    current_user: User = Depends(RequirePermission("update:test")),
    db: AsyncSession = Depends(get_db)
):
    """Restore a test definition to a specific version."""
    result = await db.execute(
        select(TestDefinition).where(TestDefinition.id == test_definition_id)
    )
    test_def = result.scalar_one_or_none()

    if not test_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definition with id {test_definition_id} not found"
        )

    result = await db.execute(select(TestVersion).where(TestVersion.id == version_id))
    version = result.scalar_one_or_none()

    if not version or version.test_definition_id != test_definition_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test version with id {version_id} not found for this test definition"
        )

    # Create snapshot before restoring
    current_snapshot = TestDefinitionResponse.model_validate(test_def).model_dump()
    pre_restore_version = TestVersion(
        test_definition_id=test_definition_id,
        version=test_def.version,
        snapshot=current_snapshot,
        change_description="Pre-restore snapshot",
        created_by="system",
    )
    db.add(pre_restore_version)

    # Restore from version snapshot
    snapshot_data = version.snapshot
    test_def.name = snapshot_data.get("name", test_def.name)
    test_def.description = snapshot_data.get("description")
    test_def.url = snapshot_data.get("url")
    test_def.environment = snapshot_data.get("environment", {})
    test_def.tags = snapshot_data.get("tags", [])
    test_def.version += 1

    await db.commit()
    await db.refresh(test_def)

    result = await db.execute(
        select(TestDefinition).where(TestDefinition.id == test_definition_id)
    )
    return result.scalar_one()

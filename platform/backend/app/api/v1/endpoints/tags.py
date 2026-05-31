"""
Tags API Endpoints

Tag management for test definitions.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.test_definition import TestDefinition
from app.models.user import User
from app.schemas.tags import TagResponse, BulkTagApply

router = APIRouter()


@router.get("/", response_model=List[TagResponse])
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all unique tags with their usage counts across test definitions."""
    stmt = (
        select(
            func.unnest(TestDefinition.tags).label("tag"),
        )
        .where(TestDefinition.is_draft == False)
    )
    result = await db.execute(stmt)
    all_tags = [row[0] for row in result.fetchall()]

    tag_counts: dict[str, int] = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return [
        TagResponse(name=name, count=count)
        for name, count in sorted(tag_counts.items(), key=lambda x: -x[1])
    ]


@router.get("/{tag}/tests")
async def get_tests_by_tag(
    tag: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all test definitions with a given tag."""
    stmt = (
        select(TestDefinition)
        .where(TestDefinition.tags.any(tag))
        .where(TestDefinition.is_draft == False)
        .order_by(TestDefinition.created_at.desc())
    )
    result = await db.execute(stmt)
    test_defs = list(result.scalars().all())

    return [
        {
            "id": td.id,
            "test_id": td.test_id,
            "name": td.name,
            "url": td.url,
            "tags": td.tags,
            "is_draft": td.is_draft,
            "created_at": td.created_at,
        }
        for td in test_defs
    ]


@router.post("/bulk-apply", status_code=status.HTTP_200_OK)
async def bulk_apply_tags(
    body: BulkTagApply,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply tags to multiple test definitions (add, replace, or remove)."""
    stmt = select(TestDefinition).where(
        TestDefinition.id.in_(body.test_definition_ids)
    )
    result = await db.execute(stmt)
    test_defs = list(result.scalars().all())

    if len(test_defs) != len(body.test_definition_ids):
        found_ids = {td.id for td in test_defs}
        missing = set(body.test_definition_ids) - found_ids
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test definitions not found: {missing}",
        )

    updated = 0
    for td in test_defs:
        current_tags = list(td.tags or [])
        if body.mode == "replace":
            td.tags = list(body.tags)
        elif body.mode == "add":
            new_tags = [t for t in body.tags if t not in current_tags]
            td.tags = current_tags + new_tags
        elif body.mode == "remove":
            td.tags = [t for t in current_tags if t not in body.tags]
        updated += 1

    await db.commit()

    return {"updated": updated, "mode": body.mode, "tags": body.tags}

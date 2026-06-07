"""
Suite Permissions API Endpoints — test suite access control.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.test_suite import TestSuite
from app.models.user import User
from app.services.suite_permission_service import SuitePermissionService
from app.core.security import get_current_user
from app.core.permissions import RequirePermission

logger = logging.getLogger(__name__)

router = APIRouter()


class PermissionCreateRequest(BaseModel):
    user_id: int
    permission_type: str  # view|edit|execute|admin


class PermissionUpdateRequest(BaseModel):
    permission_type: str  # view|edit|execute|admin


class PermissionResponse(BaseModel):
    id: int
    test_suite_id: int
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    permission_type: str
    granted_by: Optional[int] = None
    created_at: Optional[str] = None


@router.get("/{test_suite_id}/permissions", response_model=List[PermissionResponse])
async def list_suite_permissions(
    test_suite_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:suite")),
):
    stmt = select(TestSuite).where(TestSuite.id == test_suite_id)
    result = await db.execute(stmt)
    suite = result.scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="TestSuite not found")

    svc = SuitePermissionService(db)
    return await svc.list_permissions(test_suite_id)


@router.post("/{test_suite_id}/permissions", response_model=PermissionResponse, status_code=201)
async def add_suite_permission(
    test_suite_id: int,
    req: PermissionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:suite")),
):
    stmt = select(TestSuite).where(TestSuite.id == test_suite_id)
    result = await db.execute(stmt)
    suite = result.scalar_one_or_none()
    if not suite:
        raise HTTPException(status_code=404, detail="TestSuite not found")

    stmt = select(User).where(User.id == req.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        svc = SuitePermissionService(db)
        perm = await svc.add_permission(
            test_suite_id=test_suite_id,
            user_id=req.user_id,
            permission_type=req.permission_type,
            granted_by=current_user.id,
        )
        perm["username"] = user.username
        perm["email"] = user.email
        return perm
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{test_suite_id}/permissions/{user_id}", response_model=PermissionResponse)
async def update_suite_permission(
    test_suite_id: int,
    user_id: int,
    req: PermissionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:suite")),
):
    try:
        svc = SuitePermissionService(db)
        perm = await svc.update_permission(
            test_suite_id=test_suite_id,
            user_id=user_id,
            permission_type=req.permission_type,
        )
        if not perm:
            raise HTTPException(status_code=404, detail="Permission not found")
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        perm["username"] = user.username if user else None
        perm["email"] = user.email if user else None
        return perm
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{test_suite_id}/permissions/{user_id}", status_code=204)
async def remove_suite_permission(
    test_suite_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:suite")),
):
    svc = SuitePermissionService(db)
    removed = await svc.remove_permission(test_suite_id=test_suite_id, user_id=user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Permission not found")

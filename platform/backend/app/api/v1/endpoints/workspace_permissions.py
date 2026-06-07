"""
App Permissions API Endpoints — workspace access control.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.test_workspace import TestWorkspace
from app.models.user import User
from app.services.permission_service import PermissionService
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
    workspace_id: int
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    permission_type: str
    granted_by: Optional[int] = None
    created_at: Optional[str] = None


@router.get("/{workspace_id}/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("read:test-case")),
):
    stmt = select(TestWorkspace).where(TestWorkspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="TestWorkspace not found")

    svc = PermissionService(db)
    return await svc.list_permissions(workspace_id)


@router.post("/{workspace_id}/permissions", response_model=PermissionResponse, status_code=201)
async def add_permission(
    workspace_id: int,
    req: PermissionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:test-case")),
):
    stmt = select(TestWorkspace).where(TestWorkspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="TestWorkspace not found")

    stmt = select(User).where(User.id == req.user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        svc = PermissionService(db)
        perm = await svc.add_permission(
            workspace_id=workspace_id,
            user_id=req.user_id,
            permission_type=req.permission_type,
        )
        perm["username"] = user.username
        perm["email"] = user.email
        return perm
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{workspace_id}/permissions/{user_id}", response_model=PermissionResponse)
async def update_permission(
    workspace_id: int,
    user_id: int,
    req: PermissionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:test-case")),
):
    try:
        svc = PermissionService(db)
        perm = await svc.update_permission(
            workspace_id=workspace_id,
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


@router.delete("/{workspace_id}/permissions/{user_id}", status_code=204)
async def remove_permission(
    workspace_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(RequirePermission("update:test-case")),
):
    svc = PermissionService(db)
    removed = await svc.remove_permission(workspace_id=workspace_id, user_id=user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Permission not found")

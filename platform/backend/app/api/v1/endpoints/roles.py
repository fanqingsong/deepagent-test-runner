"""
Role Management API Endpoints

CRUD operations for roles and permissions (RBAC).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.models.role import Permission, Role
from app.models.user import User
from app.schemas.role import PermissionResponse, RoleCreate, RoleResponse, RoleUpdate

router = APIRouter(prefix="/roles", tags=["roles"])


async def _get_role_or_404(role_id: int, db: AsyncSession) -> Role:
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(RequirePermission("read:role")),
    db: AsyncSession = Depends(get_db),
):
    """List all roles with their permissions."""
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .order_by(Role.name)
    )
    return list(result.scalars().all())


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    current_user: User = Depends(RequirePermission("read:role")),
    db: AsyncSession = Depends(get_db),
):
    """List all available permissions."""
    result = await db.execute(
        select(Permission).order_by(Permission.resource, Permission.action)
    )
    return list(result.scalars().all())


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    current_user: User = Depends(RequirePermission("create:role")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new custom role."""
    existing = await db.execute(select(Role).where(Role.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already in use",
        )

    permissions: list[Permission] = []
    if data.permission_ids:
        result = await db.execute(
            select(Permission).where(Permission.id.in_(data.permission_ids))
        )
        permissions = list(result.scalars().all())
        if len(permissions) != len(set(data.permission_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more permission IDs are invalid",
            )

    role = Role(
        name=data.name,
        description=data.description,
        is_system=False,
        permissions=permissions,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role, ["permissions"])
    return role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user: User = Depends(RequirePermission("update:role")),
    db: AsyncSession = Depends(get_db),
):
    """Update a role's name, description, and/or permissions."""
    role = await _get_role_or_404(role_id, db)

    if data.name is not None and data.name != role.name:
        if role.is_system:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="System role names cannot be changed",
            )
        existing = await db.execute(
            select(Role).where(Role.name == data.name, Role.id != role_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already in use",
            )
        role.name = data.name

    if data.description is not None:
        role.description = data.description

    if data.permission_ids is not None:
        result = await db.execute(
            select(Permission).where(Permission.id.in_(data.permission_ids))
        )
        permissions = list(result.scalars().all())
        if len(permissions) != len(set(data.permission_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more permission IDs are invalid",
            )
        role.permissions = permissions

    await db.commit()
    await db.refresh(role, ["permissions"])
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    current_user: User = Depends(RequirePermission("delete:role")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom role. System roles cannot be deleted."""
    role = await _get_role_or_404(role_id, db)

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System roles cannot be deleted",
        )

    await db.delete(role)
    await db.commit()

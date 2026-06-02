"""
Roles and Permissions API Endpoints

RBAC management: list/create/update/delete roles, manage permissions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.models.user import User
from app.models.role import Role, Permission, role_permissions
from app.schemas.role import (
    RoleResponse,
    RoleCreate,
    RoleUpdate,
    PermissionResponse,
)

router = APIRouter()


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    current_user: User = Depends(RequirePermission("read:role")),
    db: AsyncSession = Depends(get_db),
):
    """List all available permissions."""
    result = await db.execute(select(Permission).order_by(Permission.resource, Permission.action))
    return list(result.scalars().all())


@router.get("", response_model=list[RoleResponse])
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


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    current_user: User = Depends(RequirePermission("create:role")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new role with optional permissions."""
    existing = await db.execute(select(Role).where(Role.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Role '{data.name}' already exists")

    role = Role(name=data.name, description=data.description)
    db.add(role)
    await db.flush()

    if data.permission_ids:
        perms = await db.execute(
            select(Permission).where(Permission.id.in_(data.permission_ids))
        )
        role.permissions = list(perms.scalars().all())

    await db.commit()

    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role.id)
    )
    return result.scalar_one()


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(RequirePermission("read:role")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single role with permissions."""
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user: User = Depends(RequirePermission("update:role")),
    db: AsyncSession = Depends(get_db),
):
    """Update a role. System roles cannot be renamed."""
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if data.name is not None:
        if role.is_system:
            raise HTTPException(status_code=400, detail="Cannot rename system roles")
        role.name = data.name
    if data.description is not None:
        role.description = data.description

    if data.permission_ids is not None:
        perms = await db.execute(
            select(Permission).where(Permission.id.in_(data.permission_ids))
        )
        role.permissions = list(perms.scalars().all())

    await db.commit()

    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    return result.scalar_one()


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    current_user: User = Depends(RequirePermission("delete:role")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a non-system role."""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")
    await db.delete(role)
    await db.commit()

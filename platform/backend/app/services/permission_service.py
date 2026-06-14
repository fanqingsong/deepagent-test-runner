"""
Permission Service — manages App workspace access control.
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_workspace_permission import TestWorkspacePermission
from app.models.user import User
from app.services.interfaces.permission_service_interface import IPermissionService

VALID_PERMISSION_TYPES = {"view", "edit", "execute", "admin"}


class PermissionService(IPermissionService):
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize Permission Service.

        Args:
            db: Optional database session. If not provided, session must be passed to each method.
        """
        self._default_db = db

    def _get_db(self, db: Optional[AsyncSession] = None) -> AsyncSession:
        """
        Get database session for method execution.

        Args:
            db: Optional database session passed to method

        Returns:
            Database session to use

        Raises:
            ValueError: If no database session is available
        """
        if db is not None:
            return db
        if self._default_db is not None:
            return self._default_db
        raise ValueError("Database session required. Pass db parameter or initialize service with db session.")

    async def list_permissions(
        self,
        workspace_id: int,
        db: Optional[AsyncSession] = None
    ) -> List[tuple[TestWorkspacePermission, object]]:
        """
        List all permissions for a workspace with user information.

        Returns raw (permission, user) tuples - response formatting handled by API layer.
        """
        db = self._get_db(db)

        stmt = (
            select(TestWorkspacePermission, User)
            .join(User, TestWorkspacePermission.user_id == User.id)
            .where(TestWorkspacePermission.workspace_id == workspace_id)
        )
        result = await db.execute(stmt)
        return result.all()

    async def add_permission(
        self,
        workspace_id: int,
        user_id: int,
        permission_type: str,
        granted_by: Optional[int] = None,
        db: Optional[AsyncSession] = None
    ) -> TestWorkspacePermission:
        """
        Add or update a permission for a user in a workspace.

        Returns TestWorkspacePermission object - response formatting handled by API layer.
        """
        db = self._get_db(db)

        if permission_type not in VALID_PERMISSION_TYPES:
            raise ValueError(f"Invalid permission type: {permission_type}")

        stmt = select(TestWorkspacePermission).where(
            and_(
                TestWorkspacePermission.workspace_id == workspace_id,
                TestWorkspacePermission.user_id == user_id,
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.permission_type = permission_type
            existing.granted_by = granted_by
            await db.flush()
            return existing

        perm = TestWorkspacePermission(
            workspace_id=workspace_id,
            user_id=user_id,
            permission_type=permission_type,
            granted_by=granted_by,
        )
        db.add(perm)
        await db.flush()
        return perm

    async def update_permission(
        self,
        workspace_id: int,
        user_id: int,
        permission_type: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[TestWorkspacePermission]:
        """
        Update an existing permission.

        Returns TestWorkspacePermission object or None - response formatting handled by API layer.
        """
        db = self._get_db(db)

        if permission_type not in VALID_PERMISSION_TYPES:
            raise ValueError(f"Invalid permission type: {permission_type}")

        stmt = select(TestWorkspacePermission).where(
            and_(
                TestWorkspacePermission.workspace_id == workspace_id,
                TestWorkspacePermission.user_id == user_id,
            )
        )
        result = await db.execute(stmt)
        perm = result.scalar_one_or_none()
        if not perm:
            return None
        perm.permission_type = permission_type
        await db.flush()
        return perm

    async def remove_permission(
        self,
        workspace_id: int,
        user_id: int,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Remove a permission from a workspace."""
        db = self._get_db(db)

        stmt = select(TestWorkspacePermission).where(
            and_(
                TestWorkspacePermission.workspace_id == workspace_id,
                TestWorkspacePermission.user_id == user_id,
            )
        )
        result = await db.execute(stmt)
        perm = result.scalar_one_or_none()
        if not perm:
            return False
        await db.delete(perm)
        await db.flush()
        return True

    async def get_permission(
        self,
        workspace_id: int,
        user_id: int,
        db: Optional[AsyncSession] = None
    ) -> Optional[TestWorkspacePermission]:
        """Get a specific permission."""
        db = self._get_db(db)

        stmt = select(TestWorkspacePermission).where(
            and_(
                TestWorkspacePermission.workspace_id == workspace_id,
                TestWorkspacePermission.user_id == user_id,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

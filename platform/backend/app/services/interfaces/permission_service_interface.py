"""
Permission Service Interface

Defines the contract for permission management services.
Following the Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_workspace_permission import TestWorkspacePermission


class IPermissionService(ABC):
    """
    Interface for permission management services.

    This interface defines the contract for services that manage
    workspace permissions, ensuring clean separation of concerns.
    """

    @abstractmethod
    async def list_permissions(
        self,
        workspace_id: int,
        db: Optional[AsyncSession] = None
    ) -> List[tuple[TestWorkspacePermission, object]]:
        """
        List all permissions for a workspace with user information.

        Args:
            workspace_id: Workspace ID
            db: Optional database session (if service initialized without db)

        Returns:
            List of (permission, user) tuples

        Raises:
            Exception: If database query fails
        """
        pass

    @abstractmethod
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

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            permission_type: Type of permission (view, edit, execute, admin)
            granted_by: User ID who granted the permission
            db: Optional database session (if service initialized without db)

        Returns:
            Created or updated TestWorkspacePermission object

        Raises:
            ValueError: If permission_type is invalid
            Exception: If database operation fails
        """
        pass

    @abstractmethod
    async def update_permission(
        self,
        workspace_id: int,
        user_id: int,
        permission_type: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[TestWorkspacePermission]:
        """
        Update an existing permission.

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            permission_type: New permission type
            db: Optional database session (if service initialized without db)

        Returns:
            Updated TestWorkspacePermission object, or None if not found

        Raises:
            ValueError: If permission_type is invalid
            Exception: If database operation fails
        """
        pass

    @abstractmethod
    async def remove_permission(
        self,
        workspace_id: int,
        user_id: int,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Remove a permission from a workspace.

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            db: Optional database session (if service initialized without db)

        Returns:
            True if permission was removed, False if not found

        Raises:
            Exception: If database operation fails
        """
        pass

    @abstractmethod
    async def get_permission(
        self,
        workspace_id: int,
        user_id: int,
        db: Optional[AsyncSession] = None
    ) -> Optional[TestWorkspacePermission]:
        """
        Get a specific permission.

        Args:
            workspace_id: Workspace ID
            user_id: User ID
            db: Optional database session (if service initialized without db)

        Returns:
            TestWorkspacePermission object, or None if not found

        Raises:
            Exception: If database operation fails
        """
        pass

"""
Permission Response Builder

Handles response formatting for permission-related operations.
Following Single Responsibility Principle - only formats responses.
"""

from typing import Dict, Any, List
from datetime import datetime

from app.models.test_workspace_permission import TestWorkspacePermission
from app.models.user import User


class PermissionResponseBuilder:
    """
    Response builder for permission-related operations.

    Responsible only for formatting permission data into API responses,
    following Single Responsibility Principle.
    """

    @staticmethod
    def build_permission_summary(perm: TestWorkspacePermission) -> Dict[str, Any]:
        """
        Build permission summary for API response.

        Args:
            perm: TestWorkspacePermission model instance

        Returns:
            Formatted permission summary dictionary
        """
        return {
            "id": perm.id,
            "workspace_id": perm.workspace_id,
            "user_id": perm.user_id,
            "permission_type": perm.permission_type,
            "granted_by": perm.granted_by,
            "created_at": perm.created_at.isoformat() if perm.created_at else None,
        }

    @staticmethod
    def build_permission_with_user(
        perm: TestWorkspacePermission,
        user: User
    ) -> Dict[str, Any]:
        """
        Build permission with user information for API response.

        Args:
            perm: TestWorkspacePermission model instance
            user: User model instance

        Returns:
            Formatted permission with user dictionary
        """
        return {
            "id": perm.id,
            "workspace_id": perm.workspace_id,
            "user_id": perm.user_id,
            "username": user.username,
            "email": user.email,
            "permission_type": perm.permission_type,
            "granted_by": perm.granted_by,
            "created_at": perm.created_at.isoformat() if perm.created_at else None,
        }

    @staticmethod
    def build_permissions_list(
        permissions_users: List[tuple[TestWorkspacePermission, User]]
    ) -> List[Dict[str, Any]]:
        """
        Build list of permissions with user information for API response.

        Args:
            permissions_users: List of (permission, user) tuples

        Returns:
            List of formatted permission with user dictionaries
        """
        return [
            PermissionResponseBuilder.build_permission_with_user(perm, user)
            for perm, user in permissions_users
        ]

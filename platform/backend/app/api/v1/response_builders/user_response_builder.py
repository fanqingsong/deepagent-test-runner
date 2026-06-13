"""
User Response Builder

Handles response formatting for user-related operations.
Following Single Responsibility Principle - only formats responses.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.user import User


class UserResponseBuilder:
    """
    Response builder for user-related operations.

    Responsible only for formatting user data into API responses,
    following Single Responsibility Principle.
    """

    @staticmethod
    def build_user_summary(user: User) -> Dict[str, Any]:
        """
        Build user summary for API response.

        Args:
            user: User model instance

        Returns:
            Formatted user summary dictionary
        """
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    @staticmethod
    def build_user_with_roles(user: User) -> Dict[str, Any]:
        """
        Build user with roles for API response.

        Args:
            user: User model instance (should have roles loaded)

        Returns:
            Formatted user with roles dictionary
        """
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": [role.name for role in user.roles],
        }

    @staticmethod
    def build_users_list(users: List[User]) -> List[Dict[str, Any]]:
        """
        Build list of user summaries for API response.

        Args:
            users: List of User model instances

        Returns:
            List of formatted user summary dictionaries
        """
        return [UserResponseBuilder.build_user_with_roles(u) for u in users]

    @staticmethod
    def build_search_result(user: User) -> Dict[str, Any]:
        """
        Build user search result for API response.

        Args:
            user: User model instance

        Returns:
            Formatted search result dictionary
        """
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }

    @staticmethod
    def build_search_results(users: List[User]) -> List[Dict[str, Any]]:
        """
        Build user search results for API response.

        Args:
            users: List of User model instances

        Returns:
            List of formatted search result dictionaries
        """
        return [UserResponseBuilder.build_search_result(u) for u in users]

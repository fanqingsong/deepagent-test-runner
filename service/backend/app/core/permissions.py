"""
Centralized Permission Enforcement

FastAPI dependency factories for RBAC permission checks.
Builds on get_current_user from security.py which eager-loads roles+permissions.

Usage:
    @router.post("/", dependencies=[Depends(RequirePermission("create:test"))])
    # or, to get the user in the handler:
    @router.post("/")
    async def create_test(user: User = Depends(RequirePermission("create:test"))):
        ...
"""

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.user import User


def RequirePermission(permission_name: str):
    """Require a specific permission. Admins bypass all checks."""

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_admin:
            return current_user
        if not current_user.has_permission(permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission_name}'",
            )
        return current_user

    return _check


def RequireAnyPermission(*permission_names: str):
    """Require at least one of the given permissions. Admins bypass."""

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_admin:
            return current_user
        if any(current_user.has_permission(p) for p in permission_names):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: requires one of {list(permission_names)}",
        )

    return _check


def RequireRole(role_name: str):
    """Require a specific role. Admins bypass."""

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_admin:
            return current_user
        if not current_user.has_role(role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: '{role_name}'",
            )
        return current_user

    return _check


# Convenience: just require authentication, no permission check
RequireAuth = get_current_user

"""
Context manager for chat tools that need database access with auth.

Eliminates the repeated auth + DB session + permission check boilerplate
from every tool function.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@asynccontextmanager
async def tool_db_session(
    permission: str | None = None,
) -> AsyncGenerator[tuple[AsyncSession, User], None, None]:
    """Yield an authenticated (db_session, user) pair.

    Usage inside a @tool function::

        async with tool_db_session("read:test") as (db, user):
            result = await db.execute(...)
            return format_result(result)
    """
    from app.core.database import async_session_maker
    from app.agents.deepagent.tool_context import get_current_user_id

    user_id = get_current_user_id()
    if not user_id:
        raise AuthError("Authentication required.")

    async with async_session_maker() as db:
        user_result = await db.execute(select(User).where(User.id == user_id))
        current_user = user_result.scalar_one_or_none()

        if not current_user:
            raise AuthError("User not found.")

        if permission and not _check_permission(current_user, permission):
            raise PermissionError(f"You don't have permission ({permission}).")

        yield db, current_user


def _check_permission(user: User, permission_name: str) -> bool:
    return user.is_admin or user.has_permission(permission_name)


class AuthError(Exception):
    pass


class PermissionError(Exception):
    pass

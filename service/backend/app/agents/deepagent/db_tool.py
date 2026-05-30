"""
Sync DB helpers for chat tools running inside LangGraph thread pools.

LangGraph executes tool calls in a sync thread pool where async SQLAlchemy
cannot run (greenlet_spawn error). All tools must use sync DB operations
via sync_session_maker.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.agents.deepagent.tool_context import get_current_user_id

logger = logging.getLogger(__name__)


@contextmanager
def sync_tool_db_session(
    permission: str | None = None,
) -> Generator[tuple[Session, User], None, None]:
    """Yield an authenticated (sync_db_session, user) pair.

    Usage inside a blocking helper function::

        with sync_tool_db_session("read:test") as (db, user):
            result = db.execute(...)
            return format_result(result)
    """
    from app.core.database import sync_session_maker

    user_id = get_current_user_id()
    if not user_id:
        raise AuthError("Authentication required.")

    db = sync_session_maker()
    try:
        user_result = db.execute(select(User).where(User.id == user_id))
        current_user = user_result.scalar_one_or_none()

        if not current_user:
            raise AuthError("User not found.")

        if permission and not _check_permission(current_user, permission):
            raise PermissionError(f"You don't have permission ({permission}).")

        yield db, current_user
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _check_permission(user: User, permission_name: str) -> bool:
    return user.is_admin or user.has_permission(permission_name)


class AuthError(Exception):
    pass


class PermissionError(Exception):
    pass

"""
Context management for chat tools.

Provides a way to pass user context to tools that are called by the LLM.
Supports both FastAPI (ContextVar) and LangGraph Platform Server (config) contexts.
"""

from contextvars import ContextVar
from typing import Optional

# Context variable to store the current user ID
current_user_id_ctx: ContextVar[Optional[int]] = ContextVar('current_user_id', default=None)


def get_current_user_id() -> Optional[int]:
    """Get the current user ID from context.

    Checks ContextVar first (FastAPI), then falls back to LangGraph config.
    """
    user_id = current_user_id_ctx.get()
    if user_id is not None:
        return user_id
    try:
        from langgraph.config import get_config
        config = get_config()
        uid = config.get("configurable", {}).get("user_id")
        if uid is not None:
            return int(uid)
        return None
    except Exception:
        return None


def set_current_user_id(user_id: int) -> None:
    """Set the current user ID in context."""
    current_user_id_ctx.set(user_id)


def clear_current_user_id() -> None:
    """Clear the current user ID from context."""
    current_user_id_ctx.set(None)

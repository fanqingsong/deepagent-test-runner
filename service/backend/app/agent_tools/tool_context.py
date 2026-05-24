"""
Context management for chat tools.

Provides a way to pass user context to tools that are called by the LLM.
"""

from contextvars import ContextVar
from typing import Optional

# Context variable to store the current user ID
current_user_id_ctx: ContextVar[Optional[int]] = ContextVar('current_user_id', default=None)


def get_current_user_id() -> Optional[int]:
    """Get the current user ID from context."""
    return current_user_id_ctx.get()


def set_current_user_id(user_id: int) -> None:
    """Set the current user ID in context."""
    current_user_id_ctx.set(user_id)


def clear_current_user_id() -> None:
    """Clear the current user ID from context."""
    current_user_id_ctx.set(None)

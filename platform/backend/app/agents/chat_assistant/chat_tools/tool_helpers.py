"""
Chat Tool Helpers

Shared formatting functions and utilities for chat assistant tools.
"""

from typing import Optional

from langgraph.config import get_config


def _handle_auth_error(e: Exception) -> str:
    """Format authentication/permission errors for user display."""
    return f"Error: {e}"


def _resolve_user_id() -> Optional[int]:
    """Resolve user_id from LangGraph config (must be called in async context)."""
    try:
        config = get_config()
        uid = config.get("configurable", {}).get("user_id")
        if uid is not None:
            return int(uid)
    except Exception:
        pass
    return None


def _format_test_case(test) -> str:
    """Format a test case for display in chat."""
    status_emoji = {
        "draft": "📝",
        "pending_review": "⏳",
        "approved": "✅",
        "rejected": "❌",
    }
    emoji = status_emoji.get(test.review_status or "draft", "📝")
    return (
        f"{emoji} **{test.name}** (ID: {test.id})\n"
        f"   Status: {test.review_status or 'draft'}\n"
        f"   URL: {test.url or 'N/A'}\n"
        f"   Created: {test.created_at.strftime('%Y-%m-%d %H:%M') if test.created_at else 'N/A'}"
    )


def _format_test_suite(suite) -> str:
    """Format a test suite for display in chat."""
    status_emoji = {
        "draft": "📝",
        "pending_review": "⏳",
        "approved": "✅",
        "rejected": "❌",
    }
    emoji = status_emoji.get(suite.review_status or "draft", "📝")
    test_count = len(suite.test_definition_ids or [])
    return (
        f"{emoji} **{suite.name}** (ID: {suite.id})\n"
        f"   Tests: {test_count}\n"
        f"   Status: {suite.review_status or 'draft'}\n"
        f"   Created: {suite.created_at.strftime('%Y-%m-%d %H:%M') if suite.created_at else 'N/A'}"
    )


def _format_user(user) -> str:
    """Format a user for display in chat."""
    roles_str = ", ".join([role.name for role in user.roles]) if user.roles else "No roles"
    return (
        f"👤 **{user.username}** (ID: {user.id})\n"
        f"   Email: {user.email}\n"
        f"   Roles: {roles_str}\n"
        f"   Admin: {'Yes' if user.is_admin else 'No'}"
    )


def _format_role(role) -> str:
    """Format a role for display in chat."""
    perm_count = len(role.permissions) if role.permissions else 0
    return (
        f"🔐 **{role.name}** (ID: {role.id})\n"
        f"   Description: {role.description or 'N/A'}\n"
        f"   Permissions: {perm_count}\n"
        f"   System: {'Yes' if role.is_system else 'No'}"
    )

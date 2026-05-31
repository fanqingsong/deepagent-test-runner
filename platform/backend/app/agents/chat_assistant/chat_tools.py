"""
Chat Tools for AI Assistant

Provides tools for querying system data and executing actions
with proper permission checks.

All DB operations use sync SQLAlchemy (sync_session_maker) wrapped
in run_in_executor to avoid greenlet_spawn errors in LangGraph's
thread pool.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy import select, func

from app.models.test_definition import TestDefinition
from app.models.test_suite import TestSuite
from app.models.test_run import TestRun
from app.models.role import Role
from app.models.user import User
from app.agents.chat_assistant.db_tool import sync_tool_db_session, AuthError, PermissionError

logger = logging.getLogger(__name__)


def _handle_auth_error(e: Exception) -> str:
    return f"Error: {e}"


def _resolve_user_id() -> Optional[int]:
    """Resolve user_id from LangGraph config (must be called in async context)."""
    try:
        from langgraph.config import get_config
        config = get_config()
        uid = config.get("configurable", {}).get("user_id")
        if uid is not None:
            return int(uid)
    except Exception:
        pass
    return None


def _format_test_case(test: TestDefinition) -> str:
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


def _format_test_suite(suite: TestSuite) -> str:
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


def _format_user(user: User) -> str:
    roles_str = ", ".join([role.name for role in user.roles]) if user.roles else "No roles"
    return (
        f"👤 **{user.username}** (ID: {user.id})\n"
        f"   Email: {user.email}\n"
        f"   Roles: {roles_str}\n"
        f"   Admin: {'Yes' if user.is_admin else 'No'}"
    )


def _format_role(role: Role) -> str:
    perm_count = len(role.permissions) if role.permissions else 0
    return (
        f"🔐 **{role.name}** (ID: {role.id})\n"
        f"   Description: {role.description or 'N/A'}\n"
        f"   Permissions: {perm_count}\n"
        f"   System: {'Yes' if role.is_system else 'No'}"
    )


# --- Blocking DB helpers (run via run_in_executor) ---


def _query_test_cases_sync(user_id, name_filter, status_filter, limit):
    try:
        with sync_tool_db_session("read:test", user_id=user_id) as (db, _):
            stmt = select(TestDefinition).where(TestDefinition.is_active == True)
            if name_filter:
                stmt = stmt.where(TestDefinition.name.ilike(f"%{name_filter}%"))
            if status_filter:
                stmt = stmt.where(TestDefinition.review_status == status_filter)
            stmt = stmt.order_by(TestDefinition.created_at.desc()).limit(limit)
            result = db.execute(stmt)
            tests = result.scalars().all()
            if not tests:
                return "No test cases found matching your criteria."
            formatted = [f"Found {len(tests)} test case(s):\n"]
            for test in tests:
                formatted.append(_format_test_case(test))
            return "\n\n".join(formatted)
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error querying test cases: {e}")
        return f"Error querying test cases: {str(e)}"


def _query_test_suites_sync(user_id, name_filter, status_filter, limit):
    try:
        with sync_tool_db_session("read:suite", user_id=user_id) as (db, _):
            stmt = select(TestSuite)
            if name_filter:
                stmt = stmt.where(TestSuite.name.ilike(f"%{name_filter}%"))
            if status_filter:
                stmt = stmt.where(TestSuite.review_status == status_filter)
            stmt = stmt.order_by(TestSuite.created_at.desc()).limit(limit)
            result = db.execute(stmt)
            suites = result.scalars().all()
            if not suites:
                return "No test suites found matching your criteria."
            formatted = [f"Found {len(suites)} test suite(s):\n"]
            for suite in suites:
                formatted.append(_format_test_suite(suite))
            return "\n\n".join(formatted)
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error querying test suites: {e}")
        return f"Error querying test suites: {str(e)}"


def _query_users_sync(user_id, username_filter, limit):
    try:
        with sync_tool_db_session("read:user", user_id=user_id) as (db, _):
            stmt = select(User)
            if username_filter:
                stmt = stmt.where(User.username.ilike(f"%{username_filter}%"))
            stmt = stmt.order_by(User.created_at.desc()).limit(limit)
            result = db.execute(stmt)
            users = result.scalars().all()
            if not users:
                return "No users found matching your criteria."
            formatted = [f"Found {len(users)} user(s):\n"]
            for user in users:
                formatted.append(_format_user(user))
            return "\n\n".join(formatted)
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error querying users: {e}")
        return f"Error querying users: {str(e)}"


def _query_roles_sync(user_id, name_filter):
    try:
        with sync_tool_db_session("read:role", user_id=user_id) as (db, _):
            stmt = select(Role)
            if name_filter:
                stmt = stmt.where(Role.name.ilike(f"%{name_filter}%"))
            stmt = stmt.order_by(Role.name)
            result = db.execute(stmt)
            roles = result.scalars().all()
            if not roles:
                return "No roles found matching your criteria."
            formatted = [f"Found {len(roles)} role(s):\n"]
            for role in roles:
                formatted.append(_format_role(role))
            return "\n\n".join(formatted)
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error querying roles: {e}")
        return f"Error querying roles: {str(e)}"


def _set_user_role_sync(caller_id, user_id, role_name):
    try:
        with sync_tool_db_session("update:user", user_id=caller_id) as (db, _):
            user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            if not user:
                return f"Error: User with ID {user_id} not found."
            role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
            if not role:
                return f"Error: Role '{role_name}' not found."
            if user.roles and any(r.id == role.id for r in user.roles):
                return f"User '{user.username}' already has role '{role_name}'."
            if not user.roles:
                user.roles = []
            user.roles.append(role)
            db.commit()
            return f"✅ Successfully assigned role '{role_name}' to user '{user.username}'."
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error setting user role: {e}")
        return f"Error setting user role: {str(e)}"


def _remove_user_role_sync(caller_id, user_id, role_name):
    try:
        with sync_tool_db_session("update:user", user_id=caller_id) as (db, _):
            user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
            if not user:
                return f"Error: User with ID {user_id} not found."
            if not user.roles or not any(r.name == role_name for r in user.roles):
                return f"User '{user.username}' does not have role '{role_name}'."
            user.roles = [r for r in user.roles if r.name != role_name]
            db.commit()
            return f"✅ Successfully removed role '{role_name}' from user '{user.username}'."
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error removing user role: {e}")
        return f"Error removing user role: {str(e)}"


def _approve_test_sync(user_id, test_id):
    try:
        with sync_tool_db_session("review:test", user_id=user_id) as (db, current_user):
            test = db.execute(select(TestDefinition).where(TestDefinition.id == test_id)).scalar_one_or_none()
            if not test:
                return f"Error: Test case with ID {test_id} not found."
            if test.review_status == "approved":
                return f"Test case '{test.name}' is already approved."
            test.review_status = "approved"
            test.reviewed_by = current_user.id
            test.reviewed_at = datetime.utcnow()
            db.commit()
            return f"✅ Successfully approved test case '{test.name}'."
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error approving test: {e}")
        return f"Error approving test: {str(e)}"


def _reject_test_sync(user_id, test_id, reason):
    try:
        with sync_tool_db_session("review:test", user_id=user_id) as (db, current_user):
            test = db.execute(select(TestDefinition).where(TestDefinition.id == test_id)).scalar_one_or_none()
            if not test:
                return f"Error: Test case with ID {test_id} not found."
            test.review_status = "rejected"
            test.rejection_reason = reason
            test.reviewed_by = current_user.id
            test.reviewed_at = datetime.utcnow()
            db.commit()
            return f"✅ Successfully rejected test case '{test.name}'. Reason: {reason}"
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error rejecting test: {e}")
        return f"Error rejecting test: {str(e)}"


def _approve_suite_sync(user_id, suite_id):
    try:
        with sync_tool_db_session("review:suite", user_id=user_id) as (db, current_user):
            suite = db.execute(select(TestSuite).where(TestSuite.id == suite_id)).scalar_one_or_none()
            if not suite:
                return f"Error: Test suite with ID {suite_id} not found."
            if suite.review_status == "approved":
                return f"Test suite '{suite.name}' is already approved."
            suite.review_status = "approved"
            suite.reviewed_by = current_user.id
            suite.reviewed_at = datetime.utcnow()
            db.commit()
            return f"✅ Successfully approved test suite '{suite.name}'."
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error approving suite: {e}")
        return f"Error approving suite: {str(e)}"


def _reject_suite_sync(user_id, suite_id, reason):
    try:
        with sync_tool_db_session("review:suite", user_id=user_id) as (db, current_user):
            suite = db.execute(select(TestSuite).where(TestSuite.id == suite_id)).scalar_one_or_none()
            if not suite:
                return f"Error: Test suite with ID {suite_id} not found."
            suite.review_status = "rejected"
            suite.rejection_reason = reason
            suite.reviewed_by = current_user.id
            suite.reviewed_at = datetime.utcnow()
            db.commit()
            return f"✅ Successfully rejected test suite '{suite.name}'. Reason: {reason}"
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error rejecting suite: {e}")
        return f"Error rejecting suite: {str(e)}"


def _get_system_stats_sync(user_id):
    try:
        with sync_tool_db_session(user_id=user_id) as (db, _):
            test_count = db.scalar(
                select(func.count()).select_from(TestDefinition).where(TestDefinition.is_active == True)
            )
            suite_count = db.scalar(
                select(func.count()).select_from(TestSuite)
            )
            user_count = db.scalar(
                select(func.count()).select_from(User)
            )
            role_count = db.scalar(
                select(func.count()).select_from(Role)
            )
            return (
                f"📊 **System Statistics**\n\n"
                f"🧪 Test Cases: {test_count}\n"
                f"📋 Test Suites: {suite_count}\n"
                f"👥 Users: {user_count}\n"
                f"🔐 Roles: {role_count}\n\n"
                f"You can ask me to:\n"
                f"• Query test cases or suites\n"
                f"• View users and roles\n"
                f"• Set user roles (requires permission)\n"
                f"• Approve/reject tests or suites (requires permission)"
            )
    except (AuthError, PermissionError) as e:
        return _handle_auth_error(e)
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return f"Error getting system stats: {str(e)}"


# --- LangChain @tool wrappers (async, delegate to sync via run_in_executor) ---


@tool
async def query_test_cases(
    name_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Query test cases in the system.

    Args:
        name_filter: Optional filter by test name (partial match)
        status_filter: Optional filter by review status (draft, pending_review, approved, rejected)
        limit: Maximum number of results (default 10)

    Returns:
        Formatted list of test cases with key details
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _query_test_cases_sync, user_id, name_filter, status_filter, limit,
    )


@tool
async def query_test_suites(
    name_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Query test suites in the system.

    Args:
        name_filter: Optional filter by suite name (partial match)
        status_filter: Optional filter by review status (draft, pending_review, approved, rejected)
        limit: Maximum number of results (default 10)

    Returns:
        Formatted list of test suites with key details
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _query_test_suites_sync, user_id, name_filter, status_filter, limit,
    )


@tool
async def query_users(
    username_filter: Optional[str] = None,
    limit: int = 10,
) -> str:
    """Query users in the system.

    Args:
        username_filter: Optional filter by username (partial match)
        limit: Maximum number of results (default 10)

    Returns:
        Formatted list of users with their roles
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _query_users_sync, user_id, username_filter, limit,
    )


@tool
async def query_roles(
    name_filter: Optional[str] = None,
) -> str:
    """Query roles in the system.

    Args:
        name_filter: Optional filter by role name (partial match)

    Returns:
        Formatted list of roles with their permissions
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _query_roles_sync, user_id, name_filter,
    )


@tool
async def set_user_role(
    user_id: int,
    role_name: str,
) -> str:
    """Assign a role to a user.

    Args:
        user_id: ID of the user to assign the role to
        role_name: Name of the role to assign

    Returns:
        Success message or error description
    """
    caller_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _set_user_role_sync, caller_id, user_id, role_name,
    )


@tool
async def remove_user_role(
    user_id: int,
    role_name: str,
) -> str:
    """Remove a role from a user.

    Args:
        user_id: ID of the user to remove the role from
        role_name: Name of the role to remove

    Returns:
        Success message or error description
    """
    caller_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _remove_user_role_sync, caller_id, user_id, role_name,
    )


@tool
async def approve_test(
    test_id: int,
) -> str:
    """Approve a test case for publication.

    Args:
        test_id: ID of the test case to approve

    Returns:
        Success message or error description
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _approve_test_sync, user_id, test_id,
    )


@tool
async def reject_test(
    test_id: int,
    reason: str = "No reason provided",
) -> str:
    """Reject a test case.

    Args:
        test_id: ID of the test case to reject
        reason: Reason for rejection

    Returns:
        Success message or error description
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _reject_test_sync, user_id, test_id, reason,
    )


@tool
async def approve_suite(
    suite_id: int,
) -> str:
    """Approve a test suite for publication.

    Args:
        suite_id: ID of the test suite to approve

    Returns:
        Success message or error description
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _approve_suite_sync, user_id, suite_id,
    )


@tool
async def reject_suite(
    suite_id: int,
    reason: str = "No reason provided",
) -> str:
    """Reject a test suite.

    Args:
        suite_id: ID of the test suite to reject
        reason: Reason for rejection

    Returns:
        Success message or error description
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _reject_suite_sync, user_id, suite_id, reason,
    )


@tool
async def get_system_stats() -> str:
    """Get system statistics and overview.

    Returns:
        Formatted system statistics
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _get_system_stats_sync, user_id,
    )

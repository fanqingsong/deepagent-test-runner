"""
Chat Tools Package

Provides LangChain tools for querying system data and executing actions.
Split into focused modules:
- tool_helpers: Shared formatting and utility functions
- tool_queries: Database query functions
- tool_actions: User role and approval/rejection actions
"""

import asyncio
from typing import Optional
from langchain_core.tools import tool

from .tool_helpers import _resolve_user_id
from .tool_queries import (
    _query_test_cases_sync,
    _query_test_suites_sync,
    _query_users_sync,
    _query_roles_sync,
    _get_system_stats_sync,
)
from .tool_actions import (
    _set_user_role_sync,
    _remove_user_role_sync,
    _approve_test_sync,
    _reject_test_sync,
    _approve_suite_sync,
    _reject_suite_sync,
)

__all__ = [
    "query_test_cases",
    "query_test_suites",
    "query_users",
    "query_roles",
    "set_user_role",
    "remove_user_role",
    "approve_test",
    "reject_test",
    "approve_suite",
    "reject_suite",
    "get_system_stats",
]


# ------------------------------------------------------------------
# Query Tools
# ------------------------------------------------------------------

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
async def get_system_stats() -> str:
    """Get system statistics and overview.

    Returns:
        Formatted system statistics
    """
    user_id = _resolve_user_id()
    return await asyncio.get_running_loop().run_in_executor(
        None, _get_system_stats_sync, user_id,
    )


# ------------------------------------------------------------------
# Action Tools
# ------------------------------------------------------------------

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

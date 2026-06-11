"""
Chat Tool Query Functions

Synchronous database query functions for chat assistant.
These are run via run_in_executor to avoid greenlet_spawn errors.
"""

import logging
from typing import Optional
from sqlalchemy import select, func

from app.models.test_definition import TestDefinition
from app.models.test_suite import TestSuite
from app.models.user import User
from app.models.role import Role
from app.agents.chat_assistant.db_tool import sync_tool_db_session, AuthError, PermissionError

from .tool_helpers import (
    _handle_auth_error,
    _format_test_case,
    _format_test_suite,
    _format_user,
    _format_role,
)

logger = logging.getLogger(__name__)


def _query_test_cases_sync(user_id, name_filter, status_filter, limit):
    """Query test cases from database."""
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
    """Query test suites from database."""
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
    """Query users from database."""
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
    """Query roles from database."""
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


def _get_system_stats_sync(user_id):
    """Get system statistics from database."""
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

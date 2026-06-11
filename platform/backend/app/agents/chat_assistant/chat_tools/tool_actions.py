"""
Chat Tool Action Functions

Synchronous database action functions for chat assistant.
These handle user role changes and test/suite approvals.
"""

import logging
from datetime import datetime
from sqlalchemy import select

from app.models.test_definition import TestDefinition
from app.models.test_suite import TestSuite
from app.models.user import User
from app.models.role import Role
from app.agents.chat_assistant.db_tool import sync_tool_db_session, AuthError, PermissionError

from .tool_helpers import _handle_auth_error

logger = logging.getLogger(__name__)


def _set_user_role_sync(caller_id, user_id, role_name):
    """Assign a role to a user."""
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
    """Remove a role from a user."""
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
    """Approve a test case."""
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
    """Reject a test case."""
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
    """Approve a test suite."""
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
    """Reject a test suite."""
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

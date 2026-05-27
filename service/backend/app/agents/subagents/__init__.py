"""
Subagents for the Chat Agent.

Each subagent is a specialized agent compiled with specific tools
for a particular domain.
"""

from .test_query_agent import get_test_query_subagent
from .user_admin_agent import get_user_admin_subagent
from .test_reviewer_agent import get_test_reviewer_subagent
from .analytics_agent import get_analytics_subagent

__all__ = [
    "get_test_query_subagent",
    "get_user_admin_subagent",
    "get_test_reviewer_subagent",
    "get_analytics_subagent",
]

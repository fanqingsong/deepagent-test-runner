"""
Subagents for the Chat Agent.

Each subagent is a specialized agent compiled with specific tools
for a particular domain.
"""

from .test_query_agent import get_test_query_subagent
from .user_admin_agent import get_user_admin_subagent
from .test_reviewer_agent import get_test_reviewer_subagent
from .analytics_agent import get_analytics_subagent
from .search_agent import get_search_subagent
from .email_agent import get_email_subagent
from .data_analysis_agent import get_data_analysis_subagent
from .rag_agent import get_rag_subagent
from .sql_agent import get_sql_query_subagent

__all__ = [
    "get_test_query_subagent",
    "get_user_admin_subagent",
    "get_test_reviewer_subagent",
    "get_analytics_subagent",
    "get_search_subagent",
    "get_email_subagent",
    "get_data_analysis_subagent",
    "get_rag_subagent",
    "get_sql_query_subagent",
]

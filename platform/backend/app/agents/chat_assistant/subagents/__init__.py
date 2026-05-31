"""
Subagents for the Chat Agent.

Each subagent is a specialized agent compiled with specific tools
for a particular domain.
"""

from .test_query_agent import get_test_query_subagent
from .user_admin_agent import get_user_admin_subagent
from .test_reviewer_agent import get_test_reviewer_subagent
from .analytics_agent import get_analytics_subagent
from .email_agent import get_email_subagent
from .data_analysis_agent import get_data_analysis_subagent
from .sql_agent import get_sql_query_subagent
from .content_builder_agent import get_content_builder_subagent
from .deep_research_subagent import get_deep_research_subagent
from .knowledge_base_agent import get_knowledge_base_subagent

__all__ = [
    "get_test_query_subagent",
    "get_user_admin_subagent",
    "get_test_reviewer_subagent",
    "get_analytics_subagent",
    "get_email_subagent",
    "get_data_analysis_subagent",
    "get_sql_query_subagent",
    "get_content_builder_subagent",
    "get_deep_research_subagent",
    "get_knowledge_base_subagent",
]

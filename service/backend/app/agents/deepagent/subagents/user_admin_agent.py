"""
User Admin Subagent — Specialized for user and role management.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.deepagent.chat_tools import (
    query_users,
    query_roles,
    set_user_role,
    remove_user_role,
)


def create_user_admin_graph(llm):
    """Create the compiled graph for the user admin subagent."""
    return create_agent(
        model=llm,
        tools=[query_users, query_roles, set_user_role, remove_user_role],
        system_prompt="You handle user management operations. Always verify permissions before making changes. Explain clearly what changes will be made before executing them. When viewing users, present their information in an organized way.",
    )


def get_user_admin_subagent(llm):
    """Get the compiled user admin subagent."""
    return CompiledSubAgent(
        name="user-admin",
        description="Manage users and their roles. Use this for user-related operations like viewing users, checking roles, assigning roles, or removing roles.",
        runnable=create_user_admin_graph(llm),
    )

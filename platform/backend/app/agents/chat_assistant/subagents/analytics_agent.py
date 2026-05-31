"""
Analytics Subagent — Specialized for system statistics and metrics.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.chat_assistant.chat_tools import get_system_stats


def create_analytics_graph(llm):
    """Create the compiled graph for the analytics subagent."""
    return create_agent(
        model=llm,
        tools=[get_system_stats],
        system_prompt="You provide accurate system statistics and metrics. Present data in a clear, organized manner. Highlight key insights and trends when relevant.",
    )


def get_analytics_subagent(llm):
    """Get the compiled analytics subagent."""
    return CompiledSubAgent(
        name="analytics",
        description="Provide system statistics and analytics reports. Use this when the user asks about system stats, metrics, or overall platform health.",
        runnable=create_analytics_graph(llm),
    )

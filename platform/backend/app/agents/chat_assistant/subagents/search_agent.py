"""
Search Subagent — Specialized for web search using Tavily.

Provides web search capabilities with result summarization
and source attribution.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.chat_assistant.search_tools import web_search, search_with_summary


def create_search_graph(llm):
    """Create the compiled graph for the search subagent."""
    return create_agent(
        model=llm,
        tools=[web_search, search_with_summary],
        system_prompt="You are a web search specialist. Use the search tools to find current information, news, facts, and data. When returning results, always provide a clear summary with source links. Be concise and focus on the most relevant information.",
    )


def get_search_subagent(llm):
    """Get the compiled search subagent."""
    return CompiledSubAgent(
        name="search",
        description="Search the web for current information, news, facts, and data. Use this when the user asks about recent events, needs up-to-date information, requests web research, or asks questions that require live data.",
        runnable=create_search_graph(llm),
    )

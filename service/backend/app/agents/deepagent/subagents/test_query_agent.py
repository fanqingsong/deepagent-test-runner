"""
Test Query Subagent — Specialized for searching and retrieving test information.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agent_tools.chat_tools import query_test_cases, query_test_suites


def create_test_query_graph(llm):
    """Create the compiled graph for the test query subagent."""
    return create_agent(
        model=llm,
        tools=[query_test_cases, query_test_suites],
        system_prompt="You are a test query specialist. Search and retrieve test information accurately. When returning results, format them clearly with key details like test name, status, and any relevant metadata.",
    )


def get_test_query_subagent(llm):
    """Get the compiled test query subagent."""
    return CompiledSubAgent(
        name="test-query",
        description="Query test cases and test suites. Use this when the user asks about existing tests, wants to search for test cases, or needs information about test suites.",
        runnable=create_test_query_graph(llm),
    )

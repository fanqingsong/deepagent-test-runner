"""
Test Reviewer Subagent — Specialized for test approval and review workflows.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.chat_assistant.chat_tools import (
    approve_test,
    reject_test,
    approve_suite,
    reject_suite,
)


def create_test_reviewer_graph(llm):
    """Create the compiled graph for the test reviewer subagent."""
    return create_agent(
        model=llm,
        tools=[approve_test, reject_test, approve_suite, reject_suite],
        system_prompt="You review test content before publication. Ensure quality standards are met. When approving or rejecting, explain your decision clearly. Always check that the user has the necessary permissions before proceeding.",
    )


def get_test_reviewer_subagent(llm):
    """Get the compiled test reviewer subagent."""
    return CompiledSubAgent(
        name="test-reviewer",
        description="Approve or reject test cases and test suites for publication. Use this when the user wants to review, approve, or reject tests.",
        runnable=create_test_reviewer_graph(llm),
    )

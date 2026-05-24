"""
Chat Agent — Deep Agents-based conversational AI assistant.

Provides a simple chat interface with tools for querying system data
and executing actions with proper permission checks.
"""

import logging
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent

from app.agent_tools.chat_tools import (
    query_test_cases,
    query_test_suites,
    query_users,
    query_roles,
    set_user_role,
    remove_user_role,
    approve_test,
    reject_test,
    approve_suite,
    reject_suite,
    get_system_stats,
)
from app.core.agent_config import get_llm
from app.agent_tools.tool_context import set_current_user_id, clear_current_user_id

logger = logging.getLogger(__name__)


class ChatAgent:
    """Conversational AI assistant for the E2E testing platform."""

    def __init__(self):
        """Initialize the chat agent using deepagents framework."""
        self.checkpointer = MemorySaver()
        self.tools = self._get_tools()

        # Get LLM configuration from settings
        llm = get_llm(temperature=0.7, max_tokens=2048)

        # Create deep agent with built-in middleware
        self.agent = create_deep_agent(
            model=llm,
            tools=self.tools,
            checkpointer=self.checkpointer,
            system_prompt=self._get_system_prompt()
        )

        logger.info("Chat agent initialized with deepagents framework")

    def _get_tools(self) -> list[BaseTool]:
        """Get available tools for the chat agent."""
        return [
            query_test_cases,
            query_test_suites,
            query_users,
            query_roles,
            set_user_role,
            remove_user_role,
            approve_test,
            reject_test,
            approve_suite,
            reject_suite,
            get_system_stats,
        ]

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the chat agent."""
        return """You are an AI assistant for the E2E testing platform. You help users:

• Query test cases, test suites, execution results
• View users and roles
• Execute actions with proper approval (setting roles, approving tests)

Be concise and helpful. For actions requiring permissions:
1. Explain what you will do
2. Request user confirmation
3. Execute only after approval

For queries, provide clear, formatted answers with key information.

Available tools:
- query_test_cases: Search and view test cases
- query_test_suites: Search and view test suites
- query_users: View users and their roles
- query_roles: View available roles
- set_user_role: Assign a role to a user (requires update:user permission)
- remove_user_role: Remove a role from a user (requires update:user permission)
- approve_test: Approve a test case (requires review:test permission)
- reject_test: Reject a test case (requires review:test permission)
- approve_suite: Approve a test suite (requires review:suite permission)
- reject_suite: Reject a test suite (requires review:suite permission)
- get_system_stats: Get system statistics

When a user lacks permission for an action, explain the requirement clearly."""

    async def chat(
        self,
        message: str,
        thread_id: str,
        user_id: int,
        current_user: Any = None,
        db: Any = None,
    ) -> Dict[str, Any]:
        """Send a message and get a response.

        Args:
            message: User message
            thread_id: Conversation thread ID for persistence
            user_id: User ID
            current_user: Current user object (for compatibility)
            db: Database session (for compatibility)

        Returns:
            Response with messages and metadata
        """
        try:
            print(f"[CHAT DEBUG] Starting chat with message: {message[:100]}...")

            # Set the user context for tools
            set_current_user_id(user_id)

            # Prepare the input for the agent
            agent_input = {
                "messages": [{"role": "user", "content": message}],
            }

            # Configure the thread for conversation persistence
            config = {
                "configurable": {
                    "thread_id": thread_id,
                }
            }

            print(f"[CHAT DEBUG] Invoking Agent with thread_id: {thread_id}")

            # Invoke the deep agent
            result = await self.agent.ainvoke(agent_input, config=config)

            print(f"[CHAT DEBUG] Agent invocation completed")

            # Extract the last message content
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                response_content = getattr(last_message, "content", "")
            else:
                response_content = "I've processed your request."

            # Check for tool calls in the result
            tool_calls = []
            for msg in messages:
                tc = getattr(msg, "tool_calls", None)
                if tc:
                    tool_calls.extend(tc if isinstance(tc, list) else [tc])

            print(f"[CHAT DEBUG] Response: {response_content[:100] if response_content else 'None'}...")
            print(f"[CHAT DEBUG] Tool calls: {len(tool_calls)}")

            return {
                "response": response_content or "I've processed your request.",
                "tool_calls": tool_calls,
                "messages": messages,
            }

        except Exception as e:
            print(f"[CHAT DEBUG] Error in chat: {e}")
            import traceback
            print(f"[CHAT DEBUG] Traceback: {traceback.format_exc()}")
            return {
                "response": f"Sorry, I encountered an error: {str(e)}",
                "tool_calls": [],
                "messages": [],
            }
        finally:
            # Clear the user context
            clear_current_user_id()


# Singleton instance
_chat_agent: Optional[ChatAgent] = None


def get_chat_agent() -> ChatAgent:
    """Get or create the chat agent singleton.

    Returns:
        ChatAgent instance
    """
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent

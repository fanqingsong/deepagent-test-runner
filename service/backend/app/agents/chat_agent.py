"""
Chat Agent — Deep Agents-based conversational AI assistant.

Provides a simple chat interface with tools for querying system data
and executing actions with proper permission checks.
"""

import logging
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
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
        """Initialize the chat agent using deepagents framework with subagents."""
        self.checkpointer = MemorySaver()

        # Get LLM configuration from settings
        llm = get_llm(temperature=0.7, max_tokens=4096)

        # Create deep agent with specialized subagents
        self.agent = create_deep_agent(
            model=llm,
            checkpointer=self.checkpointer,
            system_prompt=self._get_system_prompt(),
            subagents=[
                {
                    "name": "test-query",
                    "description": "Query test cases and test suites. Use this when the user asks about existing tests, wants to search for test cases, or needs information about test suites.",
                    "system_prompt": "You are a test query specialist. Search and retrieve test information accurately. When returning results, format them clearly with key details like test name, status, and any relevant metadata.",
                    "tools": [query_test_cases, query_test_suites],
                },
                {
                    "name": "user-admin",
                    "description": "Manage users and their roles. Use this for user-related operations like viewing users, checking roles, assigning roles, or removing roles.",
                    "system_prompt": "You handle user management operations. Always verify permissions before making changes. Explain clearly what changes will be made before executing them. When viewing users, present their information in an organized way.",
                    "tools": [query_users, query_roles, set_user_role, remove_user_role],
                },
                {
                    "name": "test-reviewer",
                    "description": "Approve or reject test cases and test suites for publication. Use this when the user wants to review, approve, or reject tests.",
                    "system_prompt": "You review test content before publication. Ensure quality standards are met. When approving or rejecting, explain your decision clearly. Always check that the user has the necessary permissions before proceeding.",
                    "tools": [approve_test, reject_test, approve_suite, reject_suite],
                },
                {
                    "name": "analytics",
                    "description": "Provide system statistics and analytics reports. Use this when the user asks about system stats, metrics, or overall platform health.",
                    "system_prompt": "You provide accurate system statistics and metrics. Present data in a clear, organized manner. Highlight key insights and trends when relevant.",
                    "tools": [get_system_stats],
                },
            ],
        )

        logger.info("Chat agent initialized with deepagents framework and 4 subagents")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the chat agent."""
        return """You are an AI assistant for the E2E testing platform. You coordinate specialized subagents to help users with various tasks.

**Your Role:**
You are the main coordinator that routes user requests to appropriate specialized subagents. You have access to these subagents:
- **test-query**: For searching and viewing test cases and test suites
- **user-admin**: For managing users and their roles
- **test-reviewer**: For approving or rejecting tests and suites
- **analytics**: For system statistics and metrics

**How to Work:**
1. Analyze the user's request to determine which subagent(s) to use
2. Delegate the task to the appropriate subagent using the `task` tool
3. When multiple subagents are needed, coordinate them sequentially
4. Always provide clear, human-readable summaries of what the subagents found or did

**Important Guidelines:**
- After delegating to a subagent, synthesize the results into a helpful response for the user
- Don't just repeat the subagent output - explain it in context
- For actions requiring permissions, make sure the subagent explains what will happen first
- When a user lacks permission, explain the requirement clearly
- Be concise but thorough in your responses"""

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

            # Extract the last AI message content (not ToolMessage)
            messages = result.get("messages", [])
            response_content = None
            tool_result_content = None

            # Debug: Log all messages
            print(f"[CHAT DEBUG] Total messages: {len(messages)}")
            for i, msg in enumerate(messages):
                msg_type = getattr(msg, "type", "") or type(msg).__name__
                content_preview = getattr(msg, "content", "")[:50]
                print(f"[CHAT DEBUG] Message {i}: type={msg_type}, content={content_preview}...")

            if messages:
                # First, try to find the last AIMessage with meaningful content
                for msg in reversed(messages):
                    msg_type = getattr(msg, "type", "") or type(msg).__name__
                    content = getattr(msg, "content", "")

                    # Skip ToolMessages but save their content as fallback
                    if msg_type == "tool":
                        content_stripped = content.strip() if content else ""
                        print(f"[CHAT DEBUG] ToolMessage content: '{content_stripped[:100]}', len={len(content_stripped)}")
                        if content and content_stripped and content_stripped != "...":
                            tool_result_content = content
                            print(f"[CHAT DEBUG] Saved tool result as fallback, length: {len(content)}")
                        else:
                            print(f"[CHAT DEBUG] Tool result not saved (empty or dots only)")
                        continue

                    # Skip messages without meaningful content
                    content_stripped = content.strip() if content else ""
                    if not content_stripped or content_stripped == "..." or len(content_stripped) < 10:
                        print(f"[CHAT DEBUG] Skipping message with no meaningful content: '{content_stripped[:50]}'")
                        continue

                    # Found the response
                    response_content = content
                    print(f"[CHAT DEBUG] Found response in {msg_type} message, length: {len(content)}")
                    break

                # If no AI response found but we have tool results, use them
                if not response_content and tool_result_content:
                    print(f"[CHAT DEBUG] No AI response found, using tool result as fallback")
                    response_content = tool_result_content

            if not response_content:
                print(f"[CHAT DEBUG] No response found, using fallback")
                response_content = "I've processed your request."

            # Only extract tool calls that have actual args (not empty)
            # Tool results are already included in the response content
            tool_calls = []
            for msg in messages:
                tc = getattr(msg, "tool_calls", None)
                if tc:
                    for call in (tc if isinstance(tc, list) else [tc]):
                        # Only include tool calls with actual arguments
                        args = getattr(call, "args", None)
                        if args and len(args) > 0:
                            tool_calls.append(call)

            print(f"[CHAT DEBUG] Final response length: {len(response_content)}")
            print(f"[CHAT DEBUG] Response preview: {response_content[:500]}")
            print(f"[CHAT DEBUG] Tool calls with args: {len(tool_calls)}")

            return {
                "response": response_content,
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

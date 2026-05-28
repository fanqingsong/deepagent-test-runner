"""
Chat Agent — Deep Agents-based conversational AI assistant.

Provides a simple chat interface with tools for querying system data
and executing actions with proper permission checks.
"""

import asyncio
import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_config
from langgraph.store.memory import InMemoryStore
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

from app.core.agent_config import get_llm
from app.core.config import settings
from app.core.llm_context import llm_usage_context
from app.agent_tools.tool_context import set_current_user_id, clear_current_user_id
from app.agents.subagents import (
    get_test_query_subagent,
    get_user_admin_subagent,
    get_test_reviewer_subagent,
    get_analytics_subagent,
    get_search_subagent,
)

logger = logging.getLogger(__name__)


class ChatAgent:
    """Conversational AI assistant for the E2E testing platform."""

    def __init__(self):
        """Initialize the chat agent using deepagents framework with compiled subagents."""
        self.checkpointer = MemorySaver()
        self._store: InMemoryStore | None = None
        self._ready = False

        llm = get_llm(temperature=0.7, max_tokens=8192)

        self.agent = create_deep_agent(
            model=llm,
            checkpointer=self.checkpointer,
            system_prompt=self._get_system_prompt(),
            memory=["/memories/AGENTS.md"],
            backend=CompositeBackend(
                default=StateBackend(),
                routes={
                    "/memories/": StoreBackend(
                        namespace=lambda rt: ("user", str(get_config().get("metadata", {}).get("user_id", "default")))
                    ),
                },
            ),
            subagents=[
                get_test_query_subagent(llm),
                get_user_admin_subagent(llm),
                get_test_reviewer_subagent(llm),
                get_analytics_subagent(llm),
                get_search_subagent(llm),
            ],
            debug=True,
        )

        logger.info("Chat agent initialized (store will be set up on first chat)")

    async def _ensure_store(self):
        """Lazily initialize the in-memory store."""
        if self._ready:
            return

        self._store = InMemoryStore()
        self.agent.store = self._store
        self._ready = True

        logger.info("InMemoryStore initialized — memory persists during runtime")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the chat agent."""
        return """You are an AI assistant for the E2E testing platform. You coordinate specialized subagents to help users with various tasks.

**Your Role:**
You are the main coordinator that routes user requests to appropriate specialized subagents using the `task` tool.

**How to Work:**
1. Analyze the user's request and delegate to the appropriate subagent
2. When multiple subagents are needed, coordinate them sequentially
3. Synthesize the subagent results into a helpful, human-readable response

**Memory & Context:**
Use your memory filesystem (/memories/) to persist important information across conversations. When the user shares their name, preferences, or project details, write them to /memories/AGENTS.md so you can recall them later.

**Response Guidelines:**
- Don't just repeat the subagent output - explain it in context
- For actions requiring permissions, ensure the subagent explains what will happen first
- When a user lacks permission, explain the requirement clearly
- Be concise but thorough"""

    async def chat(
        self,
        message: str,
        thread_id: str,
        user_id: int,
        current_user: Any = None,
        db: Any = None,
    ) -> dict[str, Any]:
        """Send a message and get a response."""
        try:
            await self._ensure_store()

            logger.info("Starting chat: user_id=%s, thread_id=%s", user_id, thread_id)

            set_current_user_id(user_id)

            agent_input = {
                "messages": [{"role": "user", "content": message}],
            }

            config = {
                "configurable": {
                    "thread_id": thread_id,
                },
                "metadata": {
                    "user_id": user_id,
                },
            }

            with llm_usage_context("chat", user_id=user_id):
                result = await self.agent.ainvoke(agent_input, config=config)

            # Extract the last AI message content (not ToolMessage)
            messages = result.get("messages", [])
            response_content = None
            tool_result_content = None

            logger.debug("Agent returned %d messages", len(messages))

            if messages:
                for msg in reversed(messages):
                    msg_type = getattr(msg, "type", "") or type(msg).__name__
                    content = getattr(msg, "content", "")

                    if msg_type == "tool":
                        stripped = content.strip() if content else ""
                        # Skip empty-looking tool results like "[]", "..."
                        if (content and stripped
                                and stripped != "..."
                                and stripped != "[]"
                                and stripped != "{}"):
                            # Don't overwrite with a less meaningful result
                            if not tool_result_content:
                                tool_result_content = content
                        continue

                    if not (content.strip() if content else ""):
                        continue

                    if msg_type == "human":
                        continue

                    response_content = content
                    break

                if not response_content and tool_result_content:
                    response_content = tool_result_content

            if not response_content:
                response_content = "I've processed your request."

            tool_calls = []
            for msg in messages:
                tc = getattr(msg, "tool_calls", None)
                if tc:
                    for call in (tc if isinstance(tc, list) else [tc]):
                        args = getattr(call, "args", None)
                        if args and len(args) > 0:
                            tool_calls.append(call)

            logger.info("Chat complete: response_len=%d, tool_calls=%d", len(response_content), len(tool_calls))

            return {
                "response": response_content,
                "tool_calls": tool_calls,
                "messages": messages,
            }

        except Exception as e:
            logger.exception("Error in chat")
            return {
                "response": f"Sorry, I encountered an error: {e}",
                "tool_calls": [],
                "messages": [],
            }
        finally:
            clear_current_user_id()


# Singleton instance
_chat_agent: ChatAgent | None = None


def get_chat_agent() -> ChatAgent:
    """Get or create the chat agent singleton."""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent

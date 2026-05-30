"""
Chat Agent — Deep Agents-based conversational AI assistant.

Provides a simple chat interface with tools for querying system data
and executing actions with proper permission checks.
"""

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_config
from langgraph.store.memory import InMemoryStore
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

from app.core.agent_config import get_llm
from app.core.config import settings
from app.agents.deepagent.subagents import (
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
                        namespace=lambda rt: ("user", str(
                            get_config().get("configurable", {}).get("user_id")
                            or get_config().get("metadata", {}).get("user_id")
                            or "default"
                        ))
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

    async def generate_title(self, message: str) -> str:
        """Generate a short conversation title from the user's first message."""
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_llm(temperature=0.3, max_tokens=50)
        messages = [
            SystemMessage(content=(
                "Generate a very short conversation title (max 20 characters) "
                "summarizing the user's intent. "
                "Output ONLY the title text, nothing else. "
                "Use the same language as the user's message."
            )),
            HumanMessage(content=message),
        ]
        result = await llm.ainvoke(messages)
        title = result.content.strip().strip('"').strip("'")
        return title[:50] if len(title) > 50 else title

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the chat agent."""
        return """You are an AI assistant for the E2E testing platform. You coordinate specialized subagents to help users with various tasks.

**Your Role:**
You are the main coordinator that routes user requests to appropriate specialized subagents using the `task` tool.

**How to Work:**
1. Analyze the user's request complexity
2. For multi-step or complex requests, use `write_todos` to create a plan first — break the task into clear, actionable steps
3. Work through each todo item, delegating to the appropriate subagent via `task`
4. Update todo status as you progress (pending → in_progress → completed)
5. Synthesize the results into a helpful, human-readable response

**When to Plan with Todos:**
- User requests involve 3+ steps or multiple subagents
- User asks for analysis, comparison, or complex data operations
- The task has clear sequential dependencies
- Simple single-step questions (greetings, quick lookups) do NOT need a plan

**Memory & Context:**
Use your memory filesystem (/memories/) to persist important information across conversations. When the user shares their name, preferences, or project details, write them to /memories/AGENTS.md so you can recall them later.

**Response Guidelines:**
- Don't just repeat the subagent output - explain it in context
- For actions requiring permissions, ensure the subagent explains what will happen first
- When a user lacks permission, explain the requirement clearly
- Be concise but thorough"""

    def _get_subagent_description(self, subagent_name: str) -> str:
        """Get human-readable description for subagent."""
        descriptions = {
            "test-query": "Querying test cases and suites",
            "user-admin": "Managing user accounts and permissions",
            "test-reviewer": "Analyzing test results and outcomes",
            "analytics": "Processing analytics and metrics",
            "search": "Searching web and external sources",
            "planner": "Planning task execution",
            "executor": "Executing planned tasks",
            "reviewer": "Reviewing and validating results",
        }
        return descriptions.get(subagent_name, "Processing request")


# Singleton instance
_chat_agent: ChatAgent | None = None


def get_chat_agent() -> ChatAgent:
    """Get or create the chat agent singleton."""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent

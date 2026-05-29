"""
Chat Agent — Deep Agents-based conversational AI assistant.

Provides a simple chat interface with tools for querying system data
and executing actions with proper permission checks.
"""

import asyncio
import logging
import time
from typing import Any, AsyncIterator

from fastapi import WebSocket
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_config
from langgraph.store.memory import InMemoryStore
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

from app.core.agent_config import get_llm
from app.core.config import settings
from app.core.llm_context import llm_usage_context
from app.agents.deepagent.tool_context import set_current_user_id, clear_current_user_id
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
        enable_search: bool = False,
        enable_deep_thinking: bool = False,
    ) -> dict[str, Any]:
        """Send a message and get a response."""
        try:
            await self._ensure_store()

            logger.info("Starting chat: user_id=%s, thread_id=%s, enable_search=%s, enable_deep_thinking=%s", user_id, thread_id, enable_search, enable_deep_thinking)

            set_current_user_id(user_id)

            system_notes = []
            if not enable_search:
                system_notes.append("The search subagent is currently disabled. Do NOT route to the 'search' subagent for any reason.")
            if enable_deep_thinking:
                system_notes.append(
                    "Deep thinking mode is enabled. Use write_todos to create a structured task plan before acting. "
                    "Break complex questions into focused subtasks. Execute each subtask via the appropriate subagent. "
                    "After receiving results, assess what you've learned and plan next steps before continuing. "
                    "Synthesize all findings into a comprehensive, well-structured response."
                )
            if system_notes:
                content = f"{message}\n\n[System note: {' '.join(system_notes)}]"
            else:
                content = message

            agent_input = {
                "messages": [{"role": "user", "content": content}],
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

    async def chat_stream(
        self,
        message: str,
        thread_id: str,
        user_id: int,
        current_user: Any = None,
        db: Any = None,
        enable_search: bool = False,
        enable_deep_thinking: bool = False,
        websocket: WebSocket = None,
    ) -> AsyncIterator[dict]:
        """Stream chat responses with real-time updates.

        Yields dictionaries containing stream events that can be sent via WebSocket.
        Events include:
        - token_delta: Individual tokens as they generate
        - subagent_started: When a subagent begins work
        - subagent_progress: Progress updates during execution
        - tool_call/tool_result: Tool invocations and results
        - stream_complete: Final completion event
        """
        try:
            await self._ensure_store()

            logger.info("Starting chat stream: user_id=%s, thread_id=%s, enable_search=%s, enable_deep_thinking=%s",
                       user_id, thread_id, enable_search, enable_deep_thinking)

            set_current_user_id(user_id)

            system_notes = []
            if not enable_search:
                system_notes.append("The search subagent is currently disabled. Do NOT route to the 'search' subagent for any reason.")
            if enable_deep_thinking:
                system_notes.append(
                    "Deep thinking mode is enabled. Use write_todos to create a structured task plan before acting. "
                    "Break complex questions into focused subtasks. Execute each subtask via the appropriate subagent. "
                    "After receiving results, assess what you've learned and plan next steps before continuing. "
                    "Synthesize all findings into a comprehensive, well-structured response."
                )
            if system_notes:
                content = f"{message}\n\n[System note: {' '.join(system_notes)}]"
            else:
                content = message

            agent_input = {
                "messages": [{"role": "user", "content": content}],
            }

            config = {
                "configurable": {
                    "thread_id": thread_id,
                },
                "metadata": {
                    "user_id": user_id,
                },
            }

            # Track subagent activity
            current_subagent = None
            subagent_start_time = None
            accumulated_content = ""
            tool_calls = []

            # Stream with multiple modes for comprehensive updates
            with llm_usage_context("chat", user_id=user_id):
                for chunk in self.agent.stream(
                    agent_input,
                    config=config,
                    stream_mode=["updates", "messages"],
                    subgraphs=True,
                    version="v2",
                ):
                    # Debug: Log the chunk structure to understand what we're receiving
                    logger.debug(f"Stream chunk type: {chunk.get('type')}, keys: {chunk.keys()}, ns: {chunk.get('ns')}")

                    # Process different chunk types
                    if chunk.get("type") == "updates":
                        # Handle subagent progress updates
                        update_data = chunk.get("data", {})
                        namespace = chunk.get("ns", [])

                        # Determine if this is main agent or subagent
                        if not namespace:
                            # Main agent update
                            for node_name, node_data in update_data.items():
                                if node_name == "tools":
                                    # Tool call completed
                                    for msg in node_data.get("messages", []):
                                        msg_type = getattr(msg, "type", "")
                                        if msg_type == "tool":
                                            tool_name = getattr(msg, "name", "")
                                            tool_content = getattr(msg, "content", "")
                                            tool_calls.append({
                                                "name": tool_name,
                                                "args": tool_content,
                                                "result": str(tool_content)[:500] if tool_content else ""
                                            })
                                            yield {
                                                "type": "tool_result",
                                                "tool": tool_name,
                                                "result": str(tool_content)[:500] if tool_content else "",
                                                "source": "main"
                                            }
                        else:
                            # Subagent update - extract subagent name from namespace
                            subagent_name = namespace[0] if namespace else "unknown"

                            # Track subagent transitions
                            if subagent_name != current_subagent:
                                if current_subagent:
                                    # Previous subagent completed
                                    yield {
                                        "type": "subagent_completed",
                                        "subagent": current_subagent,
                                        "duration": time.time() - subagent_start_time
                                    }

                                current_subagent = subagent_name
                                subagent_start_time = time.time()
                                yield {
                                    "type": "subagent_started",
                                    "subagent": subagent_name,
                                    "description": self._get_subagent_description(subagent_name)
                                }

                            # Process subagent node updates
                            for node_name, node_data in update_data.items():
                                if node_name == "tools":
                                    for msg in node_data.get("messages", []):
                                        msg_type = getattr(msg, "type", "")
                                        if msg_type == "tool":
                                            msg_name = getattr(msg, "name", "")
                                            msg_args = getattr(getattr(msg, 'args', None), '__dict__', {}).__str__() if hasattr(getattr(msg, 'args', None), '__dict__') else str(getattr(msg, 'args', {}))
                                            yield {
                                                "type": "tool_call",
                                                "tool": msg_name,
                                                "args": msg_args[:500] if msg_args else "",
                                                "source": subagent_name
                                            }
                                        elif msg_type == "ai":
                                            # Subagent is generating content
                                            yield {
                                                "type": "subagent_progress",
                                                "subagent": subagent_name,
                                                "status": f"Running {node_name}",
                                                "progress": None
                                            }

                    elif chunk.get("type") == "messages":
                        # Handle token streaming
                        message_data = chunk.get("data")
                        if message_data:
                            msg, metadata = message_data

                            # Check if this is a content token
                            if hasattr(msg, 'content') and msg.content:
                                # Determine source from metadata
                                source = metadata.get('langgraph_node', 'main')

                                # If this is from a subagent, extract the subagent name
                                namespace = chunk.get("ns", [])
                                if namespace:
                                    source = namespace[0]

                                yield {
                                    "type": "token_delta",
                                    "content": msg.content,
                                    "source": source
                                }

                                # Accumulate content for final message
                                accumulated_content += msg.content

            # Final completion message
            if current_subagent:
                yield {
                    "type": "subagent_completed",
                    "subagent": current_subagent,
                    "duration": time.time() - subagent_start_time
                }

            yield {
                "type": "stream_complete",
                "content": accumulated_content,
                "tool_calls": tool_calls,
            }

        except Exception as e:
            logger.exception("Error in chat stream")
            yield {
                "type": "error",
                "content": str(e)
            }
        finally:
            clear_current_user_id()

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

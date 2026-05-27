"""
Chat Agent — Deep Agents-based conversational AI assistant.

Provides a simple chat interface with tools for querying system data
and executing actions with proper permission checks.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, messages_from_dict
from langgraph.checkpoint.memory import MemorySaver
from deepagents import create_deep_agent

from app.core.agent_config import get_llm
from app.agent_tools.tool_context import set_current_user_id, clear_current_user_id
from app.agents.subagents import (
    get_test_query_subagent,
    get_user_admin_subagent,
    get_test_reviewer_subagent,
    get_analytics_subagent,
)

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Short-term memory for chat conversations."""

    def __init__(self, max_messages: int = 20):
        """Initialize conversation memory.

        Args:
            max_messages: Maximum number of messages to keep in memory
        """
        self.max_messages = max_messages
        self.user_profile: Dict[str, Any] = {}
        self.key_facts: List[str] = []
        self.last_summary: Optional[str] = None
        self.message_count = 0

    def add_fact(self, fact: str):
        """Add a key fact to memory."""
        if fact and fact not in self.key_facts:
            self.key_facts.append(fact)
            logger.info(f"[MEMORY] Added fact: {fact[:50]}...")

    def update_profile(self, key: str, value: Any):
        """Update user profile information."""
        self.user_profile[key] = value
        logger.info(f"[MEMORY] Updated profile: {key} = {value}")

    def extract_info(self, text: str):
        """Extract key information from user message."""
        text_lower = text.lower()

        # Extract name (patterns like "I am X", "My name is X", "Call me X")
        name_patterns = [
            r"(?:i am|i'm|my name is|call me)\s+([a-zA-Z]+)",
            r"(?:我是|叫我)\s*([a-zA-Z一-龥]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if name and len(name) > 1 and len(name) < 50:
                    self.update_profile("name", name)
                    self.add_fact(f"User's name is {name}")

        # Extract preferences
        if any(word in text_lower for word in ["prefer", "like", "want", "need"]):
            self.add_fact(f"User preference: {text[:100]}")

        # Extract project/work context
        if any(word in text_lower for word in ["project", "working on", "testing"]):
            self.add_fact(f"Work context: {text[:100]}")

    def get_memory_context(self) -> str:
        """Get memory context for system prompt."""
        context_parts = []

        if self.user_profile:
            context_parts.append("**User Profile:**")
            for key, value in self.user_profile.items():
                context_parts.append(f"- {key}: {value}")

        if self.key_facts:
            context_parts.append("**Key Facts from Conversation:**")
            context_parts.extend([f"- {fact}" for fact in self.key_facts[-5:]])

        return "\n".join(context_parts) if context_parts else ""


class ChatAgent:
    """Conversational AI assistant for the E2E testing platform."""

    def __init__(self):
        """Initialize the chat agent using deepagents framework with compiled subagents."""
        self.checkpointer = MemorySaver()

        # Get LLM configuration from settings
        llm = get_llm(temperature=0.7, max_tokens=4096)

        # Per-user memory storage (keyed by user_id)
        self.user_memories: Dict[int, ConversationMemory] = {}

        # Create deep agent with specialized compiled subagents
        self.agent = create_deep_agent(
            model=llm,
            checkpointer=self.checkpointer,
            system_prompt=self._get_system_prompt(),
            subagents=[
                get_test_query_subagent(llm),
                get_user_admin_subagent(llm),
                get_test_reviewer_subagent(llm),
                get_analytics_subagent(llm),
            ],
            debug=True,
        )

        logger.info("Chat agent initialized with deepagents framework and 4 compiled subagents")

    def _get_memory(self, user_id: int) -> ConversationMemory:
        """Get or create conversation memory for a user."""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = ConversationMemory()
        return self.user_memories[user_id]

    def _get_system_prompt(self, memory_context: str = "") -> str:
        """Get the system prompt for the chat agent."""
        base_prompt = """You are an AI assistant for the E2E testing platform. You coordinate specialized subagents to help users with various tasks.

**Your Role:**
You are the main coordinator that routes user requests to appropriate specialized subagents using the `task` tool.

**How to Work:**
1. Analyze the user's request and delegate to the appropriate subagent
2. When multiple subagents are needed, coordinate them sequentially
3. Synthesize the subagent results into a helpful, human-readable response

**Memory & Context:**
Remember important information the user shares (name, preferences, project details). Use this context to provide personalized responses.

**Response Guidelines:**
- Don't just repeat the subagent output - explain it in context
- For actions requiring permissions, ensure the subagent explains what will happen first
- When a user lacks permission, explain the requirement clearly
- Be concise but thorough"""

        if memory_context:
            return f"""{base_prompt}

**Conversation Context:**
{memory_context}

Use this context to provide personalized and contextual responses."""

        return base_prompt

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

            # Get or create memory for this user
            memory = self._get_memory(user_id)

            # Extract information from user message
            memory.extract_info(message)
            memory.message_count += 1

            # Set the user context for tools
            set_current_user_id(user_id)

            # Get memory context and update system prompt if needed
            memory_context = memory.get_memory_context()
            if memory_context:
                print(f"[CHAT DEBUG] Using memory context with {len(memory.user_profile)} profile fields and {len(memory.key_facts)} facts")

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

            print(f"[CHAT DEBUG] Invoking Agent with user_id={user_id}, thread_id={thread_id}")

            # Invoke the deep agent
            result = await self.agent.ainvoke(agent_input, config=config)

            print(f"[CHAT DEBUG] Agent invocation completed")

            # Extract the last AI message content (not ToolMessage)
            messages = result.get("messages", [])
            response_content = None
            tool_result_content = None

            # Debug: Log all messages with full details
            print(f"[CHAT DEBUG] Total messages: {len(messages)}")
            for i, msg in enumerate(messages):
                msg_type = getattr(msg, "type", "") or type(msg).__name__
                content = getattr(msg, "content", "")
                content_preview = content[:50] if content else ""
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
                    if not content_stripped:
                        print(f"[CHAT DEBUG] Skipping empty message")
                        continue

                    # Skip human messages (don't return user's own message as response)
                    if msg_type == "human":
                        print(f"[CHAT DEBUG] Skipping human message in response search")
                        continue

                    # Found the response (accept any non-empty AI content)
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

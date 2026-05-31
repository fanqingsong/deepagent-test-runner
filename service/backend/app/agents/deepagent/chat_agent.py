"""
Chat Agent — Deep Agents-based conversational AI assistant.

Provides a simple chat interface with tools for querying system data
and executing actions with proper permission checks.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.config import get_config
from langgraph.store.memory import InMemoryStore
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends.utils import create_file_data

from app.core.agent_config import get_llm
from app.core.config import settings
from app.agents.deepagent.subagents import (
    get_test_query_subagent,
    get_user_admin_subagent,
    get_test_reviewer_subagent,
    get_analytics_subagent,
    get_search_subagent,
    get_email_subagent,
)

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def _load_skills_files_sync() -> dict:
    """Load skill files from disk into StateBackend format (blocking I/O)."""
    files = {}
    if not SKILLS_DIR.is_dir():
        logger.warning("Skills directory not found: %s", SKILLS_DIR)
        return files
    for skill_dir in sorted(d for d in SKILLS_DIR.iterdir() if d.is_dir()):
        for fpath in sorted(skill_dir.rglob("*")):
            if not fpath.is_file():
                continue
            rel = fpath.relative_to(SKILLS_DIR).as_posix()
            key = f"/skills/{rel}"
            files[key] = create_file_data(fpath.read_text(encoding="utf-8"))
    return files


async def _load_skills_files() -> dict:
    """Async wrapper — runs blocking I/O in a thread."""
    return await asyncio.to_thread(_load_skills_files_sync)


def _get_checkpointer_conn_string() -> str:
    """Build a psycopg connection string from async DATABASE_URL."""
    # DATABASE_URL: postgresql+asyncpg://user:pass@host:port/db
    url = settings.DATABASE_URL
    url = url.replace("+asyncpg", "")
    return url


class ChatAgent:
    """Conversational AI assistant for the E2E testing platform."""

    def __init__(self):
        """Initialize the chat agent (checkpointer set up lazily in _ensure_store)."""
        self.checkpointer: AsyncPostgresSaver | None = None
        self._store: InMemoryStore | None = None
        self._ready = False
        self._agent = None

    async def _ensure_store(self):
        """Lazily initialize the PostgreSQL checkpointer and in-memory store."""
        if self._ready:
            return

        from contextlib import AsyncExitStack

        llm = get_llm(temperature=0.7, max_tokens=8192)
        conn_string = _get_checkpointer_conn_string()

        self._exit_stack = AsyncExitStack()
        await self._exit_stack.__aenter__()

        self.checkpointer = await self._exit_stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(conn_string)
        )
        await self.checkpointer.setup()

        self._store = InMemoryStore()

        skills_files = await _load_skills_files()
        for key, data in skills_files.items():
            self._store.put(
                namespace=("skills", "shared"),
                key=key,
                value=data,
            )

        skills_backend = StoreBackend(
            store=self._store,
            namespace=lambda _rt: ("skills", "shared"),
        )

        self._agent = create_deep_agent(
            model=llm,
            checkpointer=self.checkpointer,
            system_prompt=self._get_system_prompt(),
            memory=["/memories/AGENTS.md"],
            skills=["/skills/"],
            backend=CompositeBackend(
                default=StateBackend(),
                routes={
                    "/skills/": skills_backend,
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
                get_email_subagent(llm),
            ],
            debug=True,
        )
        self._agent.store = self._store
        self._skills_files = skills_files

        if skills_files:
            logger.info("Loaded %d skill files into StoreBackend", len(skills_files))

        self._ready = True

        logger.info("Chat agent initialized with PostgreSQL checkpointer")

    @property
    def agent(self):
        if self._agent is None:
            raise RuntimeError("ChatAgent not initialized — call _ensure_store() first")
        return self._agent

    @property
    def skills_files(self) -> dict:
        """Skill files for seeding the StateBackend on first invoke."""
        if not self._ready:
            raise RuntimeError("ChatAgent not initialized — call _ensure_store() first")
        return self._skills_files

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
            "email": "Sending emails and querying email history",
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

"""
Chat Session Tracker Callback

Lightweight LangChain callback that updates chat_sessions metadata
on every LLM call. Uses fire-and-forget asyncio tasks so it never
blocks the user's response path.
"""

import asyncio
import logging
import uuid
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.llm_context import agent_type_ctx, thread_id_ctx, user_id_ctx

logger = logging.getLogger(__name__)


class ChatSessionTracker(BaseCallbackHandler):
    """Fire-and-forget tracker that updates chat_sessions metadata."""

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        thread_id = thread_id_ctx.get()
        user_id = user_id_ctx.get()
        agent_type = agent_type_ctx.get()

        # Fall back to LangGraph's runtime config when context vars aren't set
        if not thread_id:
            try:
                from langgraph.config import get_config
                config = get_config()
                configurable = config.get("configurable", {})
                thread_id = configurable.get("thread_id")
                if not user_id:
                    user_id = configurable.get("user_id")
            except Exception:
                pass

        if not thread_id:
            return

        asyncio.create_task(
            self._update_session(thread_id, user_id, agent_type)
        )

    async def _update_session(
        self,
        thread_id: str,
        user_id: int | None,
        agent_type: str | None,
    ) -> None:
        try:
            from app.services.chat_session_service import chat_session_service
            from app.core.database import async_session_maker

            async with async_session_maker() as db:
                if user_id:
                    await chat_session_service.upsert_session(
                        db, thread_id, user_id
                    )
                if agent_type and agent_type != "unknown":
                    await chat_session_service.record_subagent(
                        db, thread_id, agent_type
                    )
        except Exception:
            logger.warning(
                "Failed to update chat session for thread %s",
                thread_id, exc_info=True,
            )


_chat_session_tracker = ChatSessionTracker()

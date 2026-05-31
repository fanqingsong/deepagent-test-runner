"""
LangChain callback handler that captures token usage from every LLM call
and persists it to the llm_usage PostgreSQL table.
"""

import logging
import time
import uuid
from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.core.llm_context import agent_type_ctx, test_run_id_ctx, user_id_ctx

logger = logging.getLogger(__name__)


def _get_session_factory():
    """Return the appropriate async session factory for the current context."""
    from app.core.worker_db import _active_session_maker

    if _active_session_maker is not None:
        return _active_session_maker
    from app.core.database import async_session_maker

    return async_session_maker


class LlmUsageCallbackHandler(BaseCallbackHandler):
    """Captures token usage from each LLM call and persists to PostgreSQL."""

    def __init__(self):
        self._start_times: dict[str, float] = {}

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: Sequence[str],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        self._start_times[str(run_id)] = time.monotonic()

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        run_id_str = str(run_id)
        start = self._start_times.pop(run_id_str, None)
        duration_ms = int((time.monotonic() - start) * 1000) if start else 0

        usage: dict[str, int] = {}
        model_name = ""
        try:
            gen = response.generations[0][0]
            msg = getattr(gen, "message", None)
            if msg and hasattr(msg, "usage_metadata") and msg.usage_metadata:
                usage = msg.usage_metadata
            if response.llm_output:
                model_name = response.llm_output.get("model_name", "")
                if not usage:
                    usage = response.llm_output.get("token_usage", {})
        except (IndexError, AttributeError):
            pass

        prompt_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        completion_tokens = usage.get("output_tokens", usage.get("completion_tokens", 0))
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        if total_tokens == 0:
            logger.debug("Skipping LLM usage record with zero tokens for run %s", run_id_str)
            return

        agent_type = agent_type_ctx.get() or "unknown"
        user_id = user_id_ctx.get()
        test_run_id = test_run_id_ctx.get()

        await self._persist(
            agent_type=agent_type,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            user_id=user_id,
            test_run_id=test_run_id,
        )

    async def _persist(self, **kwargs):
        try:
            from app.models.llm_usage import LlmUsage

            factory = _get_session_factory()
            async with factory() as session:
                record = LlmUsage(**kwargs)
                session.add(record)
                await session.commit()
        except Exception:
            logger.warning("Failed to persist LLM usage record", exc_info=True)


_usage_callback = LlmUsageCallbackHandler()

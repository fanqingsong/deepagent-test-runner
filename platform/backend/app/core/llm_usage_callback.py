"""
LangChain callback handler that captures token usage from every LLM call,
persists it to the llm_usage PostgreSQL table, and integrates with token services.
"""

import logging
import time
import uuid
from collections.abc import Sequence
from typing import Any, Optional, Dict, TYPE_CHECKING

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_context import agent_type_ctx, test_run_id_ctx, thread_id_ctx, user_id_ctx
from app.core.llm.token_estimator import TokenEstimator

if TYPE_CHECKING:
    from app.services.token_budget_service import TokenBudgetService
    from app.services.token_quota_service import TokenQuotaService

logger = logging.getLogger(__name__)


def _get_session_factory():
    """Return the appropriate async session factory for the current context."""
    from app.core.worker_db import _active_session_maker

    if _active_session_maker is not None:
        return _active_session_maker
    from app.core.database import async_session_maker

    return async_session_maker


class LlmUsageCallbackHandler(BaseCallbackHandler):
    """
    Captures token usage from each LLM call and persists to PostgreSQL.

    Enhanced with token service integration for budget and quota tracking.
    """

    def __init__(
        self,
        token_budget_service: Optional['TokenBudgetService'] = None,
        token_quota_service: Optional['TokenQuotaService'] = None,
        enable_token_estimation: bool = True
    ):
        """
        Initialize callback handler.

        Args:
            token_budget_service: Optional token budget service
            token_quota_service: Optional token quota service
            enable_token_estimation: Whether to estimate tokens pre-call
        """
        self._start_times: dict[str, float] = {}
        self._token_budget_service = token_budget_service
        self._token_quota_service = token_quota_service
        self._enable_token_estimation = enable_token_estimation
        self._token_estimator = TokenEstimator() if enable_token_estimation else None
        self._db_session: Optional[AsyncSession] = None

    def set_db_session(self, session: AsyncSession):
        """Set database session for token services."""
        self._db_session = session

    async def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: Sequence[str],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts. Records start time and optionally estimates tokens."""
        run_id_str = str(run_id)
        self._start_times[run_id_str] = time.monotonic()

        # Pre-call token estimation
        if self._enable_token_estimation and self._token_estimator:
            try:
                # Combine all prompts
                combined_prompt = "\n".join(prompts)

                # Estimate tokens
                estimated_tokens = self._token_estimator.estimate_tokens_from_text(
                    combined_prompt,
                    model="glm-4-plus"  # Default model
                )

                logger.debug(f"Pre-call token estimation: {estimated_tokens} tokens for run {run_id_str}")

                # Could integrate with budget/quota services here if needed
                # This would require scope_type, scope_id, user_id from context

            except Exception as e:
                logger.warning(f"Failed to estimate tokens for run {run_id_str}: {e}")

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        """Called when LLM ends. Persists usage and optionally records to token services."""
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
        thread_id = thread_id_ctx.get()

        # Persist to database
        await self._persist(
            agent_type=agent_type,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            duration_ms=duration_ms,
            user_id=user_id,
            test_run_id=test_run_id,
            thread_id=thread_id,
        )

        # Record to token services if available
        await self._record_to_token_services(
            total_tokens=total_tokens,
            model_name=model_name,
            user_id=user_id,
            test_run_id=test_run_id,
            agent_type=agent_type,
            duration_ms=duration_ms
        )

    async def _persist(self, **kwargs):
        """Persist usage record to database."""
        try:
            from app.models.llm_usage import LlmUsage

            factory = _get_session_factory()
            async with factory() as session:
                record = LlmUsage(**kwargs)
                session.add(record)
                await session.commit()
        except Exception:
            logger.warning("Failed to persist LLM usage record", exc_info=True)

    async def _record_to_token_services(
        self,
        total_tokens: int,
        model_name: str,
        user_id: Optional[int],
        test_run_id: Optional[int],
        agent_type: str,
        duration_ms: int
    ):
        """Record token usage to budget and quota services if available."""
        try:
            # Determine scope from context
            scope_type = None
            scope_id = None

            # If we have a test_run_id, use test scope
            if test_run_id:
                scope_type = "test"
                scope_id = test_run_id

            # Use provided session or create new one
            if self._db_session:
                db = self._db_session
            else:
                factory = _get_session_factory()
                async with factory() as db:
                    await self._do_record_to_services(
                        total_tokens=total_tokens,
                        model_name=model_name,
                        user_id=user_id,
                        test_run_id=test_run_id,
                        agent_type=agent_type,
                        duration_ms=duration_ms,
                        scope_type=scope_type,
                        scope_id=scope_id,
                        db=db
                    )
                return

            await self._do_record_to_services(
                total_tokens=total_tokens,
                model_name=model_name,
                user_id=user_id,
                test_run_id=test_run_id,
                agent_type=agent_type,
                duration_ms=duration_ms,
                scope_type=scope_type,
                scope_id=scope_id,
                db=db
            )

        except Exception as e:
            logger.warning(f"Failed to record to token services: {e}")

    async def _do_record_to_services(
        self,
        total_tokens: int,
        model_name: str,
        user_id: Optional[int],
        test_run_id: Optional[int],
        agent_type: str,
        duration_ms: int,
        scope_type: Optional[str],
        scope_id: Optional[int],
        db: AsyncSession
    ):
        """Actually record to the services."""
        # Record budget usage
        if self._token_budget_service and scope_type and scope_id:
            try:
                await self._token_budget_service.record_token_usage(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    tokens_used=total_tokens,
                    db=db,
                    metadata={
                        "model": model_name,
                        "agent_type": agent_type,
                        "test_run_id": test_run_id,
                        "duration_ms": duration_ms
                    }
                )
                logger.debug(f"Recorded {total_tokens} tokens to budget {scope_type}:{scope_id}")
            except Exception as e:
                logger.warning(f"Failed to record to budget service: {e}")

        # Record quota usage
        if self._token_quota_service and user_id:
            try:
                await self._token_quota_service.record_quota_usage(
                    user_id=user_id,
                    tokens_used=total_tokens,
                    db=db,
                    metadata={
                        "model": model_name,
                        "agent_type": agent_type,
                        "test_run_id": test_run_id,
                        "duration_ms": duration_ms
                    }
                )
                logger.debug(f"Recorded {total_tokens} tokens to quota for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to record to quota service: {e}")


_usage_callback = LlmUsageCallbackHandler()

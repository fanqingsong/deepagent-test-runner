"""
Retry Middleware for deepagents — automatic retry on rate limits and transient errors.

Wraps model and tool calls with exponential backoff to handle 429 rate-limit
errors and other transient failures gracefully.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable

from deepagents.middleware.filesystem import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)

from langchain_core.messages import ToolMessage

logger = logging.getLogger(__name__)


class ModelRetryMiddleware(AgentMiddleware):
    """Retry model calls on rate-limit (429), timeout, and 5xx errors.

    Args:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Multiplier for exponential backoff (seconds).
        initial_delay: Initial delay before first retry (seconds).
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await handler(request)
            except Exception as e:
                last_error = e
                if not _is_retryable_model_error(e):
                    raise
                if attempt >= self.max_retries:
                    logger.error(
                        "ModelRetryMiddleware: exhausted %d retries for model call: %s",
                        self.max_retries, e,
                    )
                    raise
                delay = self.initial_delay * (self.backoff_factor ** attempt)
                logger.warning(
                    "ModelRetryMiddleware: attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt + 1, self.max_retries, type(e).__name__, delay,
                )
                await asyncio.sleep(delay)
        raise last_error  # unreachable, but satisfies type checkers


class ToolRetryMiddleware(AgentMiddleware):
    """Retry specific tool calls on transient errors.

    Args:
        max_retries: Maximum number of retry attempts.
        tools: Tool names to wrap. If empty, wraps all tools.
        retry_on: Exception types that trigger a retry.
        backoff_factor: Multiplier for exponential backoff (seconds).
        initial_delay: Initial delay before first retry (seconds).
    """

    def __init__(
        self,
        max_retries: int = 2,
        tools: list[str] | None = None,
        retry_on: tuple[type[Exception], ...] = (TimeoutError, ConnectionError),
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
    ) -> None:
        self.max_retries = max_retries
        self.tool_names = set(tools) if tools else None
        self.retry_on = retry_on
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage]],
    ) -> ToolMessage:
        tool_name = request.tool_call["name"]

        if self.tool_names and tool_name not in self.tool_names:
            return await handler(request)

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await handler(request)
            except self.retry_on as e:
                last_error = e
                if attempt >= self.max_retries:
                    logger.error(
                        "ToolRetryMiddleware: exhausted %d retries for tool '%s': %s",
                        self.max_retries, tool_name, e,
                    )
                    raise
                delay = self.initial_delay * (self.backoff_factor ** attempt)
                logger.warning(
                    "ToolRetryMiddleware: attempt %d/%d for tool '%s' failed (%s), retrying in %.1fs",
                    attempt + 1, self.max_retries, tool_name, type(e).__name__, delay,
                )
                await asyncio.sleep(delay)
            except Exception:
                raise
        raise last_error  # unreachable


def _is_retryable_model_error(error: Exception) -> bool:
    """Check if a model call error is worth retrying."""
    error_str = str(error).lower()
    if "429" in error_str or "rate" in error_str or "速率限制" in error_str:
        return True
    if any(code in error_str for code in ("500", "502", "503", "504")):
        return True
    if "timeout" in error_str or "timed out" in error_str:
        return True
    try:
        import openai
        if isinstance(error, openai.RateLimitError):
            return True
        if isinstance(error, (openai.APITimeoutError, openai.APIConnectionError)):
            return True
        if isinstance(error, openai.InternalServerError):
            return True
    except ImportError:
        pass
    return False

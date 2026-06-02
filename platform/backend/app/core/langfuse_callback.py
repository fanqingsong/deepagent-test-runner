"""
Langfuse callback handler for LangChain/LangGraph tracing.

Lazily initialized — only creates the handler when LANGFUSE_PUBLIC_KEY
and LANGFUSE_SECRET_KEY are both set. Otherwise returns a no-op placeholder.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_placeholder_sentinel = object()


class _NoopHandler:
    """Fallback when Langfuse is not configured — accepts all callback methods as no-ops."""

    def __getattr__(self, name: str) -> Any:
        return lambda *a, **kw: None


_handler = _placeholder_sentinel


def get_langfuse_handler():
    """Return the Langfuse CallbackHandler (lazy singleton)."""
    global _handler
    if _handler is not _placeholder_sentinel:
        return _handler

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000").strip()

    if not public_key or not secret_key:
        logger.info("Langfuse not configured (missing keys), tracing disabled")
        _handler = _NoopHandler()
        return _handler

    try:
        from langfuse.langchain import CallbackHandler

        _handler = CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        logger.info("Langfuse callback handler initialized (host=%s)", host)
    except Exception:
        logger.warning("Failed to initialize Langfuse handler, tracing disabled", exc_info=True)
        _handler = _NoopHandler()

    return _handler


# Module-level instance for convenient import
langfuse_handler = get_langfuse_handler()

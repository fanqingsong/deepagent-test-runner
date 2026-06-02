"""
Context variables for propagating LLM usage metadata through the call stack.

Used by LlmUsageCallbackHandler to associate each LLM call with its
agent type, user, and test run — without modifying function signatures.
"""

from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Optional

agent_type_ctx: ContextVar[Optional[str]] = ContextVar("agent_type", default=None)
user_id_ctx: ContextVar[Optional[int]] = ContextVar("user_id", default=None)
test_run_id_ctx: ContextVar[Optional[str]] = ContextVar("test_run_id", default=None)


@asynccontextmanager
async def llm_usage_context(agent_type: str, user_id: int = None, test_run_id: str = None):
    tokens = [
        agent_type_ctx.set(agent_type),
        user_id_ctx.set(user_id),
        test_run_id_ctx.set(test_run_id),
    ]
    try:
        yield
    finally:
        for t in tokens:
            t.var.reset(t)

"""
Test Runner DeepAgent — singleton dispatcher.

Thin dispatcher that delegates script generation to the specialized subagent.
Stateless service: no checkpointer, no user-specific storage.
"""

import asyncio
import logging
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import StateBackend

from app.agents.chat_assistant.retry_middleware import ModelRetryMiddleware
from app.core.agent_config import get_llm

from .tools import get_test_results
from .subagents import get_script_generator_subagent

logger = logging.getLogger(__name__)

DISPATCHER_SYSTEM_PROMPT = """You are a test automation coordinator. You have a specialized subagent:

1. **script-generator** — Generates Playwright test scripts with full orchestration (page fetch, generate, validate, execute, retry, save).

Delegate script generation tasks to the script-generator subagent.
You also have a tool to retrieve test results from the database."""

_agent_instance = None
_lock = asyncio.Lock()


async def get_test_runner_agent() -> Any:
    """Get or create the singleton Test Runner DeepAgent (dispatcher)."""
    global _agent_instance
    if _agent_instance is not None:
        return _agent_instance

    async with _lock:
        if _agent_instance is not None:
            return _agent_instance

        llm = get_llm(temperature=0.3, max_tokens=4096)

        _agent_instance = create_deep_agent(
            model=llm,
            system_prompt=DISPATCHER_SYSTEM_PROMPT,
            tools=[get_test_results],
            middleware=[
                ModelRetryMiddleware(max_retries=3, backoff_factor=2.0, initial_delay=1.0),
            ],
            subagents=[
                get_script_generator_subagent(llm),
            ],
            backend=StateBackend(),
        )

        logger.info("Test Runner DeepAgent (dispatcher) initialized")
        return _agent_instance

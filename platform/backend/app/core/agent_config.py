"""
Agent Configuration — LLM factory for LangGraph agents.

Uses ChatOpenAI with GLM's OpenAI-compatible API endpoint.
Supports any OpenAI-compatible LLM provider via base_url override.
"""

import os
from typing import Optional

from langchain_openai import ChatOpenAI

from app.core.llm_usage_callback import _usage_callback
from app.core.langfuse_callback import langfuse_handler


def get_llm(
    model_name: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 4096,
    timeout: float = 120.0,
) -> ChatOpenAI:
    """Create LLM instance — supports GLM via OpenAI-compatible API."""
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY is required. Set it in .env or environment.")

    from langchain_core.callbacks import BaseCallbackHandler
    callbacks = []
    if isinstance(_usage_callback, BaseCallbackHandler):
        callbacks.append(_usage_callback)
    if isinstance(langfuse_handler, BaseCallbackHandler):
        callbacks.append(langfuse_handler)

    return ChatOpenAI(
        model=model_name or os.getenv("LLM_MODEL", "glm-4-plus"),
        base_url=os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        callbacks=callbacks or None,
    )

"""
LLM Client Implementations

This package provides implementations of the ILLMClient interface.

Implementations:
- GLMClient: Production implementation for GLM (BigModel) API
- MockLLMClient: Mock implementation for testing

Usage:
    from app.core.llm.glm_client import GLMClient
    from app.core.llm.mock_llm_client import MockLLMClient
"""

from app.core.llm.glm_client import GLMClient
from app.core.llm.mock_llm_client import MockLLMClient

__all__ = [
    "GLMClient",
    "MockLLMClient",
]

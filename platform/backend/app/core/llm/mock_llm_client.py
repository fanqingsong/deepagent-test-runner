"""
Mock LLM Client Implementation

Provides a mock implementation of ILLMClient for testing purposes.
Supports deterministic responses, configurable delays, and error simulation.
"""

import asyncio
import logging
from typing import AsyncIterator, Dict, Any, Optional, List
from datetime import datetime

from app.core.interfaces.llm_client_interface import (
    ILLMClient,
    LLMResponse,
    LLMMessage,
    LLMStreamChunk,
    LLMClientException,
    LLMTimeoutError,
    LLMValidationError,
    LLMRateLimitError,
    LLMTokenLimitError
)


logger = logging.getLogger(__name__)


class MockLLMClient(ILLMClient):
    """
    Mock LLM client for testing.

    Provides deterministic responses without calling external APIs.
    Useful for unit tests and integration tests.
    """

    def __init__(
        self,
        model: str = "mock-model",
        delay_ms: int = 100,
        simulate_errors: bool = False,
        response_mode: str = "deterministic"
    ):
        """
        Initialize mock LLM client.

        Args:
            model: Mock model name
            delay_ms: Artificial delay in milliseconds
            simulate_errors: Whether to simulate errors randomly
            response_mode: Response generation mode
                - "deterministic": Always return the same response
                - "echo": Echo back the prompt
                - "template": Use response templates
        """
        self.model = model
        self.delay_ms = delay_ms
        self.simulate_errors = simulate_errors
        self.response_mode = response_mode

        # Response templates
        self._response_templates = {
            "test_case": """
# Test Case: User Login Flow

## Test Steps:
1. Navigate to login page
2. Enter valid username and password
3. Click login button
4. Verify user is redirected to dashboard
5. Verify welcome message is displayed

## Expected Results:
- User should be successfully logged in
- Dashboard should be accessible
- Welcome message should show correct username
            """,
            "validation": "Script validation passed successfully",
            "generation": "Generated content based on your requirements",
            "error": "Simulated error response",
        }

        # Model information
        self._model_info = {
            "name": self.model,
            "max_tokens": 128000,
            "provider": "Mock",
            "description": "Mock LLM for testing",
            "supports_streaming": True,
            "supports_structured": True,
        }

    async def _simulate_delay(self):
        """Simulate API delay."""
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000.0)

    def _maybe_simulate_error(self):
        """Simulate random errors if enabled."""
        if not self.simulate_errors:
            return

        import random
        error_type = random.random()

        if error_type < 0.1:  # 10% chance of timeout
            raise LLMTimeoutError("Mock timeout error", provider="Mock")
        elif error_type < 0.2:  # 10% chance of validation error
            raise LLMValidationError("Mock validation error", provider="Mock")
        elif error_type < 0.25:  # 5% chance of rate limit
            raise LLMRateLimitError("Mock rate limit error", provider="Mock")
        elif error_type < 0.275:  # 2.5% chance of token limit
            raise LLMTokenLimitError(
                "Mock token limit error",
                token_limit=128000,
                provider="Mock"
            )

    def _generate_response(self, prompt: str) -> str:
        """Generate deterministic response based on prompt."""
        if self.response_mode == "echo":
            return f"Echo: {prompt}"

        # Determine response type based on prompt content
        prompt_lower = prompt.lower()

        if "test case" in prompt_lower or "test" in prompt_lower:
            return self._response_templates["test_case"].strip()
        elif "validation" in prompt_lower or "validate" in prompt_lower:
            return self._response_templates["validation"]
        elif "generate" in prompt_lower or "generation" in prompt_lower:
            return self._response_templates["generation"]
        else:
            # Generic response
            return f"Mock response for: {prompt[:50]}..."

    async def generate_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a mock response.

        Args:
            prompt: Input prompt
            model: Model name (ignored)
            temperature: Temperature (ignored)
            max_tokens: Max tokens (ignored)
            **kwargs: Additional parameters (ignored)

        Returns:
            LLMResponse: Mock response
        """
        if not prompt or not prompt.strip():
            raise LLMValidationError("Prompt cannot be empty", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error()

        # Generate response content
        content = self._generate_response(prompt)

        # Estimate tokens
        input_tokens = self.estimate_tokens(prompt)
        output_tokens = self.estimate_tokens(content)
        total_tokens = input_tokens + output_tokens

        logger.debug(f"Mock LLM response: {len(content)} chars, {total_tokens} tokens")

        return LLMResponse(
            content=content,
            model=model or self.model,
            tokens_used=total_tokens,
            duration_ms=self.delay_ms,
            finish_reason="stop",
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "provider": "Mock",
                "mock": True
            }
        )

    async def generate_chat_response(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a mock chat response.

        Args:
            messages: List of conversation messages
            model: Model name (ignored)
            temperature: Temperature (ignored)
            max_tokens: Max tokens (ignored)
            **kwargs: Additional parameters (ignored)

        Returns:
            LLMResponse: Mock chat response
        """
        if not messages:
            raise LLMValidationError("Messages list cannot be empty", provider="Mock")

        await self._simulate_delay()
        self._maybe_simulate_error()

        # Combine messages into a single prompt
        combined_prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
        content = self._generate_response(combined_prompt)

        # Estimate tokens
        prompt_text = "\n".join([msg.content for msg in messages])
        input_tokens = self.estimate_tokens(prompt_text)
        output_tokens = self.estimate_tokens(content)
        total_tokens = input_tokens + output_tokens

        logger.debug(f"Mock LLM chat response: {len(content)} chars, {total_tokens} tokens")

        return LLMResponse(
            content=content,
            model=model or self.model,
            tokens_used=total_tokens,
            duration_ms=self.delay_ms,
            finish_reason="stop",
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "provider": "Mock",
                "mock": True,
                "conversation_length": len(messages)
            }
        )

    async def generate_structured_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a mock structured response.

        Args:
            prompt: Input prompt
            schema: JSON schema for response structure
            model: Model name (ignored)
            temperature: Temperature (ignored)
            max_tokens: Max tokens (ignored)
            **kwargs: Additional parameters (ignored)

        Returns:
            Dict[str, Any]: Mock structured response matching schema
        """
        await self._simulate_delay()
        self._maybe_simulate_error()

        # Generate mock data based on schema
        def generate_mock_value(value_type, description=""):
            if value_type == "string":
                if "url" in description.lower():
                    return "https://example.com"
                elif "email" in description.lower():
                    return "test@example.com"
                elif "name" in description.lower():
                    return "Test Name"
                else:
                    return "Mock string value"
            elif value_type == "integer":
                return 42
            elif value_type == "number":
                return 3.14
            elif value_type == "boolean":
                return True
            elif value_type == "array":
                return ["item1", "item2", "item3"]
            elif value_type == "object":
                return {"mock": "value"}
            else:
                return None

        # Build mock response from schema
        mock_response = {}

        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                prop_type = prop_schema.get("type", "string")
                prop_desc = prop_schema.get("description", "")
                mock_response[prop_name] = generate_mock_value(prop_type, prop_desc)

        logger.debug(f"Mock structured response: {len(mock_response)} keys")

        return mock_response

    async def stream_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        Stream a mock response.

        Args:
            prompt: Input prompt
            model: Model name (ignored)
            temperature: Temperature (ignored)
            max_tokens: Max tokens (ignored)
            **kwargs: Additional parameters (ignored)

        Yields:
            LLMStreamChunk: Response chunks
        """
        if not prompt or not prompt.strip():
            raise LLMValidationError("Prompt cannot be empty", provider="Mock")

        self._maybe_simulate_error()

        # Generate full response
        content = self._generate_response(prompt)

        # Split into chunks (simulate streaming)
        chunk_size = 20  # Small chunks for testing
        for i in range(0, len(content), chunk_size):
            await self._simulate_delay()

            chunk = content[i:i + chunk_size]
            yield LLMStreamChunk(
                content=chunk,
                is_complete=False,
                metadata={"model": model or self.model, "provider": "Mock", "mock": True}
            )

        # Send final completion chunk
        yield LLMStreamChunk(
            content="",
            is_complete=True,
            metadata={"model": model or self.model, "provider": "Mock", "mock": True}
        )

        logger.debug("Mock streaming completed")

    async def stream_chat_response(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        Stream a mock chat response.

        Args:
            messages: List of conversation messages
            model: Model name (ignored)
            temperature: Temperature (ignored)
            max_tokens: Max tokens (ignored)
            **kwargs: Additional parameters (ignored)

        Yields:
            LLMStreamChunk: Response chunks
        """
        if not messages:
            raise LLMValidationError("Messages list cannot be empty", provider="Mock")

        self._maybe_simulate_error()

        # Combine messages into a single prompt
        combined_prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
        content = self._generate_response(combined_prompt)

        # Split into chunks
        chunk_size = 20
        for i in range(0, len(content), chunk_size):
            await self._simulate_delay()

            chunk = content[i:i + chunk_size]
            yield LLMStreamChunk(
                content=chunk,
                is_complete=False,
                metadata={"model": model or self.model, "provider": "Mock", "mock": True}
            )

        # Send final completion chunk
        yield LLMStreamChunk(
            content="",
            is_complete=True,
            metadata={"model": model or self.model, "provider": "Mock", "mock": True}
        )

        logger.debug("Mock chat streaming completed")

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get mock model information."""
        return self._model_info.copy()

    def estimate_tokens(self, text: str) -> int:
        """Estimate tokens (same heuristic as GLM)."""
        if not text:
            return 0
        return int(len(text) * 0.3)

    async def health_check(self) -> bool:
        """Mock health check - always returns True."""
        await self._simulate_delay()
        logger.debug("Mock LLM health check: HEALTHY")
        return True

    def get_default_model(self) -> str:
        """Get mock model name."""
        return self.model

    def list_available_models(self) -> List[str]:
        """List available mock models."""
        return [self.model, "mock-model-2", "mock-model-3"]

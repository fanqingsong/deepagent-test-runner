"""
LLM Client Service (Refactored)

Refactored to use ILLMClient interface for flexibility.
Maintains backward compatibility with existing code.
"""

import logging
from typing import Optional

from app.core.interfaces.llm_client_interface import ILLMClient, LLMMessage
from app.core.llm.glm_client import GLMClient


logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM Client Service (Wrapper for backward compatibility).

    Wraps ILLMClient interface to maintain backward compatibility
    with existing code while using the new abstraction layer.
    """

    def __init__(
        self,
        llm_client: Optional[ILLMClient] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0,
        max_retries: int = 3
    ):
        """
        Initialize LLM client service.

        Args:
            llm_client: ILLMClient implementation (creates GLMClient if None)
            api_key: LLM API key (only used if llm_client is None)
            base_url: LLM API base URL (only used if llm_client is None)
            model: Model name (only used if llm_client is None)
            timeout: Request timeout (only used if llm_client is None)
            max_retries: Maximum retries (only used if llm_client is None)
        """
        if llm_client is not None:
            self._llm_client = llm_client
        else:
            # Create GLM client with provided parameters
            self._llm_client = GLMClient(
                api_key=api_key,
                base_url=base_url,
                model=model,
                timeout=timeout,
                max_retries=max_retries
            )

        # Expose properties for backward compatibility
        self.api_key = getattr(self._llm_client, 'api_key', None) or api_key
        self.base_url = getattr(self._llm_client, 'base_url', None) or base_url
        self.model = getattr(self._llm_client, 'model', None) or model
        self.timeout = getattr(self._llm_client, 'timeout', None) or timeout
        self.max_retries = getattr(self._llm_client, 'max_retries', None) or max_retries

    async def generate_test_case(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096
    ) -> str:
        """
        Generate test case content via LLM (backward compatible method).

        Args:
            prompt: Prompt to send to LLM
            model: Override default model
            max_tokens: Maximum tokens in response

        Returns:
            str: LLM response content

        Raises:
            ValueError: If API key is not configured
            Exception: For other errors
        """
        logger.info(f"Calling LLM API with model: {model or self.model}")

        try:
            # Use new interface
            response = await self._llm_client.generate_response(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens
            )

            # Return content for backward compatibility
            content = response.content
            logger.info(f"LLM response received, length: {len(content)}")
            return content

        except Exception as e:
            logger.error(f"Error calling LLM via new interface: {str(e)}")
            raise

    async def generate_structured_response(
        self,
        prompt: str,
        schema: dict,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        **kwargs
    ) -> dict:
        """
        Generate structured response matching JSON schema.

        Args:
            prompt: Prompt to send to LLM
            schema: JSON schema for response structure
            model: Override default model
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters

        Returns:
            dict: Structured response matching schema
        """
        logger.info(f"Calling LLM API for structured response with model: {model or self.model}")

        try:
            # Use new interface
            response = await self._llm_client.generate_structured_response(
                prompt=prompt,
                schema=schema,
                model=model,
                max_tokens=max_tokens,
                **kwargs
            )

            logger.info(f"Structured response received with {len(response)} keys")
            return response

        except Exception as e:
            logger.error(f"Error generating structured response: {str(e)}")
            raise

    async def health_check(self) -> bool:
        """
        Check if LLM API is accessible.

        Returns:
            bool: True if API is healthy
        """
        try:
            return await self._llm_client.health_check()
        except Exception as e:
            logger.error(f"LLM health check failed: {str(e)}")
            return False

    # New methods using the full interface capabilities

    async def generate_chat_response(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """
        Generate chat response from LLM.

        Args:
            messages: List of conversation messages (dicts with role/content)
            model: Override default model
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Returns:
            str: Generated response content
        """
        # Convert dict messages to LLMMessage objects
        llm_messages = [
            LLMMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", "")
            )
            for msg in messages
        ]

        response = await self._llm_client.generate_chat_response(
            messages=llm_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return response.content

    def get_model_info(self, model: str) -> dict:
        """
        Get information about a specific model.

        Args:
            model: Model name

        Returns:
            dict: Model information
        """
        return self._llm_client.get_model_info(model)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in text.

        Args:
            text: Text to estimate tokens for

        Returns:
            int: Estimated token count
        """
        return self._llm_client.estimate_tokens(text)

    def get_default_model(self) -> str:
        """Get the default model name."""
        return self._llm_client.get_default_model()

    def list_available_models(self) -> list:
        """List available model names."""
        return self._llm_client.list_available_models()

    # Property access to underlying client for advanced usage

    @property
    def client(self) -> ILLMClient:
        """Get the underlying ILLMClient instance."""
        return self._llm_client

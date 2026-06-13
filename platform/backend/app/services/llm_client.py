"""
LLM Client Service

Handles all LLM API communication with error handling, retries, and timeout management.
Uses GLM via OpenAI-compatible API.
"""

import logging
import os
from typing import Optional

import httpx

from app.core.agent_config import get_llm

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM API client for test case generation.

    Handles communication with GLM via OpenAI-compatible API,
    including error handling, retries, and timeout management.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0,
        max_retries: int = 3
    ):
        """
        Initialize LLM client.

        Args:
            api_key: LLM API key (defaults to LLM_API_KEY env var)
            base_url: LLM API base URL (defaults to LLM_BASE_URL env var)
            model: Model name (defaults to LLM_MODEL env var)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
        self.model = model or os.getenv("LLM_MODEL", "glm-4-plus")
        self.timeout = timeout
        self.max_retries = max_retries

        if not self.api_key:
            raise ValueError("LLM_API_KEY is required")

    async def generate_test_case(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096
    ) -> str:
        """
        Generate test case content via LLM.

        Args:
            prompt: Prompt to send to LLM
            model: Override default model
            max_tokens: Maximum tokens in response

        Returns:
            str: LLM response content

        Raises:
            ValueError: If API key is not configured
            httpx.HTTPError: If HTTP request fails
            Exception: For other errors
        """
        model_to_use = model or self.model

        logger.info(f"Calling LLM API with model: {model_to_use}")

        # Use LangChain get_llm for consistent configuration
        try:
            llm = get_llm(
                model_name=model_to_use,
                max_tokens=max_tokens,
                timeout=self.timeout
            )

            # Invoke the LLM
            from langchain_core.messages import HumanMessage
            response = await llm.agenerate([[HumanMessage(content=prompt)]])

            # Extract the content
            content = response.generations[0][0].text
            logger.info(f"LLM response received, length: {len(content)}")
            return content

        except Exception as e:
            logger.error(f"Error calling LLM via LangChain: {str(e)}")
            # Fallback to direct HTTP call if LangChain fails
            return await self._call_llm_direct(prompt, model_to_use, max_tokens)

    async def _call_llm_direct(
        self,
        prompt: str,
        model: str,
        max_tokens: int
    ) -> str:
        """
        Direct HTTP call to LLM API (fallback method).

        Args:
            prompt: Prompt to send
            model: Model name
            max_tokens: Maximum tokens

        Returns:
            str: LLM response content
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=data
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"Direct LLM call succeeded on attempt {attempt + 1}")
                    return content

            except httpx.TimeoutException as e:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e.response.status_code}")
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise
                if attempt == self.max_retries - 1:
                    raise

            except httpx.HTTPError as e:
                logger.error(f"HTTP error on attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}/{self.max_retries}: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise

        raise Exception(f"Failed to complete LLM call after {self.max_retries} attempts")

    async def health_check(self) -> bool:
        """
        Check if LLM API is accessible.

        Returns:
            bool: True if API is healthy
        """
        try:
            test_prompt = "Respond with 'OK' if you receive this message."
            response = await self.generate_test_case(test_prompt, max_tokens=10)
            return "OK" in response.upper()
        except Exception as e:
            logger.error(f"LLM health check failed: {str(e)}")
            return False

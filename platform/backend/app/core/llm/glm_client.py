"""
GLM LLM Client Implementation

Implements ILLMClient interface for GLM (BigModel) API.
Wraps existing LangChain ChatOpenAI integration with enhanced features.
"""

import logging
import os
import time
import asyncio
from typing import AsyncIterator, Dict, Any, Optional, List, TYPE_CHECKING
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.interfaces.llm_client_interface import (
    ILLMClient,
    LLMResponse,
    LLMMessage,
    LLMStreamChunk,
    LLMClientException,
    LLMConnectionError,
    LLMTimeoutError,
    LLMValidationError,
    LLMRateLimitError,
    LLMTokenLimitError,
    TokenCheckResult,
    EnforcementMode
)
from app.core.llm.token_estimator import TokenEstimator
from app.core.exceptions.token_exceptions import (
    TokenBudgetExceeded,
    TokenQuotaExceeded,
    TokenEstimationError
)

if TYPE_CHECKING:
    from app.services.token_budget_service import TokenBudgetService
    from app.services.token_quota_service import TokenQuotaService


logger = logging.getLogger(__name__)


class GLMClient(ILLMClient):
    """
    GLM (BigModel) LLM client implementation.

    Uses GLM's OpenAI-compatible API via LangChain ChatOpenAI.
    Supports all standard LLM operations with token tracking and streaming.
    """

    # Approximate token estimation (GLM uses similar tokenization to GPT)
    TOKENS_PER_CHAR = 0.3  # Rough estimate for English/Chinese mixed text

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 600.0,
        max_retries: int = 3,
        token_budget_service: Optional['TokenBudgetService'] = None,
        token_quota_service: Optional['TokenQuotaService'] = None,
        enforcement_mode: str = "soft",
        default_priority: int = 3
    ):
        """
        Initialize GLM client with token limitation support.

        Args:
            api_key: GLM API key (defaults to LLM_API_KEY env var)
            base_url: API base URL (defaults to LLM_BASE_URL env var)
            model: Default model name (defaults to LLM_MODEL env var)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            token_budget_service: Token budget service for budget management
            token_quota_service: Token quota service for quota management
            enforcement_mode: Token enforcement mode (hard, soft, monitoring)
            default_priority: Default priority for token checks (1-10)
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
        self.model = model or os.getenv("LLM_MODEL", "glm-4-plus")
        self.timeout = timeout
        self.max_retries = max_retries
        self.token_budget_service = token_budget_service
        self.token_quota_service = token_quota_service
        self.enforcement_mode = enforcement_mode
        self.default_priority = default_priority
        self.token_estimator = TokenEstimator()

        if not self.api_key:
            raise LLMValidationError("LLM_API_KEY is required", provider="GLM")

        # Model information
        self._model_info = {
            "glm-4-plus": {
                "name": "glm-4-plus",
                "max_tokens": 128000,
                "provider": "GLM",
                "description": "GLM-4 Plus - Most capable model",
                "supports_streaming": True,
                "supports_structured": True,
            },
            "glm-4": {
                "name": "glm-4",
                "max_tokens": 128000,
                "provider": "GLM",
                "description": "GLM-4 - Balanced model",
                "supports_streaming": True,
                "supports_structured": True,
            },
            "glm-4-flash": {
                "name": "glm-4-flash",
                "max_tokens": 128000,
                "provider": "GLM",
                "description": "GLM-4 Flash - Fast model for simple tasks",
                "supports_streaming": True,
                "supports_structured": True,
            },
        }

    def _get_llm_instance(
        self,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        timeout: Optional[float] = None
    ) -> ChatOpenAI:
        """
        Get LangChain ChatOpenAI instance configured for GLM.

        Args:
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            timeout: Request timeout

        Returns:
            ChatOpenAI: Configured LLM instance
        """
        # Lazy import to avoid circular dependency
        from app.core.agent_config import get_llm

        return get_llm(
            model_name=model or self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout or self.timeout
        )

    def _convert_messages(self, messages: List[LLMMessage]) -> List:
        """
        Convert LLMMessage objects to LangChain message format.

        Args:
            messages: List of LLMMessage objects

        Returns:
            List: LangChain message objects
        """
        langchain_messages = []
        for msg in messages:
            if msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            else:
                # Default to human message for unknown roles
                langchain_messages.append(HumanMessage(content=msg.content))

        return langchain_messages

    async def generate_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        user_id: Optional[int] = None,
        priority: Optional[int] = None,
        db: Optional[AsyncSession] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from GLM with token limitation support.

        Args:
            prompt: Input prompt
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            scope_type: Scope type for budget checks
            scope_id: Scope ID for budget checks
            user_id: User ID for quota checks
            priority: Request priority (1-10)
            db: Database session for token services
            **kwargs: Additional parameters

        Returns:
            LLMResponse: Generated response

        Raises:
            LLMValidationError: If validation fails
            LLMConnectionError: If connection fails
            LLMTimeoutError: If request times out
            TokenBudgetExceeded: If budget exceeded and enforcement is hard
            TokenQuotaExceeded: If quota exceeded and enforcement is hard
        """
        if not prompt or not prompt.strip():
            raise LLMValidationError("Prompt cannot be empty", provider="GLM")

        model_to_use = model or self.model
        priority_to_use = priority or self.default_priority

        # Pre-call token checking
        token_check = await self.check_token_availability(
            prompt=prompt,
            model=model_to_use,
            max_tokens=max_tokens,
            scope_type=scope_type,
            scope_id=scope_id,
            user_id=user_id,
            priority=priority_to_use,
            db=db
        )

        # Handle enforcement actions
        if not token_check.allowed and self.enforcement_mode == "hard":
            if token_check.budget_available and not token_check.budget_available.get("available"):
                raise TokenBudgetExceeded(
                    message=f"Token budget exceeded: {token_check.reason}",
                    budget_id=token_check.budget_available.get("budget_id"),
                    scope_type=scope_type,
                    scope_id=scope_id,
                    requested_tokens=token_check.estimated_tokens,
                    available_tokens=token_check.budget_available.get("available_tokens"),
                    enforcement_mode="hard"
                )
            elif token_check.quota_available and not token_check.quota_available.get("available"):
                raise TokenQuotaExceeded(
                    message=f"Token quota exceeded: {token_check.reason}",
                    user_id=user_id,
                    requested_tokens=token_check.estimated_tokens,
                    available_tokens=token_check.quota_available.get("available_tokens"),
                    enforcement_mode="hard"
                )

        # Handle throttling
        if token_check.enforcement_action == "throttle":
            throttle_delay = 2.0  # 2 second delay
            logger.info(f"Throttling request: {throttle_delay}s delay")
            await asyncio.sleep(throttle_delay)

        start_time = time.time()

        logger.info(f"Calling GLM API with model: {model_to_use}")

        try:
            llm = self._get_llm_instance(
                model=model_to_use,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Convert prompt to message format
            messages = [HumanMessage(content=prompt)]

            # Invoke LLM
            response = await llm.agenerate([messages])

            # Extract content and metadata
            content = response.generations[0][0].text
            duration_ms = int((time.time() - start_time) * 1000)

            # Estimate tokens
            input_tokens = self.estimate_tokens(prompt)
            output_tokens = self.estimate_tokens(content)
            total_tokens = input_tokens + output_tokens

            # Get finish reason if available
            finish_reason = getattr(response.generations[0][0], 'generation_info', {}).get('finish_reason', 'stop')

            logger.info(f"GLM response received: {len(content)} chars, {total_tokens} tokens")

            # Post-call token recording
            await self.record_token_usage(
                tokens_used=total_tokens,
                model=model_to_use,
                scope_type=scope_type,
                scope_id=scope_id,
                user_id=user_id,
                metadata={
                    "duration_ms": duration_ms,
                    "finish_reason": finish_reason,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens
                },
                db=db
            )

            return LLMResponse(
                content=content,
                model=model_to_use,
                tokens_used=total_tokens,
                duration_ms=duration_ms,
                finish_reason=finish_reason,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "provider": "GLM",
                    "token_check_result": token_check.to_dict()
                }
            )

        except TimeoutError as e:
            logger.error(f"GLM API timeout: {str(e)}")
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s", provider="GLM")

        except ConnectionError as e:
            logger.error(f"GLM API connection error: {str(e)}")
            raise LLMConnectionError(f"Failed to connect to GLM API: {str(e)}", provider="GLM")

        except Exception as e:
            logger.error(f"GLM API error: {str(e)}")
            # Check for rate limit errors
            if "rate limit" in str(e).lower() or "429" in str(e):
                raise LLMRateLimitError("Rate limit exceeded", provider="GLM")

            # Check for token limit errors
            if "token" in str(e).lower() and "limit" in str(e).lower():
                model_info = self.get_model_info(model_to_use)
                raise LLMTokenLimitError(
                    "Token limit exceeded",
                    token_limit=model_info.get("max_tokens"),
                    provider="GLM"
                )

            raise LLMClientException(f"GLM API error: {str(e)}", provider="GLM")

    async def generate_chat_response(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a chat response from GLM.

        Args:
            messages: List of conversation messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Returns:
            LLMResponse: Generated response
        """
        if not messages:
            raise LLMValidationError("Messages list cannot be empty", provider="GLM")

        model_to_use = model or self.model
        start_time = time.time()

        logger.info(f"Calling GLM chat API with model: {model_to_use}, {len(messages)} messages")

        try:
            llm = self._get_llm_instance(
                model=model_to_use,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Convert messages
            langchain_messages = self._convert_messages(messages)

            # Invoke LLM
            response = await llm.agenerate([langchain_messages])

            # Extract content and metadata
            content = response.generations[0][0].text
            duration_ms = int((time.time() - start_time) * 1000)

            # Estimate tokens
            prompt_text = "\n".join([msg.content for msg in messages])
            input_tokens = self.estimate_tokens(prompt_text)
            output_tokens = self.estimate_tokens(content)
            total_tokens = input_tokens + output_tokens

            finish_reason = getattr(response.generations[0][0], 'generation_info', {}).get('finish_reason', 'stop')

            logger.info(f"GLM chat response received: {len(content)} chars, {total_tokens} tokens")

            return LLMResponse(
                content=content,
                model=model_to_use,
                tokens_used=total_tokens,
                duration_ms=duration_ms,
                finish_reason=finish_reason,
                metadata={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "provider": "GLM",
                    "conversation_length": len(messages)
                }
            )

        except TimeoutError as e:
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s", provider="GLM")

        except ConnectionError as e:
            raise LLMConnectionError(f"Failed to connect to GLM API: {str(e)}", provider="GLM")

        except Exception as e:
            logger.error(f"GLM chat API error: {str(e)}")

            if "rate limit" in str(e).lower():
                raise LLMRateLimitError("Rate limit exceeded", provider="GLM")

            if "token" in str(e).lower() and "limit" in str(e).lower():
                model_info = self.get_model_info(model_to_use)
                raise LLMTokenLimitError(
                    "Token limit exceeded",
                    token_limit=model_info.get("max_tokens"),
                    provider="GLM"
                )

            raise LLMClientException(f"GLM chat API error: {str(e)}", provider="GLM")

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
        Generate a structured response matching a JSON schema.

        Args:
            prompt: Input prompt
            schema: JSON schema for response structure
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Returns:
            Dict[str, Any]: Structured response matching schema
        """
        import json

        # Enhance prompt to request JSON output
        enhanced_prompt = f"""{prompt}

Please provide your response in the following JSON format:
{json.dumps(schema, indent=2)}

Ensure your response is valid JSON matching this schema."""

        response = await self.generate_response(
            prompt=enhanced_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        # Parse JSON response
        try:
            # Try to extract JSON from markdown code blocks if present
            content = response.content.strip()
            if "```json" in content:
                # Extract JSON from code block
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                # Extract from generic code block
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            structured_data = json.loads(content)
            logger.info(f"Successfully parsed structured response with {len(structured_data)} keys")
            return structured_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            # Try to salvage partial JSON or return error
            raise LLMValidationError(
                f"Failed to parse structured response as JSON: {str(e)}",
                provider="GLM",
                details={"raw_content": response.content}
            )

    async def stream_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        Stream a response from GLM.

        Args:
            prompt: Input prompt
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Yields:
            LLMStreamChunk: Response chunks
        """
        if not prompt or not prompt.strip():
            raise LLMValidationError("Prompt cannot be empty", provider="GLM")

        model_to_use = model or self.model

        logger.info(f"Streaming response from GLM with model: {model_to_use}")

        try:
            llm = self._get_llm_instance(
                model=model_to_use,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Convert prompt to message format
            messages = [HumanMessage(content=prompt)]

            # Stream response
            async for chunk in llm.astream(messages):
                if chunk and chunk.content:
                    yield LLMStreamChunk(
                        content=chunk.content,
                        is_complete=False,
                        metadata={"model": model_to_use, "provider": "GLM"}
                    )

            # Send final completion chunk
            yield LLMStreamChunk(
                content="",
                is_complete=True,
                metadata={"model": model_to_use, "provider": "GLM"}
            )

            logger.info("GLM streaming completed")

        except Exception as e:
            logger.error(f"GLM streaming error: {str(e)}")
            raise LLMClientException(f"GLM streaming error: {str(e)}", provider="GLM")

    async def stream_chat_response(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        Stream a chat response from GLM.

        Args:
            messages: List of conversation messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Yields:
            LLMStreamChunk: Response chunks
        """
        if not messages:
            raise LLMValidationError("Messages list cannot be empty", provider="GLM")

        model_to_use = model or self.model

        logger.info(f"Streaming chat response from GLM with model: {model_to_use}")

        try:
            llm = self._get_llm_instance(
                model=model_to_use,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Convert messages
            langchain_messages = self._convert_messages(messages)

            # Stream response
            async for chunk in llm.astream(langchain_messages):
                if chunk and chunk.content:
                    yield LLMStreamChunk(
                        content=chunk.content,
                        is_complete=False,
                        metadata={"model": model_to_use, "provider": "GLM"}
                    )

            # Send final completion chunk
            yield LLMStreamChunk(
                content="",
                is_complete=True,
                metadata={"model": model_to_use, "provider": "GLM"}
            )

            logger.info("GLM chat streaming completed")

        except Exception as e:
            logger.error(f"GLM chat streaming error: {str(e)}")
            raise LLMClientException(f"GLM chat streaming error: {str(e)}", provider="GLM")

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get information about a specific model.

        Args:
            model: Model name

        Returns:
            Dict: Model information
        """
        if model not in self._model_info:
            # Return generic info for unknown models
            return {
                "name": model,
                "max_tokens": 128000,  # GLM-4 default
                "provider": "GLM",
                "description": "GLM model",
                "supports_streaming": True,
                "supports_structured": True,
            }

        return self._model_info[model].copy()

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in text.

        Uses a simple heuristic: ~0.3 tokens per character for mixed English/Chinese text.

        Args:
            text: Text to estimate tokens for

        Returns:
            int: Estimated token count
        """
        if not text:
            return 0

        # Rough estimation for mixed English/Chinese
        # English: ~4 chars per token, Chinese: ~1.5 chars per token
        # Average for mixed text: ~0.3 tokens per character
        return int(len(text) * 0.3)

    async def health_check(self) -> bool:
        """
        Check if GLM API is accessible.

        Returns:
            bool: True if API is healthy
        """
        try:
            test_prompt = "Respond with 'OK' if you receive this message."
            response = await self.generate_response(test_prompt, max_tokens=10)
            is_healthy = "OK" in response.content.upper()
            logger.info(f"GLM health check: {'HEALTHY' if is_healthy else 'UNHEALTHY'}")
            return is_healthy

        except Exception as e:
            logger.error(f"GLM health check failed: {str(e)}")
            return False

    def get_default_model(self) -> str:
        """
        Get the default model name.

        Returns:
            str: Default model name
        """
        return self.model

    def list_available_models(self) -> List[str]:
        """
        List available model names.

        Returns:
            List[str]: List of model names
        """
        return list(self._model_info.keys())

    async def check_token_availability(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        user_id: Optional[int] = None,
        priority: int = 3,
        db: Optional[AsyncSession] = None
    ) -> TokenCheckResult:
        """
        Check token availability before making an LLM call.

        Args:
            prompt: Input prompt to estimate tokens from
            model: Model name (uses default if None)
            max_tokens: Maximum tokens in response
            scope_type: Scope type for budget check (organization, suite, test, user)
            scope_id: Scope ID for budget check
            user_id: User ID for quota check
            priority: Request priority (1-10, higher = more important)
            db: Database session for token services

        Returns:
            TokenCheckResult: Check result with enforcement decision

        Raises:
            TokenEstimationError: If token estimation fails
        """
        model_to_use = model or self.model

        try:
            # Estimate tokens
            estimation = self.token_estimator.estimate_prompt_tokens(
                prompt=prompt,
                model=model_to_use,
                max_tokens=max_tokens
            )

            estimated_tokens = estimation["total_estimated_tokens"]
            estimated_cost = estimation["estimated_cost"]

            logger.info(
                f"Token estimation for {model_to_use}: "
                f"{estimated_tokens} tokens, ${estimated_cost['total_cost']:.6f}"
            )

            # Check budget if service and scope provided
            budget_available = None
            if self.token_budget_service and scope_type and scope_id and db:
                budget_result = await self.token_budget_service.check_token_availability(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    requested_tokens=estimated_tokens,
                    db=db
                )

                if hasattr(budget_result, 'data'):
                    budget_available = budget_result.data
                else:
                    budget_available = {"available": True, "reason": "Budget check disabled"}

            # Check quota if service and user provided
            quota_available = None
            if self.token_quota_service and user_id and db:
                quota_result = await self.token_quota_service.check_user_quota(
                    user_id=user_id,
                    requested_tokens=estimated_tokens,
                    db=db
                )

                if hasattr(quota_result, 'data'):
                    quota_available = quota_result.data
                else:
                    quota_available = {"available": True, "reason": "Quota check disabled"}

            # Determine enforcement action
            allowed = True
            enforcement_action = "allow"
            reason = "Sufficient tokens available"

            # Check budget availability
            if budget_available and not budget_available.get("available", True):
                budget_enforcement = budget_available.get("enforcement_action", "warning")
                if budget_enforcement == "blocked":
                    if self.enforcement_mode == "hard":
                        allowed = False
                        enforcement_action = "reject"
                        reason = budget_available.get("reason", "Budget exceeded")
                    elif self.enforcement_mode == "soft":
                        enforcement_action = "warn"
                        reason = budget_available.get("reason", "Budget exceeded")
                elif budget_enforcement == "warning":
                    enforcement_action = "warn"
                    reason = budget_available.get("reason", "Budget near limit")

            # Check quota availability
            if quota_available and not quota_available.get("available", True):
                quota_enforcement = quota_available.get("enforcement_action", "warning")
                if quota_enforcement == "blocked":
                    if self.enforcement_mode == "hard":
                        allowed = False
                        enforcement_action = "reject"
                        reason = quota_available.get("reason", "Quota exceeded")
                    elif self.enforcement_mode == "soft":
                        if enforcement_action == "allow":
                            enforcement_action = "warn"
                        reason = quota_available.get("reason", "Quota exceeded")
                elif quota_enforcement == "warning":
                    if enforcement_action == "allow":
                        enforcement_action = "warn"
                    reason = quota_available.get("reason", "Quota near limit")

            # Apply priority logic
            if not allowed and priority >= 8:
                # High priority requests are throttled instead of rejected
                allowed = True
                enforcement_action = "throttle"
                reason = "High priority request throttled instead of rejected"

            return TokenCheckResult(
                allowed=allowed,
                enforcement_action=enforcement_action,
                budget_available=budget_available,
                quota_available=quota_available,
                estimated_tokens=estimated_tokens,
                estimated_cost=estimated_cost,
                reason=reason
            )

        except Exception as e:
            logger.error(f"Error checking token availability: {e}")
            # On error, allow the request but log the error
            return TokenCheckResult(
                allowed=True,
                enforcement_action="allow",
                estimated_tokens=0,
                reason=f"Token check failed, allowing: {str(e)}"
            )

    async def record_token_usage(
        self,
        tokens_used: int,
        model: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Record token usage after an LLM call.

        Args:
            tokens_used: Number of tokens actually used
            model: Model name
            scope_type: Scope type for budget recording
            scope_id: Scope ID for budget recording
            user_id: User ID for quota recording
            metadata: Optional metadata (test_run_id, etc.)
            db: Database session for token services

        Returns:
            Dict with recording results
        """
        results = {}

        try:
            # Record budget usage
            if self.token_budget_service and scope_type and scope_id and db:
                budget_result = await self.token_budget_service.record_token_usage(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    tokens_used=tokens_used,
                    db=db,
                    metadata=metadata
                )

                if hasattr(budget_result, 'data'):
                    results["budget"] = budget_result.data
                else:
                    results["budget"] = {"recorded": False}

            # Record quota usage
            if self.token_quota_service and user_id and db:
                quota_result = await self.token_quota_service.record_quota_usage(
                    user_id=user_id,
                    tokens_used=tokens_used,
                    db=db,
                    metadata=metadata
                )

                if hasattr(quota_result, 'data'):
                    results["quota"] = quota_result.data
                else:
                    results["quota"] = {"recorded": False}

            logger.info(f"Token usage recorded: {tokens_used} tokens for {model}")

        except Exception as e:
            logger.error(f"Error recording token usage: {e}")
            results["error"] = str(e)

        return results

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name (uses default if None)

        Returns:
            Dict with cost breakdown (input_cost, output_cost, total_cost, currency)
        """
        model_to_use = model or self.model
        return self.token_estimator.estimate_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model_to_use
        )

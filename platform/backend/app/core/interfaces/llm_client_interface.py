"""
LLM Client Interface

Defines the contract for LLM (Large Language Model) providers.
Following SOLID Dependency Inversion Principle - high-level modules depend on abstractions.

This interface enables:
- Easy swapping of LLM providers (GLM, OpenAI, Anthropic, etc.)
- Mock implementations for testing
- Consistent API across different providers
- Token estimation and cost tracking
- Streaming responses support
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from app.services.token_budget_service import TokenBudgetService
    from app.services.token_quota_service import TokenQuotaService


class EnforcementMode(str, Enum):
    """Token enforcement modes."""
    HARD = "hard"  # Block requests when limit exceeded
    SOFT = "soft"  # Allow with warning when limit exceeded
    MONITORING = "monitoring"  # Track only, never block


class TokenCheckResult:
    """
    Result of token availability check.

    Attributes:
        allowed: Whether the request is allowed
        enforcement_action: Action taken (allow, reject, queue, throttle, warn)
        budget_available: Budget check result
        quota_available: Quota check result
        estimated_tokens: Estimated token count
        estimated_cost: Estimated cost
        reason: Reason for enforcement action
    """

    def __init__(
        self,
        allowed: bool,
        enforcement_action: str,
        budget_available: Optional[Dict[str, Any]] = None,
        quota_available: Optional[Dict[str, Any]] = None,
        estimated_tokens: Optional[int] = None,
        estimated_cost: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None
    ):
        self.allowed = allowed
        self.enforcement_action = enforcement_action
        self.budget_available = budget_available
        self.quota_available = quota_available
        self.estimated_tokens = estimated_tokens
        self.estimated_cost = estimated_cost
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed": self.allowed,
            "enforcement_action": self.enforcement_action,
            "budget_available": self.budget_available,
            "quota_available": self.quota_available,
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost": self.estimated_cost,
            "reason": self.reason
        }


@dataclass
class LLMResponse:
    """
    Standardized LLM response structure.

    Attributes:
        content: Generated text content
        model: Model name used for generation
        tokens_used: Number of tokens consumed (input + output)
        duration_ms: Generation duration in milliseconds
        finish_reason: Reason for generation completion (stop, length, etc.)
        metadata: Additional provider-specific metadata
    """
    content: str
    model: str
    tokens_used: int
    duration_ms: int
    finish_reason: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMMessage:
    """
    Standardized message structure for LLM conversations.

    Attributes:
        role: Message role (system, user, assistant, tool)
        content: Message content
        name: Optional name for the message
        tool_calls: Optional tool/function calls
        tool_id: Optional tool call ID this message is responding to
    """
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_id: Optional[str] = None


@dataclass
class LLMStreamChunk:
    """
    Standardized streaming response chunk.

    Attributes:
        content: Chunk of text content
        is_complete: Whether this is the final chunk
        metadata: Additional chunk metadata
    """
    content: str
    is_complete: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ILLMClient(ABC):
    """
    Interface for LLM (Large Language Model) clients.

    This abstraction allows switching between different LLM providers
    (GLM, OpenAI, Anthropic, etc.) without changing application code.
    """

    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: Input prompt for the LLM
            model: Model name (uses default if None)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse: Standardized response with metadata

        Raises:
            ValueError: If parameters are invalid
            ConnectionError: If API connection fails
            TimeoutError: If request times out
            Exception: For other errors
        """
        pass

    @abstractmethod
    async def generate_chat_response(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM using chat-style messages.

        Args:
            messages: List of conversation messages
            model: Model name (uses default if None)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse: Standardized response with metadata

        Raises:
            ValueError: If parameters are invalid
            ConnectionError: If API connection fails
            TimeoutError: If request times out
            Exception: For other errors
        """
        pass

    @abstractmethod
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

        Useful for generating structured data like test cases, configs, etc.

        Args:
            prompt: Input prompt for the LLM
            schema: JSON schema for response structure
            model: Model name (uses default if None)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            Dict[str, Any]: Structured response matching the schema

        Raises:
            ValueError: If parameters are invalid or schema is malformed
            ConnectionError: If API connection fails
            TimeoutError: If request times out
            Exception: For other errors
        """
        pass

    @abstractmethod
    async def stream_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        Stream a response from the LLM chunk by chunk.

        Useful for long-running generations or real-time responses.

        Args:
            prompt: Input prompt for the LLM
            model: Model name (uses default if None)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Yields:
            LLMStreamChunk: Chunks of the response

        Raises:
            ValueError: If parameters are invalid
            ConnectionError: If API connection fails
            TimeoutError: If request times out
            Exception: For other errors
        """
        pass

    @abstractmethod
    async def stream_chat_response(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[LLMStreamChunk]:
        """
        Stream a chat response from the LLM chunk by chunk.

        Args:
            messages: List of conversation messages
            model: Model name (uses default if None)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Yields:
            LLMStreamChunk: Chunks of the response

        Raises:
            ValueError: If parameters are invalid
            ConnectionError: If API connection fails
            TimeoutError: If request times out
            Exception: For other errors
        """
        pass

    @abstractmethod
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get information about a specific model.

        Args:
            model: Model name

        Returns:
            Dict with keys:
                - name: Model name
                - max_tokens: Maximum context length
                - provider: Provider name
                - description: Model description
                - cost_per_1k_tokens: Cost information (if available)
                - supports_streaming: Whether streaming is supported
                - supports_structured: Whether structured output is supported
        """
        pass

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in text.

        Useful for cost estimation and context length checking.

        Args:
            text: Text to estimate tokens for

        Returns:
            int: Estimated token count
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM API is accessible and working.

        Returns:
            bool: True if API is healthy

        Raises:
            Exception: If health check fails
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """
        Get the default model name.

        Returns:
            str: Default model name
        """
        pass

    @abstractmethod
    def list_available_models(self) -> List[str]:
        """
        List available model names.

        Returns:
            List[str]: List of model names
        """
        pass

    @abstractmethod
    async def check_token_availability(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        user_id: Optional[int] = None,
        priority: int = 3
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

        Returns:
            TokenCheckResult: Check result with enforcement decision

        Raises:
            TokenEstimationError: If token estimation fails
        """
        pass

    @abstractmethod
    async def record_token_usage(
        self,
        tokens_used: int,
        model: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
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

        Returns:
            Dict with recording results
        """
        pass

    @abstractmethod
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
        pass


class LLMClientException(Exception):
    """Base exception for LLM client errors."""

    def __init__(self, message: str, provider: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(self.message)


class LLMConnectionError(LLMClientException, ConnectionError):
    """Exception raised when LLM API connection fails."""

    pass


class LLMTimeoutError(LLMClientException, TimeoutError):
    """Exception raised when LLM API request times out."""

    pass


class LLMValidationError(LLMClientException, ValueError):
    """Exception raised when LLM request validation fails."""

    pass


class LLMRateLimitError(LLMClientException):
    """Exception raised when LLM API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class LLMTokenLimitError(LLMClientException):
    """Exception raised when token limit is exceeded."""

    def __init__(self, message: str, token_limit: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.token_limit = token_limit

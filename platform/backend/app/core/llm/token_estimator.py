"""
Token Estimation Utility

Provides token estimation for different LLM models and text formats.
Supports cost estimation and token counting for various models.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Supported LLM model types."""
    GLM_4_PLUS = "glm-4-plus"
    GLM_4 = "glm-4"
    GLM_4_FLASH = "glm-4-flash"
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"


class TokenEstimator:
    """
    Token estimation utility for LLM models.

    Provides:
    - Character-to-token estimation
    - Message-to-token estimation
    - Cost estimation
    - Model-specific pricing

    Estimation accuracy:
    - GLM models: ~0.3 tokens per character (mixed English/Chinese)
    - GPT models: ~0.25 tokens per character (English)
    - Chinese text: ~0.67 tokens per character
    - Code: ~0.15 tokens per character
    """

    # Token estimation factors (chars per token)
    ESTIMATION_FACTORS = {
        ModelType.GLM_4_PLUS: 0.3,
        ModelType.GLM_4: 0.3,
        ModelType.GLM_4_FLASH: 0.3,
        ModelType.GPT_4: 0.25,
        ModelType.GPT_3_5_TURBO: 0.25,
    }

    # Pricing per 1K tokens (in USD)
    # Note: These are approximate prices and should be updated regularly
    PRICING = {
        ModelType.GLM_4_PLUS: {
            "input": 0.012,  # $0.012 per 1K input tokens
            "output": 0.012,  # $0.012 per 1K output tokens
        },
        ModelType.GLM_4: {
            "input": 0.01,  # $0.01 per 1K input tokens
            "output": 0.01,  # $0.01 per 1K output tokens
        },
        ModelType.GLM_4_FLASH: {
            "input": 0.0001,  # $0.0001 per 1K input tokens
            "output": 0.0001,  # $0.0001 per 1K output tokens
        },
        ModelType.GPT_4: {
            "input": 0.03,  # $0.03 per 1K input tokens
            "output": 0.06,  # $0.06 per 1K output tokens
        },
        ModelType.GPT_3_5_TURBO: {
            "input": 0.0015,  # $0.0015 per 1K input tokens
            "output": 0.002,  # $0.002 per 1K output tokens
        },
    }

    # Special character multipliers
    CHAR_MULTIPLIERS = {
        "chinese": 2.0,  # Chinese characters use ~2x tokens
        "code": 0.5,  # Code uses ~0.5x tokens (more efficient)
        "markup": 1.2,  # Markup/JSON uses ~1.2x tokens
    }

    @classmethod
    def estimate_tokens_from_text(
        cls,
        text: str,
        model: str = ModelType.GLM_4_PLUS,
        text_type: Optional[str] = None
    ) -> int:
        """
        Estimate token count from text.

        Args:
            text: Text to estimate
            model: Model name (default: glm-4-plus)
            text_type: Text type (chinese, code, markup) for better estimation

        Returns:
            int: Estimated token count

        Examples:
            >>> estimator = TokenEstimator()
            >>> estimator.estimate_tokens_from_text("Hello world")
            3
            >>> estimator.estimate_tokens_from_text("你好世界", text_type="chinese")
            8
        """
        if not text:
            return 0

        text_length = len(text)

        # Get base estimation factor
        try:
            model_enum = ModelType(model)
            factor = cls.ESTIMATION_FACTORS.get(model_enum, 0.3)
        except ValueError:
            # Unknown model, use default factor
            factor = 0.3

        # Apply text type multiplier
        if text_type:
            multiplier = cls.CHAR_MULTIPLIERS.get(text_type, 1.0)
            factor = factor * multiplier

        # Calculate tokens
        estimated_tokens = int(text_length * factor)

        logger.debug(
            f"Token estimation: {text_length} chars * {factor:.3f} = {estimated_tokens} tokens"
        )

        return estimated_tokens

    @classmethod
    def estimate_tokens_from_messages(
        cls,
        messages: List[Dict[str, str]],
        model: str = ModelType.GLM_4_PLUS
    ) -> int:
        """
        Estimate token count from message list.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (default: glm-4-plus)

        Returns:
            int: Estimated token count

        Examples:
            >>> messages = [
            ...     {"role": "system", "content": "You are a helpful assistant"},
            ...     {"role": "user", "content": "Hello!"},
            ... ]
            >>> TokenEstimator.estimate_tokens_from_messages(messages)
            15
        """
        if not messages:
            return 0

        total_tokens = 0

        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "")

            # Estimate content tokens
            content_tokens = cls.estimate_tokens_from_text(content, model)
            total_tokens += content_tokens

            # Add tokens for role and formatting (~4 tokens per message)
            total_tokens += 4

        # Add overhead for the conversation (~3 tokens)
        total_tokens += 3

        logger.debug(f"Token estimation from {len(messages)} messages: {total_tokens} tokens")

        return total_tokens

    @classmethod
    def estimate_cost(
        cls,
        input_tokens: int,
        output_tokens: int,
        model: str = ModelType.GLM_4_PLUS
    ) -> Dict[str, Any]:
        """
        Estimate cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name (default: glm-4-plus)

        Returns:
            Dict with cost breakdown:
                - input_cost: Cost for input tokens
                - output_cost: Cost for output tokens
                - total_cost: Total cost
                - currency: Currency (USD)

        Examples:
            >>> TokenEstimator.estimate_cost(1000, 500, "glm-4-plus")
            {
                "input_cost": 0.012,
                "output_cost": 0.006,
                "total_cost": 0.018,
                "currency": "USD"
            }
        """
        try:
            model_enum = ModelType(model)
            pricing = cls.PRICING.get(model_enum, cls.PRICING[ModelType.GLM_4_PLUS])
        except ValueError:
            # Unknown model, use default pricing
            pricing = cls.PRICING[ModelType.GLM_4_PLUS]

        # Calculate costs (pricing is per 1K tokens)
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost

        return {
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(total_cost, 6),
            "currency": "USD",
            "model": model
        }

    @classmethod
    def estimate_prompt_tokens(
        cls,
        prompt: str,
        model: str = ModelType.GLM_4_PLUS,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Estimate tokens for a prompt including expected response.

        Args:
            prompt: Input prompt
            model: Model name
            max_tokens: Expected max tokens in response (optional)

        Returns:
            Dict with estimation details:
                - input_tokens: Estimated input tokens
                - estimated_output_tokens: Estimated output tokens
                - total_estimated_tokens: Total estimated tokens
                - estimated_cost: Estimated cost

        Examples:
            >>> result = TokenEstimator.estimate_prompt_tokens(
            ...     "Explain quantum computing",
            ...     max_tokens=1000
            ... )
            >>> result["total_estimated_tokens"]
            1350
        """
        input_tokens = cls.estimate_tokens_from_text(prompt, model)

        # Estimate output tokens (typically 20-40% of input for explanations)
        if max_tokens:
            estimated_output_tokens = min(max_tokens, int(input_tokens * 0.3))
        else:
            estimated_output_tokens = int(input_tokens * 0.3)

        total_tokens = input_tokens + estimated_output_tokens

        cost = cls.estimate_cost(input_tokens, estimated_output_tokens, model)

        return {
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "total_estimated_tokens": total_tokens,
            "estimated_cost": cost,
            "model": model
        }

    @classmethod
    def detect_text_type(cls, text: str) -> str:
        """
        Detect text type for better token estimation.

        Args:
            text: Text to analyze

        Returns:
            str: Detected text type (chinese, code, markup, or default)
        """
        # Check for Chinese characters
        chinese_chars = sum(1 for char in text if '一' <= char <= '鿿')
        if chinese_chars / len(text) > 0.3:
            return "chinese"

        # Check for code-like patterns
        code_indicators = ['def ', 'function', 'const ', 'let ', 'var ', 'class ', 'import ']
        if any(indicator in text for indicator in code_indicators):
            return "code"

        # Check for markup/JSON
        markup_indicators = ['{', '}', '<', '>', '[', ']']
        markup_count = sum(1 for char in text if char in markup_indicators)
        if markup_count / len(text) > 0.1:
            return "markup"

        return "default"

    @classmethod
    def get_model_pricing(cls, model: str) -> Dict[str, float]:
        """
        Get pricing for a specific model.

        Args:
            model: Model name

        Returns:
            Dict with input and output pricing per 1K tokens
        """
        try:
            model_enum = ModelType(model)
            return cls.PRICING.get(model_enum, cls.PRICING[ModelType.GLM_4_PLUS])
        except ValueError:
            return cls.PRICING[ModelType.GLM_4_PLUS]

    @classmethod
    def list_supported_models(cls) -> List[str]:
        """
        List all supported models.

        Returns:
            List[str]: List of model names
        """
        return [model.value for model in ModelType]

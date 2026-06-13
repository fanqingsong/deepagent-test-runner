"""
Token Limitation Exceptions

Custom exceptions for token budget and quota enforcement.
These exceptions provide detailed error information for LLM token management.
"""

from typing import Optional, Dict, Any


class TokenBudgetExceeded(Exception):
    """
    Exception raised when token budget limit is exceeded.

    Attributes:
        message: Human-readable error message
        budget_id: ID of the budget that was exceeded
        scope_type: Scope type (organization, suite, test, user)
        scope_id: ID of the scoped entity
        requested_tokens: Number of tokens requested
        available_tokens: Number of tokens available
        enforcement_mode: Enforcement mode (hard, soft, monitoring)
    """

    def __init__(
        self,
        message: str,
        budget_id: Optional[int] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        requested_tokens: Optional[int] = None,
        available_tokens: Optional[int] = None,
        enforcement_mode: Optional[str] = None,
        **kwargs
    ):
        self.message = message
        self.budget_id = budget_id
        self.scope_type = scope_type
        self.scope_id = scope_id
        self.requested_tokens = requested_tokens
        self.available_tokens = available_tokens
        self.enforcement_mode = enforcement_mode
        self.details = kwargs

        # Build detailed error context
        context = {
            "budget_id": budget_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "requested_tokens": requested_tokens,
            "available_tokens": available_tokens,
            "enforcement_mode": enforcement_mode,
            "shortage": (requested_tokens - available_tokens) if requested_tokens and available_tokens else None
        }
        context.update(kwargs)

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_type": "TokenBudgetExceeded",
            "message": self.message,
            "budget_id": self.budget_id,
            "scope_type": self.scope_type,
            "scope_id": self.scope_id,
            "requested_tokens": self.requested_tokens,
            "available_tokens": self.available_tokens,
            "enforcement_mode": self.enforcement_mode,
            "details": self.details
        }


class TokenQuotaExceeded(Exception):
    """
    Exception raised when user token quota limit is exceeded.

    Attributes:
        message: Human-readable error message
        quota_id: ID of the quota that was exceeded
        user_id: ID of the user
        quota_name: Name of the quota
        requested_tokens: Number of tokens requested
        available_tokens: Number of tokens available
        enforcement_mode: Enforcement mode (hard, soft, monitoring)
        period_type: Period type (daily, weekly, monthly)
    """

    def __init__(
        self,
        message: str,
        quota_id: Optional[int] = None,
        user_id: Optional[int] = None,
        quota_name: Optional[str] = None,
        requested_tokens: Optional[int] = None,
        available_tokens: Optional[int] = None,
        enforcement_mode: Optional[str] = None,
        period_type: Optional[str] = None,
        **kwargs
    ):
        self.message = message
        self.quota_id = quota_id
        self.user_id = user_id
        self.quota_name = quota_name
        self.requested_tokens = requested_tokens
        self.available_tokens = available_tokens
        self.enforcement_mode = enforcement_mode
        self.period_type = period_type
        self.details = kwargs

        # Build detailed error context
        context = {
            "quota_id": quota_id,
            "user_id": user_id,
            "quota_name": quota_name,
            "requested_tokens": requested_tokens,
            "available_tokens": available_tokens,
            "enforcement_mode": enforcement_mode,
            "period_type": period_type,
            "shortage": (requested_tokens - available_tokens) if requested_tokens and available_tokens else None
        }
        context.update(kwargs)

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_type": "TokenQuotaExceeded",
            "message": self.message,
            "quota_id": self.quota_id,
            "user_id": self.user_id,
            "quota_name": self.quota_name,
            "requested_tokens": self.requested_tokens,
            "available_tokens": self.available_tokens,
            "enforcement_mode": self.enforcement_mode,
            "period_type": self.period_type,
            "details": self.details
        }


class TokenEstimationError(Exception):
    """
    Exception raised when token estimation fails.

    Attributes:
        message: Human-readable error message
        text_length: Length of text that failed estimation
        model_name: Model name for estimation
        reason: Specific reason for failure
    """

    def __init__(
        self,
        message: str,
        text_length: Optional[int] = None,
        model_name: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs
    ):
        self.message = message
        self.text_length = text_length
        self.model_name = model_name
        self.reason = reason
        self.details = kwargs

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_type": "TokenEstimationError",
            "message": self.message,
            "text_length": self.text_length,
            "model_name": self.model_name,
            "reason": self.reason,
            "details": self.details
        }


class TokenLimitationError(Exception):
    """
    Base exception for token limitation errors.

    Attributes:
        message: Human-readable error message
        error_code: Specific error code
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        **kwargs
    ):
        self.message = message
        self.error_code = error_code or "TOKEN_LIMITATION_ERROR"
        self.details = kwargs

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_type": "TokenLimitationError",
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }

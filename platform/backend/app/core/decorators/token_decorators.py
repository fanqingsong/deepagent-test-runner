"""
Token Limitation Decorators

Decorators for automatic token checking and tracking in LLM-related functions.
Supports both sync and async functions with comprehensive token management.
"""

import asyncio
import functools
import logging
from typing import Callable, Optional, Any, Dict, TYPE_CHECKING
from inspect import iscoroutinefunction

from app.core.exceptions.token_exceptions import (
    TokenBudgetExceeded,
    TokenQuotaExceeded
)
from app.core.llm.token_estimator import TokenEstimator

if TYPE_CHECKING:
    from app.services.token_budget_service import TokenBudgetService
    from app.services.token_quota_service import TokenQuotaService
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def check_token_budget(
    scope_type_param: str = "scope_type",
    scope_id_param: str = "scope_id",
    prompt_param: str = "prompt",
    model_param: str = "model",
    max_tokens_param: str = "max_tokens",
    priority_param: str = "priority",
    enforcement_mode: str = "soft",
    on_exceeded: str = "raise"  # raise, return, warn
):
    """
    Decorator to check token budget before function execution.

    Args:
        scope_type_param: Parameter name for scope type
        scope_id_param: Parameter name for scope ID
        prompt_param: Parameter name for prompt/text
        model_param: Parameter name for model
        max_tokens_param: Parameter name for max tokens
        priority_param: Parameter name for priority
        enforcement_mode: Enforcement mode (hard, soft, monitoring)
        on_exceeded: Action when exceeded (raise, return, warn)

    Examples:
        ```python
        @check_token_budget(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            enforcement_mode="soft"
        )
        async def generate_test_plan(
            prompt: str,
            scope_type: str,
            scope_id: int,
            **kwargs
        ):
            # Function body
            pass
        ```
    """
    def decorator(func: Callable) -> Callable:
        if iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract parameters
                scope_type = kwargs.get(scope_type_param)
                scope_id = kwargs.get(scope_id_param)
                prompt = kwargs.get(prompt_param)
                model = kwargs.get(model_param, "glm-4-plus")
                max_tokens = kwargs.get(max_tokens_param, 4096)
                priority = kwargs.get(priority_param, 3)

                # Get token budget service from kwargs or globals
                budget_service: Optional['TokenBudgetService'] = kwargs.get(
                    'token_budget_service'
                )
                db: Optional['AsyncSession'] = kwargs.get('db')

                # Check if we have all required parameters
                if budget_service and scope_type and scope_id and db and prompt:
                    try:
                        # Estimate tokens
                        estimator = TokenEstimator()
                        estimated_tokens = estimator.estimate_prompt_tokens(
                            prompt=prompt,
                            model=model,
                            max_tokens=max_tokens
                        )["total_estimated_tokens"]

                        # Check availability
                        result = await budget_service.check_token_availability(
                            scope_type=scope_type,
                            scope_id=scope_id,
                            requested_tokens=estimated_tokens,
                            db=db
                        )

                        if hasattr(result, 'data'):
                            check_data = result.data
                        else:
                            check_data = result

                        # Handle exceeded budget
                        if not check_data.get("available", True):
                            enforcement_action = check_data.get("enforcement_action", "warning")

                            if enforcement_mode == "hard" and enforcement_action == "blocked":
                                if on_exceeded == "raise":
                                    raise TokenBudgetExceeded(
                                        message=f"Token budget exceeded for {scope_type}:{scope_id}",
                                        budget_id=check_data.get("budget_id"),
                                        scope_type=scope_type,
                                        scope_id=scope_id,
                                        requested_tokens=estimated_tokens,
                                        available_tokens=check_data.get("available_tokens"),
                                        enforcement_mode="hard"
                                    )
                                elif on_exceeded == "return":
                                    logger.warning(
                                        f"Token budget exceeded for {scope_type}:{scope_id}, "
                                        f"returning early"
                                    )
                                    return {
                                        "error": "token_budget_exceeded",
                                        "available_tokens": check_data.get("available_tokens"),
                                        "requested_tokens": estimated_tokens
                                    }
                                elif on_exceeded == "warn":
                                    logger.warning(
                                        f"Token budget exceeded for {scope_type}:{scope_id}, "
                                        f"proceeding with warning"
                                    )

                        logger.debug(
                            f"Token budget check passed for {scope_type}:{scope_id}: "
                            f"{estimated_tokens} tokens"
                        )

                    except Exception as e:
                        logger.error(f"Token budget check failed: {e}")
                        # Continue execution on check failure

                # Execute original function
                return await func(*args, **kwargs)

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, run check in async context if possible
                scope_type = kwargs.get(scope_type_param)
                scope_id = kwargs.get(scope_id_param)
                prompt = kwargs.get(prompt_param)

                budget_service: Optional['TokenBudgetService'] = kwargs.get(
                    'token_budget_service'
                )
                db: Optional['AsyncSession'] = kwargs.get('db')

                if budget_service and scope_type and scope_id and db and prompt:
                    logger.warning(
                        "Token budget check on sync function - skipping async check"
                    )

                # Execute original function
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


def track_token_usage(
    scope_type_param: str = "scope_type",
    scope_id_param: str = "scope_id",
    user_id_param: str = "user_id",
    metadata_param: str = "token_metadata"
):
    """
    Decorator to track token usage after function execution.

    Automatically records token usage to budget and quota services.

    Args:
        scope_type_param: Parameter name for scope type
        scope_id_param: Parameter name for scope ID
        user_id_param: Parameter name for user ID
        metadata_param: Parameter name for additional metadata

    Examples:
        ```python
        @track_token_usage(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            user_id_param="user_id"
        )
        async def generate_test_script(
            prompt: str,
            scope_type: str,
            scope_id: int,
            user_id: int,
            **kwargs
        ):
            # Function that uses LLM
            pass
        ```
    """
    def decorator(func: Callable) -> Callable:
        if iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Execute original function
                result = await func(*args, **kwargs)

                # Extract parameters
                scope_type = kwargs.get(scope_type_param)
                scope_id = kwargs.get(scope_id_param)
                user_id = kwargs.get(user_id_param)
                metadata = kwargs.get(metadata_param, {})

                # Get token services
                budget_service: Optional['TokenBudgetService'] = kwargs.get(
                    'token_budget_service'
                )
                quota_service: Optional['TokenQuotaService'] = kwargs.get(
                    'token_quota_service'
                )
                db: Optional['AsyncSession'] = kwargs.get('db')

                # Try to extract token usage from result
                tokens_used = None
                if isinstance(result, dict):
                    tokens_used = result.get("tokens_used")
                elif hasattr(result, "tokens_used"):
                    tokens_used = result.tokens_used
                elif hasattr(result, "metadata"):
                    # Check in metadata
                    if isinstance(result.metadata, dict):
                        tokens_used = result.metadata.get("tokens_used")

                # Record usage if we have tokens and services
                if tokens_used and db:
                    try:
                        # Record budget usage
                        if budget_service and scope_type and scope_id:
                            await budget_service.record_token_usage(
                                scope_type=scope_type,
                                scope_id=scope_id,
                                tokens_used=tokens_used,
                                db=db,
                                metadata=metadata
                            )
                            logger.debug(
                                f"Recorded {tokens_used} tokens to budget {scope_type}:{scope_id}"
                            )

                        # Record quota usage
                        if quota_service and user_id:
                            await quota_service.record_quota_usage(
                                user_id=user_id,
                                tokens_used=tokens_used,
                                db=db,
                                metadata=metadata
                            )
                            logger.debug(f"Recorded {tokens_used} tokens to quota for user {user_id}")

                    except Exception as e:
                        logger.error(f"Failed to track token usage: {e}")

                return result

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Execute original function
                result = func(*args, **kwargs)

                # For sync functions, just log
                logger.debug("Token usage tracking on sync function - skipping async tracking")

                return result

            return sync_wrapper

    return decorator


def enforce_token_limits(
    scope_type_param: str = "scope_type",
    scope_id_param: str = "scope_id",
    user_id_param: str = "user_id",
    prompt_param: str = "prompt",
    model_param: str = "model",
    enforcement_mode: str = "soft",
    on_exceeded: str = "raise"
):
    """
    Combined decorator for both pre-call checking and post-call tracking.

    This decorator combines the functionality of check_token_budget and
    track_token_usage for comprehensive token management.

    Args:
        scope_type_param: Parameter name for scope type
        scope_id_param: Parameter name for scope ID
        user_id_param: Parameter name for user ID
        prompt_param: Parameter name for prompt/text
        model_param: Parameter name for model
        enforcement_mode: Enforcement mode (hard, soft, monitoring)
        on_exceeded: Action when exceeded (raise, return, warn)

    Examples:
        ```python
        @enforce_token_limits(
            scope_type_param="scope_type",
            scope_id_param="scope_id",
            user_id_param="user_id",
            enforcement_mode="soft"
        )
        async def generate_test_cases(
            prompt: str,
            scope_type: str,
            scope_id: int,
            user_id: int,
            **kwargs
        ):
            # Function that uses LLM
            pass
        ```
    """
    def decorator(func: Callable) -> Callable:
        # Apply check decorator first
        checked_func = check_token_budget(
            scope_type_param=scope_type_param,
            scope_id_param=scope_id_param,
            prompt_param=prompt_param,
            model_param=model_param,
            enforcement_mode=enforcement_mode,
            on_exceeded=on_exceeded
        )(func)

        # Then apply track decorator
        tracked_func = track_token_usage(
            scope_type_param=scope_type_param,
            scope_id_param=scope_id_param,
            user_id_param=user_id_param
        )(checked_func)

        return tracked_func

    return decorator


class TokenLimiter:
    """
    Context manager for token limitation.

    Provides a context-based approach to token management instead of decorators.

    Examples:
        ```python
        async with TokenLimiter(
            budget_service=budget_service,
            quota_service=quota_service,
            scope_type="test",
            scope_id=123,
            user_id=456,
            db=db_session
        ) as limiter:
            # Check before LLM call
            await limiter.check_availability(prompt="Generate test plan", model="glm-4-plus")

            # Make LLM call
            response = await llm_client.generate_response(...)

            # Track after call
            await limiter.track_usage(tokens_used=response.tokens_used)
        ```
    """

    def __init__(
        self,
        budget_service: Optional['TokenBudgetService'] = None,
        quota_service: Optional['TokenQuotaService'] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        user_id: Optional[int] = None,
        db: Optional['AsyncSession'] = None,
        enforcement_mode: str = "soft"
    ):
        self.budget_service = budget_service
        self.quota_service = quota_service
        self.scope_type = scope_type
        self.scope_id = scope_id
        self.user_id = user_id
        self.db = db
        self.enforcement_mode = enforcement_mode
        self._estimated_tokens = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup if needed
        pass

    async def check_availability(
        self,
        prompt: str,
        model: str = "glm-4-plus",
        max_tokens: int = 4096,
        priority: int = 3
    ) -> Dict[str, Any]:
        """
        Check token availability.

        Returns:
            Dict with check results including 'allowed' boolean
        """
        if not self.budget_service:
            return {"allowed": True, "reason": "No budget service configured"}

        try:
            estimator = TokenEstimator()
            estimation = estimator.estimate_prompt_tokens(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens
            )
            self._estimated_tokens = estimation["total_estimated_tokens"]

            result = await self.budget_service.check_token_availability(
                scope_type=self.scope_type,
                scope_id=self.scope_id,
                requested_tokens=self._estimated_tokens,
                db=self.db
            )

            if hasattr(result, 'data'):
                return result.data
            return result

        except Exception as e:
            logger.error(f"Token availability check failed: {e}")
            return {"allowed": True, "reason": "Check failed"}

    async def track_usage(
        self,
        tokens_used: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track token usage after LLM call.
        """
        if not self.db:
            logger.warning("No database session provided for token tracking")
            return

        tasks = []

        # Track budget usage
        if self.budget_service and self.scope_type and self.scope_id:
            tasks.append(self.budget_service.record_token_usage(
                scope_type=self.scope_type,
                scope_id=self.scope_id,
                tokens_used=tokens_used,
                db=self.db,
                metadata=metadata
            ))

        # Track quota usage
        if self.quota_service and self.user_id:
            tasks.append(self.quota_service.record_quota_usage(
                user_id=self.user_id,
                tokens_used=tokens_used,
                db=self.db,
                metadata=metadata
            ))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.debug(f"Tracked {tokens_used} tokens to services")

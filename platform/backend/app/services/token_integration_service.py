"""
Token Integration Service

Centralized service for integrating token checking into test workflows.
Provides high-level methods for token validation, tracking, and error handling.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.token_budget_service import TokenBudgetService
from app.services.token_quota_service import TokenQuotaService
from app.core.result_helpers import service_success, service_error, service_validation_error
from app.core.error_codes import ErrorCode
from app.core.llm.token_estimator import TokenEstimator
from app.core.exceptions.token_exceptions import TokenBudgetExceeded, TokenQuotaExceeded

logger = logging.getLogger(__name__)


class TokenIntegrationService:
    """
    Service for integrating token management into test workflows.

    Responsibilities:
    - Check token availability before LLM operations
    - Track token usage after LLM operations
    - Handle token limit errors gracefully
    - Provide metadata for test results
    - Support multiple scope types (test, suite, organization)

    Usage:
        service = TokenIntegrationService(budget_service, quota_service)

        # Before LLM call
        check_result = await service.check_before_llm_call(
            scope_type="test",
            scope_id=123,
            prompt="Generate test cases",
            model="glm-4-plus"
        )

        if not check_result["allowed"]:
            return error_result

        # Make LLM call...
        # After LLM call
        await service.track_after_llm_call(
            scope_type="test",
            scope_id=123,
            tokens_used=1500,
            metadata={"test_run_id": "abc123"}
        )
    """

    def __init__(
        self,
        budget_service: Optional[TokenBudgetService] = None,
        quota_service: Optional[TokenQuotaService] = None
    ):
        """
        Initialize Token Integration Service.

        Args:
            budget_service: Token budget service (created if not provided)
            quota_service: Token quota service (created if not provided)
        """
        self.budget_service = budget_service or TokenBudgetService()
        self.quota_service = quota_service or TokenQuotaService()
        self.estimator = TokenEstimator()

    async def check_before_llm_call(
        self,
        scope_type: str,
        scope_id: Optional[int],
        prompt: str,
        model: str = "glm-4-plus",
        max_tokens: int = 4096,
        db: Optional[AsyncSession] = None,
        enforcement_mode: str = "soft"
    ) -> Dict[str, Any]:
        """
        Check token availability before making an LLM call.

        Args:
            scope_type: Scope type (test, suite, organization, user)
            scope_id: ID of the scoped entity
            prompt: The prompt/text to be sent
            model: Model name for token estimation
            max_tokens: Maximum tokens in response
            db: Database session
            enforcement_mode: Enforcement mode (hard, soft, monitoring)

        Returns:
            dict with keys:
                - allowed (bool): Whether operation is allowed
                - estimated_tokens (int): Estimated token usage
                - available_tokens (int): Tokens remaining in budget
                - enforcement_action (str): Action taken (allowed, warning, blocked)
                - reason (str): Explanation of decision
                - budget_status (dict): Full budget status details
        """
        try:
            # Estimate tokens
            estimation = self.estimator.estimate_prompt_tokens(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens
            )
            estimated_tokens = estimation["total_estimated_tokens"]

            logger.debug(
                f"Token check for {scope_type}:{scope_id}: "
                f"estimated {estimated_tokens} tokens"
            )

            # Check budget if service and db available
            if self.budget_service and db and scope_id:
                result = await self.budget_service.check_token_availability(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    requested_tokens=estimated_tokens,
                    db=db
                )

                if hasattr(result, 'data'):
                    budget_data = result.data
                else:
                    budget_data = result

                # Determine if allowed
                allowed = budget_data.get("available", True)
                enforcement_action = budget_data.get("enforcement_action", "allowed")

                # Hard enforcement blocking
                if enforcement_mode == "hard" and not allowed:
                    logger.warning(
                        f"Token budget exceeded for {scope_type}:{scope_id}, "
                        f"blocking operation (hard enforcement)"
                    )
                    return {
                        "allowed": False,
                        "estimated_tokens": estimated_tokens,
                        "available_tokens": budget_data.get("available_tokens", 0),
                        "enforcement_action": "blocked",
                        "reason": "Token budget exceeded (hard enforcement)",
                        "budget_status": budget_data,
                        "error": "token_budget_exceeded"
                    }

                # Soft enforcement warning
                if not allowed and enforcement_mode == "soft":
                    logger.warning(
                        f"Token budget exceeded for {scope_type}:{scope_id}, "
                        f"proceeding with warning (soft enforcement)"
                    )

                return {
                    "allowed": True,
                    "estimated_tokens": estimated_tokens,
                    "available_tokens": budget_data.get("available_tokens", 0),
                    "enforcement_action": enforcement_action,
                    "reason": "Token check passed",
                    "budget_status": budget_data
                }

            # No budget checking configured
            return {
                "allowed": True,
                "estimated_tokens": estimated_tokens,
                "available_tokens": -1,  # Unknown
                "enforcement_action": "allowed",
                "reason": "No budget checking configured",
                "budget_status": None
            }

        except Exception as e:
            logger.error(f"Token pre-check failed: {e}")
            # Fail open - allow operation on check failure
            return {
                "allowed": True,
                "estimated_tokens": -1,
                "available_tokens": -1,
                "enforcement_action": "allowed",
                "reason": f"Check failed: {str(e)}",
                "budget_status": None
            }

    async def track_after_llm_call(
        self,
        scope_type: str,
        scope_id: Optional[int],
        tokens_used: int,
        db: Optional[AsyncSession] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track token usage after an LLM call completes.

        Args:
            scope_type: Scope type (test, suite, organization)
            scope_id: ID of the scoped entity
            tokens_used: Actual tokens consumed
            db: Database session
            user_id: Optional user ID for quota tracking
            metadata: Optional metadata (test_run_id, operation, etc.)

        Returns:
            dict with tracking results
        """
        try:
            if tokens_used <= 0:
                logger.warning(f"Invalid tokens_used: {tokens_used}, skipping tracking")
                return {"tracked": False, "reason": "Invalid token count"}

            tracking_results = {}
            tasks = []

            # Track budget usage
            if self.budget_service and db and scope_id:
                async def track_budget():
                    result = await self.budget_service.record_token_usage(
                        scope_type=scope_type,
                        scope_id=scope_id,
                        tokens_used=tokens_used,
                        db=db,
                        metadata=metadata
                    )
                    if hasattr(result, 'data'):
                        return result.data
                    return result

                tasks.append(("budget", track_budget()))

            # Track quota usage
            if self.quota_service and db and user_id:
                async def track_quota():
                    result = await self.quota_service.record_quota_usage(
                        user_id=user_id,
                        tokens_used=tokens_used,
                        db=db,
                        metadata=metadata
                    )
                    if hasattr(result, 'data'):
                        return result.data
                    return result

                tasks.append(("quota", track_quota()))

            # Execute tracking tasks
            import asyncio
            if tasks:
                results = await asyncio.gather(
                    *[task for _, task in tasks],
                    return_exceptions=True
                )

                for (name, _), result in zip(tasks, results):
                    if isinstance(result, Exception):
                        logger.error(f"{name.title()} tracking failed: {result}")
                        tracking_results[name] = {"error": str(result)}
                    else:
                        tracking_results[name] = result

                logger.info(
                    f"Tracked {tokens_used} tokens for {scope_type}:{scope_id} "
                    f"(budget: {'✓' if 'budget' in tracking_results else '✗'}, "
                    f"quota: {'✓' if 'quota' in tracking_results else '✗'})"
                )
            else:
                logger.debug("No tracking services available, skipping token tracking")

            return {
                "tracked": len(tracking_results) > 0,
                "tokens_used": tokens_used,
                "tracking_results": tracking_results
            }

        except Exception as e:
            logger.error(f"Token tracking failed: {e}")
            return {"tracked": False, "error": str(e)}

    async def check_and_track_workflow(
        self,
        scope_type: str,
        scope_id: Optional[int],
        prompt: str,
        llm_call_func: callable,
        db: Optional[AsyncSession] = None,
        user_id: Optional[int] = None,
        model: str = "glm-4-plus",
        max_tokens: int = 4096,
        enforcement_mode: str = "soft",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: check before, execute LLM call, track after.

        This is a convenience method that combines pre-check, execution, and tracking.

        Args:
            scope_type: Scope type
            scope_id: Scope ID
            prompt: Prompt for token estimation
            llm_call_func: Async function that makes the LLM call
            db: Database session
            user_id: Optional user ID
            model: Model name
            max_tokens: Max tokens
            enforcement_mode: Enforcement mode
            metadata: Additional metadata

        Returns:
            dict with:
                - success (bool): Whether workflow succeeded
                - allowed (bool): Whether operation was allowed
                - result (Any): Result from LLM call (if successful)
                - tokens_used (int): Tokens consumed (if tracked)
                - error (str): Error message (if failed)
        """
        # Step 1: Check before
        check_result = await self.check_before_llm_call(
            scope_type=scope_type,
            scope_id=scope_id,
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            db=db,
            enforcement_mode=enforcement_mode
        )

        if not check_result.get("allowed"):
            return {
                "success": False,
                "allowed": False,
                "error": check_result.get("error", "Token budget exceeded"),
                "check_result": check_result
            }

        # Step 2: Execute LLM call
        try:
            result = await llm_call_func()

            # Extract tokens used from result if available
            tokens_used = None
            if isinstance(result, dict):
                tokens_used = result.get("tokens_used")
            elif hasattr(result, "tokens_used"):
                tokens_used = result.tokens_used

            # If no token info provided, use estimate
            if tokens_used is None:
                tokens_used = check_result.get("estimated_tokens", 0)

            # Step 3: Track after
            track_metadata = metadata or {}
            track_metadata["model"] = model
            track_metadata["estimated_tokens"] = check_result.get("estimated_tokens")

            await self.track_after_llm_call(
                scope_type=scope_type,
                scope_id=scope_id,
                tokens_used=tokens_used,
                db=db,
                user_id=user_id,
                metadata=track_metadata
            )

            return {
                "success": True,
                "allowed": True,
                "result": result,
                "tokens_used": tokens_used,
                "check_result": check_result
            }

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {
                "success": False,
                "allowed": True,
                "error": str(e),
                "check_result": check_result
            }

    def create_token_metadata(
        self,
        operation: str,
        test_definition_id: Optional[int] = None,
        test_run_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create metadata dictionary for token tracking.

        Args:
            operation: Operation type (script_generation, test_execution, etc.)
            test_definition_id: Optional test definition ID
            test_run_id: Optional test run ID
            **kwargs: Additional metadata fields

        Returns:
            Metadata dictionary
        """
        metadata = {
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if test_definition_id:
            metadata["test_definition_id"] = test_definition_id
        if test_run_id:
            metadata["test_run_id"] = test_run_id

        metadata.update(kwargs)
        return metadata

    async def get_workflow_token_status(
        self,
        scope_type: str,
        scope_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get current token status for a workflow scope.

        Args:
            scope_type: Scope type
            scope_id: Scope ID
            db: Database session

        Returns:
            Token status information
        """
        try:
            if not self.budget_service:
                return {"error": "Budget service not available"}

            result = await self.budget_service.get_budget_status(
                budget_id=scope_id,
                db=db
            )

            if hasattr(result, 'data'):
                return result.data
            return result

        except Exception as e:
            logger.error(f"Failed to get token status: {e}")
            return {"error": str(e)}

    def handle_token_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle token-related errors and return appropriate error response.

        Args:
            error: The exception that occurred
            context: Context information (scope_type, scope_id, etc.)

        Returns:
            Error response dict
        """
        if isinstance(error, TokenBudgetExceeded):
            return {
                "error": "token_budget_exceeded",
                "message": str(error),
                "scope_type": error.scope_type,
                "scope_id": error.scope_id,
                "requested_tokens": error.requested_tokens,
                "available_tokens": error.available_tokens,
                "enforcement_mode": error.enforcement_mode
            }
        elif isinstance(error, TokenQuotaExceeded):
            return {
                "error": "token_quota_exceeded",
                "message": str(error),
                "user_id": error.user_id,
                "tokens_used": error.tokens_used,
                "quota_limit": error.quota_limit
            }
        else:
            return {
                "error": "token_error",
                "message": str(error),
                "context": context
            }

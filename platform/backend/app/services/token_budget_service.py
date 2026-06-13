"""
Token Budget Service

Manages token budget operations following SOLID principles.
Handles budget checking, usage recording, status reporting, and hierarchy navigation.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.result_helpers import (
    service_success, service_error, not_found,
    validation_error, database_error,
    is_success, is_error
)
from app.core.error_codes import ErrorCode
from app.core.interfaces.metrics_collector_interface import IMetricsCollector
from app.models.token_budget import TokenBudget
from app.repositories.interfaces.token_budget_repository_interface import ITokenBudgetRepository
from app.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)


class TokenBudgetService:
    """
    Service for managing token budget operations.

    Responsibilities:
    - Check token availability before LLM calls
    - Record token usage after LLM calls
    - Get budget status and hierarchy
    - Calculate usage forecasts
    - Detect budget exhaustion

    Following SOLID principles:
    - Single Responsibility: Only handles budget operations
    - Open/Closed: Extensible through strategies
    - Liskov Substitution: Implements service interface properly
    - Interface Segregation: Focused, minimal interface
    - Dependency Inversion: Depends on repository interfaces
    """

    def __init__(
        self,
        budget_repository: Optional[ITokenBudgetRepository] = None,
        metrics_collector: Optional[IMetricsCollector] = None
    ):
        """
        Initialize Token Budget Service.

        Args:
            budget_repository: Token budget repository (created if not provided)
            metrics_collector: Optional metrics collector for instrumentation
        """
        self.budget_repository = budget_repository or RepositoryFactory.get_token_budget_repository()
        self.metrics_collector = metrics_collector
        self._record_metric = self._get_metric_recorder()

    def _get_metric_recorder(self):
        """Get metric recording function if metrics collector is available."""
        if self.metrics_collector:
            def record_metric(operation: str, duration_ms: float = 0):
                if duration_ms > 0:
                    self.metrics_collector.record_timing(operation, duration_ms)
                else:
                    self.metrics_collector.record_counter(f"token_budget.{operation}")
            return record_metric
        return None

    async def check_token_availability(
        self,
        scope_type: str,
        scope_id: Optional[int],
        requested_tokens: int,
        db: AsyncSession
    ) -> Any:
        """
        Check if tokens are available before making an LLM call.

        Args:
            scope_type: Scope type (organization, suite, test, user)
            scope_id: ID of the scoped entity
            requested_tokens: Number of tokens requested
            db: Database session

        Returns:
            ServiceSuccess with availability check result or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Validation
            if requested_tokens <= 0:
                return service_validation_error(
                    "Requested tokens must be positive",
                    error_code=ErrorCode.INVALID_VALUE
                )

            # Get budget for scope
            budget = await self.budget_repository.get_by_scope(
                scope_type, scope_id, db
            )

            if not budget:
                return not_found(
                    resource="TokenBudget",
                    identifier=f"{scope_type}:{scope_id}"
                )

            # Check if budget is active
            if budget.status != "active":
                return service_error(
                    f"Budget is not active (status: {budget.status})",
                    error_code=ErrorCode.OPERATION_NOT_ALLOWED,
                    details={
                        "budget_id": budget.id,
                        "status": budget.status,
                        "requested_tokens": requested_tokens
                    }
                )

            # Check if period is valid
            if budget.period_end and budget.period_end < datetime.utcnow():
                return service_error(
                    "Budget period has expired",
                    error_code=ErrorCode.RESOURCE_EXPIRED,
                    details={
                        "budget_id": budget.id,
                        "period_end": budget.period_end.isoformat()
                    }
                )

            # Calculate available tokens
            available_tokens = budget.remaining_tokens
            is_available = available_tokens >= requested_tokens
            usage_percentage = budget.usage_percentage

            # Build response
            result_data = {
                "available": is_available,
                "budget_id": budget.id,
                "scope_type": budget.scope_type,
                "scope_id": budget.scope_id,
                "requested_tokens": requested_tokens,
                "available_tokens": available_tokens,
                "total_tokens": budget.total_tokens,
                "used_tokens": budget.used_tokens,
                "usage_percentage": round(usage_percentage, 2),
                "enforcement_mode": budget.enforcement_mode,
                "is_near_limit": usage_percentage >= 80,
                "is_exhausted": budget.is_exhausted
            }

            # For hard enforcement, block if not available
            if budget.enforcement_mode == "hard" and not is_available:
                result_data["enforcement_action"] = "blocked"
                result_data["reason"] = "Insufficient tokens and enforcement mode is 'hard'"
            elif budget.enforcement_mode == "soft" and not is_available:
                result_data["enforcement_action"] = "warning"
                result_data["reason"] = "Insufficient tokens but enforcement mode is 'soft'"
            else:
                result_data["enforcement_action"] = "allowed"
                result_data["reason"] = "Sufficient tokens available"

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("check_token_availability", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error checking token availability: {e}")
            if self._record_metric:
                self._record_metric("check_token_availability_error")
            return database_error(
                message=f"Failed to check token availability: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR,
                details={"exception_type": type(e).__name__}
            )

    async def record_token_usage(
        self,
        scope_type: str,
        scope_id: Optional[int],
        tokens_used: int,
        db: AsyncSession,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Record token usage after an LLM call.

        Args:
            scope_type: Scope type (organization, suite, test, user)
            scope_id: ID of the scoped entity
            tokens_used: Number of tokens actually used
            db: Database session
            metadata: Optional metadata (test_run_id, user_id, etc.)

        Returns:
            ServiceSuccess with updated budget info or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Validation
            if tokens_used < 0:
                return service_validation_error(
                    "Tokens used cannot be negative",
                    error_code=ErrorCode.INVALID_VALUE
                )

            # Get budget for scope
            budget = await self.budget_repository.get_by_scope(
                scope_type, scope_id, db
            )

            if not budget:
                return not_found(
                    resource="TokenBudget",
                    identifier=f"{scope_type}:{scope_id}"
                )

            # Update usage
            await self.budget_repository.update_usage(
                budget.id, tokens_used, db
            )

            # Check if budget is now exhausted
            was_exhausted = budget.is_exhausted
            is_now_exhausted = budget.remaining_tokens <= 0

            # Check for threshold alerts
            triggered_alerts = budget.check_threshold_alerts()

            # Build response
            result_data = {
                "budget_id": budget.id,
                "scope_type": budget.scope_type,
                "scope_id": budget.scope_id,
                "tokens_used": tokens_used,
                "previous_used": budget.used_tokens - tokens_used,
                "current_used": budget.used_tokens,
                "remaining_tokens": budget.remaining_tokens,
                "total_tokens": budget.total_tokens,
                "usage_percentage": round(budget.usage_percentage, 2),
                "is_exhausted": is_now_exhausted,
                "was_exhausted": was_exhausted,
                "status": budget.status,
                "triggered_alerts": triggered_alerts,
                "metadata": metadata
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("record_token_usage", duration_ms)
                self.metrics_collector.record_counter("token_budget.tokens_used", tokens_used)
                if is_now_exhausted:
                    self.metrics_collector.record_counter("token_budget.exhausted")

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error recording token usage: {e}")
            if self._record_metric:
                self._record_metric("record_token_usage_error")
            return database_error(
                message=f"Failed to record token usage: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR,
                details={"exception_type": type(e).__name__}
            )

    async def get_budget_status(
        self,
        budget_id: int,
        db: AsyncSession
    ) -> Any:
        """
        Get current status of a token budget.

        Args:
            budget_id: Budget ID
            db: Database session

        Returns:
            ServiceSuccess with budget status or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            budget = await self.budget_repository.get_by_id(budget_id, db)

            if not budget:
                return not_found(
                    resource="TokenBudget",
                    identifier=str(budget_id)
                )

            # Build status response
            result_data = {
                "budget_id": budget.id,
                "name": budget.name,
                "description": budget.description,
                "scope_type": budget.scope_type,
                "scope_id": budget.scope_id,
                "parent_budget_id": budget.parent_budget_id,
                "period_type": budget.period_type,
                "period_start": budget.period_start.isoformat(),
                "period_end": budget.period_end.isoformat() if budget.period_end else None,
                "total_tokens": budget.total_tokens,
                "used_tokens": budget.used_tokens,
                "remaining_tokens": budget.remaining_tokens,
                "usage_percentage": round(budget.usage_percentage, 2),
                "priority": budget.priority,
                "enforcement_mode": budget.enforcement_mode,
                "status": budget.status,
                "is_exhausted": budget.is_exhausted,
                "is_near_limit": budget.is_near_limit(80),
                "inherit_from_parent": budget.inherit_from_parent,
                "alert_thresholds": budget.alert_thresholds,
                "created_at": budget.created_at.isoformat(),
                "updated_at": budget.updated_at.isoformat(),
                "last_reset_at": budget.last_reset_at.isoformat() if budget.last_reset_at else None
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("get_budget_status", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error getting budget status: {e}")
            if self._record_metric:
                self._record_metric("get_budget_status_error")
            return database_error(
                message=f"Failed to get budget status: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def get_budget_hierarchy(
        self,
        budget_id: int,
        db: AsyncSession,
        include_children: bool = True
    ) -> Any:
        """
        Get budget hierarchy (parents and optional children).

        Args:
            budget_id: Budget ID
            db: Database session
            include_children: Whether to include child budgets

        Returns:
            ServiceSuccess with hierarchy data or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Get the budget
            budget = await self.budget_repository.get_by_id(budget_id, db)

            if not budget:
                return not_found(
                    resource="TokenBudget",
                    identifier=str(budget_id)
                )

            # Get parent budgets
            parent_budgets = await self.budget_repository.get_parent_budgets(budget_id, db)

            # Get child budgets if requested
            child_budgets = []
            if include_children:
                child_budgets = await self.budget_repository.get_child_budgets(budget_id, db)

            # Build hierarchy response
            result_data = {
                "budget": {
                    "id": budget.id,
                    "name": budget.name,
                    "scope_type": budget.scope_type,
                    "scope_id": budget.scope_id,
                    "usage_percentage": round(budget.usage_percentage, 2),
                    "status": budget.status
                },
                "parents": [
                    {
                        "id": parent.id,
                        "name": parent.name,
                        "scope_type": parent.scope_type,
                        "scope_id": parent.scope_id,
                        "usage_percentage": round(parent.usage_percentage, 2),
                        "status": parent.status
                    }
                    for parent in parent_budgets
                ],
                "children": [
                    {
                        "id": child.id,
                        "name": child.name,
                        "scope_type": child.scope_type,
                        "scope_id": child.scope_id,
                        "usage_percentage": round(child.usage_percentage, 2),
                        "status": child.status
                    }
                    for child in child_budgets
                ],
                "level": len(parent_budgets),
                "has_children": len(child_budgets) > 0
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("get_budget_hierarchy", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error getting budget hierarchy: {e}")
            if self._record_metric:
                self._record_metric("get_budget_hierarchy_error")
            return database_error(
                message=f"Failed to get budget hierarchy: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def calculate_forecast(
        self,
        budget_id: int,
        db: AsyncSession,
        forecast_days: int = 30
    ) -> Any:
        """
        Calculate usage forecast for a budget.

        Args:
            budget_id: Budget ID
            db: Database session
            forecast_days: Number of days to forecast

        Returns:
            ServiceSuccess with forecast data or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            budget = await self.budget_repository.get_by_id(budget_id, db)

            if not budget:
                return not_found(
                    resource="TokenBudget",
                    identifier=str(budget_id)
                )

            # Calculate days remaining in period
            days_remaining = None
            if budget.period_end:
                days_remaining = max(0, (budget.period_end - datetime.utcnow()).days)

            # Calculate average daily usage
            days_in_period = 0
            if budget.period_start:
                days_in_period = max(1, (datetime.utcnow() - budget.period_start).days)

            avg_daily_usage = budget.used_tokens / max(1, days_in_period)

            # Calculate projected usage
            if days_remaining is not None:
                projected_usage = budget.used_tokens + (avg_daily_usage * days_remaining)
                projected_exhaustion = None

                if avg_daily_usage > 0:
                    days_until_exhaustion = budget.remaining_tokens / avg_daily_usage
                    projected_exhaustion = datetime.utcnow() + timedelta(days=days_until_exhaustion)

                will_exhaust = projected_usage >= budget.total_tokens
            else:
                projected_usage = None
                projected_exhaustion = None
                will_exhaust = None

            # Build forecast response
            result_data = {
                "budget_id": budget.id,
                "current_usage": {
                    "total_tokens": budget.total_tokens,
                    "used_tokens": budget.used_tokens,
                    "remaining_tokens": budget.remaining_tokens,
                    "usage_percentage": round(budget.usage_percentage, 2)
                },
                "usage_rate": {
                    "days_in_period": days_in_period,
                    "average_daily_usage": round(avg_daily_usage, 2)
                },
                "forecast": {
                    "days_remaining": days_remaining,
                    "projected_total_usage": round(projected_usage, 2) if projected_usage else None,
                    "will_exhaust": will_exhaust,
                    "projected_exhaustion_date": projected_exhaustion.isoformat() if projected_exhaustion else None
                }
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("calculate_forecast", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error calculating forecast: {e}")
            if self._record_metric:
                self._record_metric("calculate_forecast_error")
            return database_error(
                message=f"Failed to calculate forecast: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

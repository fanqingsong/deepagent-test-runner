"""
Token Quota Service

Manages user-specific token quota operations following SOLID principles.
Handles quota checking, usage recording, resets, and status reporting.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.result_helpers import (
    service_success, service_error, not_found,
    validation_error, database_error,
    is_success, is_error
)
from app.core.error_codes import ErrorCode
from app.core.interfaces.metrics_collector_interface import IMetricsCollector
from app.models.token_quota import TokenQuota
from app.models.user import User
from app.repositories.interfaces.token_quota_repository_interface import ITokenQuotaRepository
from app.repositories.repository_factory import RepositoryFactory

logger = logging.getLogger(__name__)


class TokenQuotaService:
    """
    Service for managing user-specific token quota operations.

    Responsibilities:
    - Check user quota availability
    - Record quota usage
    - Reset quotas based on time periods
    - Get quota status
    - Detect quota exhaustion

    Following SOLID principles:
    - Single Responsibility: Only handles quota operations
    - Open/Closed: Extensible through strategies
    - Liskov Substitution: Implements service interface properly
    - Interface Segregation: Focused, minimal interface
    - Dependency Inversion: Depends on repository interfaces
    """

    def __init__(
        self,
        quota_repository: Optional[ITokenQuotaRepository] = None,
        metrics_collector: Optional[IMetricsCollector] = None
    ):
        """
        Initialize Token Quota Service.

        Args:
            quota_repository: Token quota repository (created if not provided)
            metrics_collector: Optional metrics collector for instrumentation
        """
        self.quota_repository = quota_repository or RepositoryFactory.get_token_quota_repository()
        self.metrics_collector = metrics_collector
        self._record_metric = self._get_metric_recorder()

    def _get_metric_recorder(self):
        """Get metric recording function if metrics collector is available."""
        if self.metrics_collector:
            def record_metric(operation: str, duration_ms: float = 0):
                if duration_ms > 0:
                    self.metrics_collector.record_timing(operation, duration_ms)
                else:
                    self.metrics_collector.record_counter(f"token_quota.{operation}")
            return record_metric
        return None

    async def check_user_quota(
        self,
        user_id: int,
        requested_tokens: int,
        db: AsyncSession,
        quota_name: Optional[str] = None
    ) -> Any:
        """
        Check if user has sufficient quota tokens available.

        Args:
            user_id: User ID
            requested_tokens: Number of tokens requested
            db: Database session
            quota_name: Optional specific quota name to check

        Returns:
            ServiceSuccess with quota availability or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Validation
            if requested_tokens <= 0:
                return validation_error(
                    "Requested tokens must be positive",
                    error_code=ErrorCode.INVALID_VALUE
                )

            # Get user's quota
            quota = await self.quota_repository.get_by_user(
                user_id, db, quota_name=quota_name
            )

            if not quota:
                return not_found(
                    resource="TokenQuota",
                    identifier=f"user_id={user_id}, name={quota_name}"
                )

            # Check if quota is active
            if quota.status != "active":
                return service_error(
                    f"Quota is not active (status: {quota.status})",
                    error_code=ErrorCode.OPERATION_NOT_ALLOWED,
                    details={
                        "quota_id": quota.id,
                        "status": quota.status,
                        "user_id": user_id
                    }
                )

            # Check if period is valid
            if quota.period_end and quota.period_end < datetime.utcnow():
                return service_error(
                    "Quota period has expired",
                    error_code=ErrorCode.RESOURCE_EXPIRED,
                    details={
                        "quota_id": quota.id,
                        "period_end": quota.period_end.isoformat()
                    }
                )

            # Calculate available tokens
            available_tokens = quota.remaining_tokens
            is_available = available_tokens >= requested_tokens
            usage_percentage = quota.usage_percentage

            # Build response
            result_data = {
                "available": is_available,
                "quota_id": quota.id,
                "user_id": quota.user_id,
                "quota_name": quota.name,
                "requested_tokens": requested_tokens,
                "available_tokens": available_tokens,
                "total_tokens": quota.total_tokens,
                "used_tokens": quota.used_tokens,
                "usage_percentage": round(usage_percentage, 2),
                "enforcement_mode": quota.enforcement_mode,
                "is_near_limit": usage_percentage >= 80,
                "is_exhausted": quota.is_exhausted,
                "period_type": quota.period_type,
                "period_start": quota.period_start.isoformat(),
                "period_end": quota.period_end.isoformat() if quota.period_end else None
            }

            # Enforcement decision
            if quota.enforcement_mode == "hard" and not is_available:
                result_data["enforcement_action"] = "blocked"
                result_data["reason"] = "Insufficient tokens and enforcement mode is 'hard'"
            elif quota.enforcement_mode == "soft" and not is_available:
                result_data["enforcement_action"] = "warning"
                result_data["reason"] = "Insufficient tokens but enforcement mode is 'soft'"
            else:
                result_data["enforcement_action"] = "allowed"
                result_data["reason"] = "Sufficient tokens available"

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("check_user_quota", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error checking user quota: {e}")
            if self._record_metric:
                self._record_metric("check_user_quota_error")
            return database_error(
                message=f"Failed to check user quota: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR,
                details={"exception_type": type(e).__name__}
            )

    async def record_quota_usage(
        self,
        user_id: int,
        tokens_used: int,
        db: AsyncSession,
        quota_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Record token usage against user's quota.

        Args:
            user_id: User ID
            tokens_used: Number of tokens actually used
            db: Database session
            quota_name: Optional specific quota name
            metadata: Optional metadata (test_run_id, etc.)

        Returns:
            ServiceSuccess with updated quota info or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Validation
            if tokens_used < 0:
                return validation_error(
                    "Tokens used cannot be negative",
                    error_code=ErrorCode.INVALID_VALUE
                )

            # Get user's quota
            quota = await self.quota_repository.get_by_user(
                user_id, db, quota_name=quota_name
            )

            if not quota:
                return not_found(
                    resource="TokenQuota",
                    identifier=f"user_id={user_id}, name={quota_name}"
                )

            # Update usage
            await self.quota_repository.update_usage(
                quota.id, tokens_used, db
            )

            # Check if quota is now exhausted
            was_exhausted = quota.is_exhausted
            is_now_exhausted = quota.remaining_tokens <= 0

            # Check for threshold alerts
            triggered_alerts = quota.check_threshold_alerts()

            # Build response
            result_data = {
                "quota_id": quota.id,
                "user_id": quota.user_id,
                "quota_name": quota.name,
                "tokens_used": tokens_used,
                "previous_used": quota.used_tokens - tokens_used,
                "current_used": quota.used_tokens,
                "remaining_tokens": quota.remaining_tokens,
                "total_tokens": quota.total_tokens,
                "usage_percentage": round(quota.usage_percentage, 2),
                "is_exhausted": is_now_exhausted,
                "was_exhausted": was_exhausted,
                "status": quota.status,
                "triggered_alerts": triggered_alerts,
                "metadata": metadata
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("record_quota_usage", duration_ms)
                self.metrics_collector.record_counter("token_quota.tokens_used", tokens_used)
                if is_now_exhausted:
                    self.metrics_collector.record_counter("token_quota.exhausted")

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error recording quota usage: {e}")
            if self._record_metric:
                self._record_metric("record_quota_usage_error")
            return database_error(
                message=f"Failed to record quota usage: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR,
                details={"exception_type": type(e).__name__}
            )

    async def reset_quota(
        self,
        quota_id: int,
        db: AsyncSession,
        new_period_start: Optional[datetime] = None,
        new_period_end: Optional[datetime] = None
    ) -> Any:
        """
        Reset a quota's period and usage counters.

        Args:
            quota_id: Quota ID
            db: Database session
            new_period_start: New period start (default: now)
            new_period_end: New period end (optional)

        Returns:
            ServiceSuccess with reset quota info or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            quota = await self.quota_repository.get_by_id(quota_id, db)

            if not quota:
                return not_found(
                    resource="TokenQuota",
                    identifier=str(quota_id)
                )

            # Calculate new period if not provided
            if not new_period_start:
                new_period_start = datetime.utcnow()

                # Calculate period end based on period type
                if not new_period_end:
                    if quota.period_type == "daily":
                        new_period_end = new_period_start + timedelta(days=1)
                    elif quota.period_type == "weekly":
                        new_period_end = new_period_start + timedelta(weeks=1)
                    elif quota.period_type == "monthly":
                        # Add approximately 1 month
                        new_period_end = new_period_start + timedelta(days=30)

            # Reset the quota
            await self.quota_repository.reset_period(
                quota_id, new_period_start, new_period_end, db
            )

            # Build response
            result_data = {
                "quota_id": quota.id,
                "user_id": quota.user_id,
                "quota_name": quota.name,
                "period_type": quota.period_type,
                "new_period_start": new_period_start.isoformat(),
                "new_period_end": new_period_end.isoformat() if new_period_end else None,
                "previous_used_tokens": quota.used_tokens,
                "new_used_tokens": 0,
                "total_tokens": quota.total_tokens,
                "remaining_tokens": quota.total_tokens,
                "status": "active"
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("reset_quota", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error resetting quota: {e}")
            if self._record_metric:
                self._record_metric("reset_quota_error")
            return database_error(
                message=f"Failed to reset quota: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR,
                details={"exception_type": type(e).__name__}
            )

    async def get_quota_status(
        self,
        quota_id: int,
        db: AsyncSession
    ) -> Any:
        """
        Get current status of a token quota.

        Args:
            quota_id: Quota ID
            db: Database session

        Returns:
            ServiceSuccess with quota status or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            quota = await self.quota_repository.get_by_id(quota_id, db)

            if not quota:
                return not_found(
                    resource="TokenQuota",
                    identifier=str(quota_id)
                )

            # Build status response
            result_data = {
                "quota_id": quota.id,
                "user_id": quota.user_id,
                "name": quota.name,
                "description": quota.description,
                "period_type": quota.period_type,
                "reset_strategy": quota.reset_strategy,
                "period_start": quota.period_start.isoformat(),
                "period_end": quota.period_end.isoformat() if quota.period_end else None,
                "total_tokens": quota.total_tokens,
                "used_tokens": quota.used_tokens,
                "remaining_tokens": quota.remaining_tokens,
                "usage_percentage": round(quota.usage_percentage, 2),
                "priority": quota.priority,
                "enforcement_mode": quota.enforcement_mode,
                "status": quota.status,
                "is_exhausted": quota.is_exhausted,
                "is_near_limit": quota.is_near_limit(80),
                "alert_thresholds": quota.alert_thresholds,
                "created_at": quota.created_at.isoformat(),
                "updated_at": quota.updated_at.isoformat(),
                "last_reset_at": quota.last_reset_at.isoformat() if quota.last_reset_at else None
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("get_quota_status", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error getting quota status: {e}")
            if self._record_metric:
                self._record_metric("get_quota_status_error")
            return database_error(
                message=f"Failed to get quota status: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def get_user_all_quotas(
        self,
        user_id: int,
        db: AsyncSession,
        status_filter: Optional[str] = None
    ) -> Any:
        """
        Get all quotas for a user.

        Args:
            user_id: User ID
            db: Database session
            status_filter: Optional status filter (active, inactive, exhausted)

        Returns:
            ServiceSuccess with list of quotas or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            quotas = await self.quota_repository.get_by_user_all(
                user_id, db, status=status_filter
            )

            # Build response
            quotas_data = []
            for quota in quotas:
                quotas_data.append({
                    "quota_id": quota.id,
                    "name": quota.name,
                    "description": quota.description,
                    "period_type": quota.period_type,
                    "total_tokens": quota.total_tokens,
                    "used_tokens": quota.used_tokens,
                    "remaining_tokens": quota.remaining_tokens,
                    "usage_percentage": round(quota.usage_percentage, 2),
                    "status": quota.status,
                    "enforcement_mode": quota.enforcement_mode
                })

            result_data = {
                "user_id": user_id,
                "total_quotas": len(quotas_data),
                "quotas": quotas_data
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("get_user_all_quotas", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error getting user quotas: {e}")
            if self._record_metric:
                self._record_metric("get_user_all_quotas_error")
            return database_error(
                message=f"Failed to get user quotas: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

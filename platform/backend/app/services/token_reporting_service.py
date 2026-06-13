"""
Token Reporting Service

Manages token usage reporting and analytics following SOLID principles.
Handles report generation, cost calculation, usage analytics, and forecasting.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal

from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.result_helpers import (
    service_success, service_error, database_error
)
from app.core.error_codes import ErrorCode
from app.core.interfaces.metrics_collector_interface import IMetricsCollector
from app.models.llm_usage import LlmUsage
from app.models.token_budget import TokenBudget
from app.models.token_quota import TokenQuota
from app.models.token_alert import TokenAlert
from app.models.user import User

logger = logging.getLogger(__name__)


class TokenReportingService:
    """
    Service for managing token usage reporting and analytics.

    Responsibilities:
    - Generate usage reports (daily, weekly, monthly)
    - Calculate costs and forecast usage
    - Provide usage analytics (by scope, time, user)
    - Budget utilization metrics
    - Trend analysis and anomaly detection
    - Export functionality (CSV, JSON)

    Following SOLID principles:
    - Single Responsibility: Only handles reporting operations
    - Open/Closed: Extensible through report strategies
    - Liskov Substitution: Implements service interface properly
    - Interface Segregation: Focused, minimal interface
    - Dependency Inversion: Depends on repository interfaces
    """

    def __init__(
        self,
        metrics_collector: Optional[IMetricsCollector] = None
    ):
        """
        Initialize Token Reporting Service.

        Args:
            metrics_collector: Optional metrics collector for instrumentation
        """
        self.metrics_collector = metrics_collector
        self._record_metric = self._get_metric_recorder()

        # Cost per token (example pricing)
        self.cost_per_1k_tokens = 0.007  # $0.007 per 1K tokens

    def _get_metric_recorder(self):
        """Get metric recording function if metrics collector is available."""
        if self.metrics_collector:
            def record_metric(operation: str, duration_ms: float = 0):
                if duration_ms > 0:
                    self.metrics_collector.record_timing(operation, duration_ms)
                else:
                    self.metrics_collector.record_counter(f"token_reporting.{operation}")
            return record_metric
        return None

    async def generate_usage_report(
        self,
        db: AsyncSession,
        period_type: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None
    ) -> Any:
        """
        Generate token usage report for a specified period.

        Args:
            db: Database session
            period_type: Type of period (daily, weekly, monthly)
            start_date: Start date of report (default: today)
            end_date: End date of report (default: today)
            scope_type: Optional scope type filter
            scope_id: Optional scope ID filter

        Returns:
            ServiceSuccess with usage report or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Set default dates
            if not start_date:
                start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            if not end_date:
                end_date = start_date + timedelta(days=1)

            # Build query
            query = select(LlmUsage).where(
                and_(
                    LlmUsage.created_at >= start_date,
                    LlmUsage.created_at < end_date
                )
            )

            # Apply scope filters
            if scope_type:
                query = query.where(LlmUsage.scope_type == scope_type)
            if scope_id:
                query = query.where(LlmUsage.scope_id == scope_id)

            # Execute query
            result = await db.execute(query.order_by(desc(LlmUsage.created_at)))
            usage_records = result.scalars().all()

            # Calculate statistics
            total_tokens = sum(record.total_tokens or 0 for record in usage_records)
            total_prompt_tokens = sum(record.prompt_tokens or 0 for record in usage_records)
            total_completion_tokens = sum(record.completion_tokens or 0 for record in usage_records)
            total_cost = self._calculate_cost(total_tokens)
            total_calls = len(usage_records)

            # Group by agent type
            by_agent_type = {}
            for record in usage_records:
                agent_type = record.agent_type or "unknown"
                if agent_type not in by_agent_type:
                    by_agent_type[agent_type] = {
                        "total_tokens": 0,
                        "total_cost": 0.0,
                        "call_count": 0
                    }
                by_agent_type[agent_type]["total_tokens"] += record.total_tokens or 0
                by_agent_type[agent_type]["total_cost"] += self._calculate_cost(record.total_tokens or 0)
                by_agent_type[agent_type]["call_count"] += 1

            # Build report
            report_data = {
                "report_type": "usage_report",
                "period_type": period_type,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "scope": {
                    "type": scope_type,
                    "id": scope_id
                },
                "summary": {
                    "total_tokens": total_tokens,
                    "total_prompt_tokens": total_prompt_tokens,
                    "total_completion_tokens": total_completion_tokens,
                    "total_cost_rmb": round(total_cost, 4),
                    "total_llm_calls": total_calls,
                    "average_tokens_per_call": round(total_tokens / max(1, total_calls), 2)
                },
                "by_agent_type": by_agent_type,
                "records": [
                    {
                        "id": record.id,
                        "agent_type": record.agent_type,
                        "model_name": record.model_name,
                        "total_tokens": record.total_tokens,
                        "prompt_tokens": record.prompt_tokens,
                        "completion_tokens": record.completion_tokens,
                        "created_at": record.created_at.isoformat()
                    }
                    for record in usage_records[:100]  # Limit to 100 records for response
                ]
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("generate_usage_report", duration_ms)

            return service_success(data=report_data)

        except Exception as e:
            logger.error(f"Error generating usage report: {e}")
            if self._record_metric:
                self._record_metric("generate_usage_report_error")
            return database_error(
                message=f"Failed to generate usage report: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def calculate_costs(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None
    ) -> Any:
        """
        Calculate token costs for a specified period.

        Args:
            db: Database session
            start_date: Start date (default: beginning of current month)
            end_date: End date (default: now)
            scope_type: Optional scope type filter
            scope_id: Optional scope ID filter

        Returns:
            ServiceSuccess with cost breakdown or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Set default dates (current month)
            if not start_date:
                start_date = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            if not end_date:
                end_date = datetime.utcnow()

            # Build query
            query = select(LlmUsage).where(
                and_(
                    LlmUsage.created_at >= start_date,
                    LlmUsage.created_at <= end_date
                )
            )

            # Apply filters
            if scope_type:
                query = query.where(LlmUsage.scope_type == scope_type)
            if scope_id:
                query = query.where(LlmUsage.scope_id == scope_id)

            # Execute query
            result = await db.execute(query)
            usage_records = result.scalars().all()

            # Calculate costs
            total_cost = 0.0
            cost_by_model = {}
            cost_by_agent = {}
            cost_by_date = {}

            for record in usage_records:
                record_cost = self._calculate_cost(record.total_tokens or 0)
                total_cost += record_cost

                # By model
                model_name = record.model_name or "unknown"
                if model_name not in cost_by_model:
                    cost_by_model[model_name] = 0.0
                cost_by_model[model_name] += record_cost

                # By agent
                agent_type = record.agent_type or "unknown"
                if agent_type not in cost_by_agent:
                    cost_by_agent[agent_type] = 0.0
                cost_by_agent[agent_type] += record_cost

                # By date
                date_key = record.created_at.strftime("%Y-%m-%d")
                if date_key not in cost_by_date:
                    cost_by_date[date_key] = 0.0
                cost_by_date[date_key] += record_cost

            result_data = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "total_cost_rmb": round(total_cost, 4),
                "cost_breakdown": {
                    "by_model": {k: round(v, 4) for k, v in cost_by_model.items()},
                    "by_agent_type": {k: round(v, 4) for k, v in cost_by_agent.items()},
                    "by_date": {k: round(v, 4) for k, v in sorted(cost_by_date.items())}
                },
                "total_records": len(usage_records)
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("calculate_costs", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error calculating costs: {e}")
            if self._record_metric:
                self._record_metric("calculate_costs_error")
            return database_error(
                message=f"Failed to calculate costs: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def get_usage_analytics(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "agent_type",
        limit: int = 100
    ) -> Any:
        """
        Get usage analytics with grouping.

        Args:
            db: Database session
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: now)
            group_by: Grouping field (agent_type, model_name, scope_type)
            limit: Maximum number of groups to return

        Returns:
            ServiceSuccess with analytics data or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Set default dates
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)

            if not end_date:
                end_date = datetime.utcnow()

            # Build aggregation query
            group_field = getattr(LlmUsage, group_by, LlmUsage.agent_type)

            query = select(
                group_field.label("group_key"),
                func.count(LlmUsage.id).label("call_count"),
                func.sum(LlmUsage.total_tokens).label("total_tokens"),
                func.sum(LlmUsage.prompt_tokens).label("total_prompt_tokens"),
                func.sum(LlmUsage.completion_tokens).label("total_completion_tokens"),
                func.avg(LlmUsage.total_tokens).label("avg_tokens_per_call")
            ).where(
                and_(
                    LlmUsage.created_at >= start_date,
                    LlmUsage.created_at <= end_date
                )
            ).group_by(group_field).order_by(desc(func.sum(LlmUsage.total_tokens))).limit(limit)

            # Execute query
            result = await db.execute(query)
            analytics_rows = result.all()

            # Build analytics response
            analytics_data = []
            total_tokens_all = 0

            for row in analytics_rows:
                group_key = row.group_key or "unknown"
                row_tokens = row.total_tokens or 0
                total_tokens_all += row_tokens

                analytics_data.append({
                    "key": group_key,
                    "call_count": row.call_count,
                    "total_tokens": row_tokens,
                    "total_prompt_tokens": row.total_prompt_tokens or 0,
                    "total_completion_tokens": row.total_completion_tokens or 0,
                    "avg_tokens_per_call": round(row.avg_tokens_per_call or 0, 2),
                    "cost_rmb": round(self._calculate_cost(row_tokens), 4)
                })

            # Calculate percentages
            for item in analytics_data:
                item["percentage_of_total"] = round(
                    (item["total_tokens"] / max(1, total_tokens_all)) * 100, 2
                )

            result_data = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "group_by": group_by,
                "total_tokens": total_tokens_all,
                "total_cost_rmb": round(self._calculate_cost(total_tokens_all), 4),
                "analytics": analytics_data
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("get_usage_analytics", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error getting usage analytics: {e}")
            if self._record_metric:
                self._record_metric("get_usage_analytics_error")
            return database_error(
                message=f"Failed to get usage analytics: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def forecast_usage(
        self,
        db: AsyncSession,
        scope_type: Optional[str] = None,
        scope_id: Optional[int] = None,
        forecast_days: int = 30
    ) -> Any:
        """
        Forecast token usage based on historical data.

        Args:
            db: Database session
            scope_type: Optional scope type filter
            scope_id: Optional scope ID filter
            forecast_days: Number of days to forecast

        Returns:
            ServiceSuccess with usage forecast or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Calculate historical period (last 30 days)
            historical_start = datetime.utcnow() - timedelta(days=30)
            historical_end = datetime.utcnow()

            # Build query
            query = select(LlmUsage).where(
                and_(
                    LlmUsage.created_at >= historical_start,
                    LlmUsage.created_at <= historical_end
                )
            )

            # Apply filters
            if scope_type:
                query = query.where(LlmUsage.scope_type == scope_type)
            if scope_id:
                query = query.where(LlmUsage.scope_id == scope_id)

            # Execute query
            result = await db.execute(query)
            usage_records = result.scalars().all()

            if not usage_records:
                return service_success(data={
                    "message": "No historical data available for forecasting",
                    "forecast_days": forecast_days
                })

            # Calculate statistics
            total_tokens = sum(record.total_tokens or 0 for record in usage_records)
            days_in_period = 30  # Fixed to 30 days for simplicity
            avg_daily_usage = total_tokens / days_in_period

            # Calculate forecast
            forecasted_usage = avg_daily_usage * forecast_days
            forecasted_cost = self._calculate_cost(forecasted_usage)

            # Calculate trend (simple linear regression)
            # Group by day to see trend
            daily_usage = {}
            for record in usage_records:
                date_key = record.created_at.strftime("%Y-%m-%d")
                if date_key not in daily_usage:
                    daily_usage[date_key] = 0
                daily_usage[date_key] += record.total_tokens or 0

            sorted_days = sorted(daily_usage.keys())
            if len(sorted_days) >= 7:
                # Compare last 7 days to previous 7 days
                recent_7_days = sorted_days[-7:]
                previous_7_days = sorted_days[-14:-7] if len(sorted_days) >= 14 else sorted_days[:-7]

                recent_avg = sum(daily_usage[d] for d in recent_7_days) / len(recent_7_days)
                previous_avg = sum(daily_usage[d] for d in previous_7_days) / len(previous_7_days)

                trend_percentage = ((recent_avg - previous_avg) / max(0.01, previous_avg)) * 100
            else:
                trend_percentage = 0.0

            result_data = {
                "forecast_period": {
                    "days": forecast_days,
                    "start_date": datetime.utcnow().isoformat(),
                    "end_date": (datetime.utcnow() + timedelta(days=forecast_days)).isoformat()
                },
                "historical_data": {
                    "period_days": days_in_period,
                    "total_tokens": total_tokens,
                    "average_daily_usage": round(avg_daily_usage, 2),
                    "historical_records": len(usage_records)
                },
                "forecast": {
                    "forecasted_total_tokens": round(forecasted_usage, 2),
                    "forecasted_cost_rmb": round(forecasted_cost, 4),
                    "average_daily_forecast": round(avg_daily_usage, 2)
                },
                "trend": {
                    "trend_percentage": round(trend_percentage, 2),
                    "direction": "increasing" if trend_percentage > 5 else "decreasing" if trend_percentage < -5 else "stable"
                }
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("forecast_usage", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error forecasting usage: {e}")
            if self._record_metric:
                self._record_metric("forecast_usage_error")
            return database_error(
                message=f"Failed to forecast usage: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    async def get_budget_utilization(
        self,
        db: AsyncSession,
        budget_ids: Optional[List[int]] = None
    ) -> Any:
        """
        Get budget utilization metrics.

        Args:
            db: Database session
            budget_ids: Optional list of budget IDs to analyze

        Returns:
            ServiceSuccess with utilization metrics or ServiceError
        """
        import time
        start_time = time.perf_counter()

        try:
            # Build query
            query = select(TokenBudget).where(TokenBudget.status.in_(["active", "exhausted"]))

            if budget_ids:
                query = query.where(TokenBudget.id.in_(budget_ids))

            # Execute query
            result = await db.execute(query)
            budgets = result.scalars().all()

            # Calculate metrics
            total_budgets = len(budgets)
            active_budgets = sum(1 for b in budgets if b.status == "active")
            exhausted_budgets = sum(1 for b in budgets if b.status == "exhausted")
            total_allocated = sum(b.total_tokens for b in budgets)
            total_used = sum(b.used_tokens for b in budgets)
            total_remaining = sum(b.remaining_tokens for b in budgets)

            # Group by utilization level
            utilization_levels = {
                "under_50": 0,
                "between_50_and_80": 0,
                "between_80_and_95": 0,
                "over_95": 0
            }

            for budget in budgets:
                usage_pct = budget.usage_percentage
                if usage_pct < 50:
                    utilization_levels["under_50"] += 1
                elif usage_pct < 80:
                    utilization_levels["between_50_and_80"] += 1
                elif usage_pct < 95:
                    utilization_levels["between_80_and_95"] += 1
                else:
                    utilization_levels["over_95"] += 1

            # Detailed budget info
            budget_details = []
            for budget in budgets:
                budget_details.append({
                    "budget_id": budget.id,
                    "name": budget.name,
                    "scope_type": budget.scope_type,
                    "scope_id": budget.scope_id,
                    "total_tokens": budget.total_tokens,
                    "used_tokens": budget.used_tokens,
                    "remaining_tokens": budget.remaining_tokens,
                    "usage_percentage": round(budget.usage_percentage, 2),
                    "status": budget.status,
                    "is_exhausted": budget.is_exhausted
                })

            result_data = {
                "summary": {
                    "total_budgets": total_budgets,
                    "active_budgets": active_budgets,
                    "exhausted_budgets": exhausted_budgets,
                    "overall_utilization": round((total_used / max(1, total_allocated)) * 100, 2)
                },
                "tokens": {
                    "total_allocated": total_allocated,
                    "total_used": total_used,
                    "total_remaining": total_remaining
                },
                "utilization_distribution": utilization_levels,
                "budgets": budget_details
            }

            if self._record_metric:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._record_metric("get_budget_utilization", duration_ms)

            return service_success(data=result_data)

        except Exception as e:
            logger.error(f"Error getting budget utilization: {e}")
            if self._record_metric:
                self._record_metric("get_budget_utilization_error")
            return database_error(
                message=f"Failed to get budget utilization: {str(e)}",
                error_code=ErrorCode.DATABASE_ERROR
            )

    def _calculate_cost(self, tokens: int) -> float:
        """
        Calculate cost based on token usage.

        Args:
            tokens: Number of tokens

        Returns:
            Cost in RMB
        """
        return (tokens / 1000) * self.cost_per_1k_tokens

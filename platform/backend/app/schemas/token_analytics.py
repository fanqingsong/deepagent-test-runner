"""
Pydantic Schemas for Token Analytics

Request and response models for token analytics and forecasting.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TokenCostBreakdown(BaseModel):
    """Token cost breakdown by scope."""
    scope_type: str = Field(..., description="Scope type")
    scope_id: Optional[int] = Field(None, description="Scope ID")
    scope_name: Optional[str] = Field(None, description="Scope name")
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost: float = Field(..., description="Total cost in currency")
    average_cost_per_1k_tokens: float = Field(..., description="Average cost per 1k tokens")
    usage_count: int = Field(..., description="Number of usage records")


class TokenCostResponse(BaseModel):
    """Token cost analysis response."""
    period: Dict[str, Any] = Field(..., description="Analysis period")
    total_cost: float = Field(..., description="Total cost")
    total_tokens: int = Field(..., description="Total tokens used")
    cost_by_scope: List[TokenCostBreakdown] = Field(..., description="Cost breakdown by scope")
    cost_by_model: Dict[str, float] = Field(..., description="Cost by LLM model")
    cost_over_time: List[Dict[str, Any]] = Field(..., description="Cost over time series")


class TokenUsageTrend(BaseModel):
    """Single usage trend data point."""
    timestamp: datetime = Field(..., description="Timestamp")
    total_tokens: int = Field(..., description="Total tokens used")
    prompt_tokens: int = Field(..., description="Prompt tokens")
    completion_tokens: int = Field(..., description="Completion tokens")
    cost: float = Field(..., description="Estimated cost")


class TokenUsageTrendResponse(BaseModel):
    """Token usage trends response."""
    period: Dict[str, Any] = Field(..., description="Analysis period")
    granularity: str = Field(..., description="Time granularity (hourly, daily, weekly, monthly)")
    trends: List[TokenUsageTrend] = Field(..., description="Usage trend data points")
    summary: Dict[str, Any] = Field(..., description="Trend summary statistics")


class TokenForecast(BaseModel):
    """Token usage forecast."""
    budget_id: int = Field(..., description="Budget ID")
    current_usage: Dict[str, Any] = Field(..., description="Current usage statistics")
    usage_rate: Dict[str, Any] = Field(..., description="Usage rate calculations")
    forecast: Dict[str, Any] = Field(..., description="Forecast data")
    recommendations: List[str] = Field(default_factory=list, description="Usage recommendations")


class TokenModelUsage(BaseModel):
    """Token usage by model."""
    model_name: str = Field(..., description="LLM model name")
    total_tokens: int = Field(..., description="Total tokens used")
    prompt_tokens: int = Field(..., description="Total prompt tokens")
    completion_tokens: int = Field(..., description="Total completion tokens")
    usage_count: int = Field(..., description="Number of calls")
    total_cost: float = Field(..., description="Total cost")
    average_tokens_per_call: float = Field(..., description="Average tokens per call")


class TokenModelUsageResponse(BaseModel):
    """Token usage by model response."""
    period: Dict[str, Any] = Field(..., description="Analysis period")
    models: List[TokenModelUsage] = Field(..., description="Usage by model")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")


class TokenAgentUsage(BaseModel):
    """Token usage by agent type."""
    agent_type: str = Field(..., description="Agent type")
    total_tokens: int = Field(..., description="Total tokens used")
    usage_count: int = Field(..., description="Number of agent executions")
    total_cost: float = Field(..., description="Total cost")
    average_tokens_per_execution: float = Field(..., description="Average tokens per execution")


class TokenAgentUsageResponse(BaseModel):
    """Token usage by agent response."""
    period: Dict[str, Any] = Field(..., description="Analysis period")
    agents: List[TokenAgentUsage] = Field(..., description="Usage by agent")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")


class TokenBudgetComparison(BaseModel):
    """Budget comparison data."""
    budget_id: int = Field(..., description="Budget ID")
    name: str = Field(..., description="Budget name")
    scope_type: str = Field(..., description="Scope type")
    usage_percentage: float = Field(..., description="Usage percentage")
    total_tokens: int = Field(..., description="Total tokens")
    used_tokens: int = Field(..., description="Used tokens")
    remaining_tokens: int = Field(..., description="Remaining tokens")
    status: str = Field(..., description="Budget status")


class TokenComparisonResponse(BaseModel):
    """Budget comparison response."""
    budgets: List[TokenBudgetComparison] = Field(..., description="Budget comparisons")
    total_budgets: int = Field(..., description="Number of budgets compared")
    generated_at: datetime = Field(..., description="Generation timestamp")


class TokenUsageSummary(BaseModel):
    """Token usage summary."""
    period: Dict[str, Any] = Field(..., description="Analysis period")
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost: float = Field(..., description="Total estimated cost")
    total_calls: int = Field(..., description="Total API calls")
    average_tokens_per_call: float = Field(..., description="Average tokens per call")
    breakdown_by_type: Dict[str, int] = Field(..., description="Breakdown by token type")
    breakdown_by_model: Dict[str, int] = Field(..., description="Breakdown by model")
    breakdown_by_agent: Dict[str, int] = Field(..., description="Breakdown by agent")


class TokenScopeUsage(BaseModel):
    """Token usage by scope."""
    scope_type: str = Field(..., description="Scope type")
    scope_id: Optional[int] = Field(None, description="Scope ID")
    scope_name: Optional[str] = Field(None, description="Scope name")
    total_tokens: int = Field(..., description="Total tokens used")
    usage_count: int = Field(..., description="Number of operations")
    trend: List[Dict[str, Any]] = Field(default_factory=list, description="Usage trend")


class TokenScopeUsageResponse(BaseModel):
    """Token usage by scope response."""
    period: Dict[str, Any] = Field(..., description="Analysis period")
    scope_type: str = Field(..., description="Scope type analyzed")
    group_by: str = Field(..., description="Grouping period")
    scopes: List[TokenScopeUsage] = Field(..., description="Usage by scope")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")


class TokenPerformanceMetrics(BaseModel):
    """Budget performance metrics."""
    budget_id: int = Field(..., description="Budget ID")
    budget_name: str = Field(..., description="Budget name")
    performance: Dict[str, Any] = Field(..., description="Performance metrics")
    period: Dict[str, Any] = Field(..., description="Period information")
    enforcement: Dict[str, Any] = Field(..., description="Enforcement information")


class TokenAlertConfig(BaseModel):
    """Alert configuration."""
    email_notifications_enabled: bool = Field(..., description="Email notifications enabled")
    webhook_notifications_enabled: bool = Field(..., description="Webhook notifications enabled")
    webhook_url: Optional[str] = Field(None, description="Webhook URL")
    updated_at: datetime = Field(..., description="Last update timestamp")
    updated_by: int = Field(..., description="User ID who updated")


class TokenAlertConfigResponse(BaseModel):
    """Alert configuration response."""
    message: str = Field(..., description="Response message")
    config: TokenAlertConfig = Field(..., description="Alert configuration")


class TokenAlertStats(BaseModel):
    """Alert statistics."""
    period: Dict[str, Any] = Field(..., description="Analysis period")
    total_alerts: int = Field(..., description="Total alerts")
    by_severity: Dict[str, int] = Field(..., description="Alerts by severity")
    by_type: Dict[str, int] = Field(..., description="Alerts by type")
    acknowledged: int = Field(..., description="Acknowledged alerts")
    unacknowledged: int = Field(..., description="Unacknowledged alerts")
    acknowledgement_rate: float = Field(..., description="Acknowledgement rate percentage")


class TokenUsageForecastRequest(BaseModel):
    """Request for usage forecast."""
    budget_id: int = Field(..., description="Budget ID to forecast")
    forecast_days: int = Field(default=30, ge=1, le=365, description="Days to forecast")


class TokenUsageForecastResponse(BaseModel):
    """Usage forecast response."""
    forecast: TokenForecast = Field(..., description="Forecast data")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")

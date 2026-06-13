"""
Pydantic Schemas for Token Budget System

Request and response models for token budget, quota, and alert API endpoints.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Token Budget Schemas
# =============================================================================

class TokenBudgetBase(BaseModel):
    """Base schema for token budget."""
    name: str = Field(..., min_length=1, max_length=255, description="Budget name")
    description: Optional[str] = Field(None, max_length=500, description="Budget description")
    scope_type: str = Field(..., description="Scope type: organization, suite, test, user")
    scope_id: Optional[int] = Field(None, description="ID of the scoped entity")
    parent_budget_id: Optional[int] = Field(None, description="Parent budget for inheritance")
    period_type: str = Field(default="monthly", description="Period: hourly, daily, weekly, monthly")
    period_start: datetime = Field(default_factory=datetime.utcnow, description="Period start")
    period_end: Optional[datetime] = Field(None, description="Period end")
    total_tokens: int = Field(..., ge=0, description="Total token budget")
    priority: int = Field(default=5, ge=1, le=10, description="Priority (1-10)")
    enforcement_mode: str = Field(default="soft", description="Enforcement: soft, hard, monitoring")
    status: str = Field(default="active", description="Status: active, inactive, exhausted")
    inherit_from_parent: bool = Field(default=False, description="Inherit from parent")
    inherit_strategy: Optional[str] = Field(None, description="Inherit strategy")
    alert_thresholds: Dict[str, float] = Field(
        default={"warning": 80, "critical": 90, "emergency": 95},
        description="Alert thresholds as percentages"
    )
    config_data: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration data")

    @field_validator('scope_type')
    @classmethod
    def validate_scope_type(cls, v: str) -> str:
        """Validate scope type."""
        allowed = {'organization', 'suite', 'test', 'user'}
        if v not in allowed:
            raise ValueError(f"scope_type must be one of {allowed}")
        return v

    @field_validator('period_type')
    @classmethod
    def validate_period_type(cls, v: str) -> str:
        """Validate period type."""
        allowed = {'hourly', 'daily', 'weekly', 'monthly', 'custom'}
        if v not in allowed:
            raise ValueError(f"period_type must be one of {allowed}")
        return v

    @field_validator('enforcement_mode')
    @classmethod
    def validate_enforcement_mode(cls, v: str) -> str:
        """Validate enforcement mode."""
        allowed = {'soft', 'hard', 'monitoring'}
        if v not in allowed:
            raise ValueError(f"enforcement_mode must be one of {allowed}")
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status."""
        allowed = {'active', 'inactive', 'exhausted'}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


class TokenBudgetCreate(TokenBudgetBase):
    """Schema for creating a token budget."""
    pass


class TokenBudgetUpdate(BaseModel):
    """Schema for updating a token budget."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    period_type: Optional[str] = Field(None, description="Period: hourly, daily, weekly, monthly")
    period_start: Optional[datetime] = Field(None, description="Period start")
    period_end: Optional[datetime] = Field(None, description="Period end")
    total_tokens: Optional[int] = Field(None, ge=0)
    priority: Optional[int] = Field(None, ge=1, le=10)
    enforcement_mode: Optional[str] = Field(None, description="Enforcement: soft, hard, monitoring")
    status: Optional[str] = Field(None, description="Status: active, inactive, exhausted")
    inherit_from_parent: Optional[bool] = Field(None)
    inherit_strategy: Optional[str] = Field(None)
    alert_thresholds: Optional[Dict[str, float]] = Field(None, description="Alert thresholds")
    config_data: Optional[Dict[str, Any]] = Field(None)


class TokenBudgetResponse(TokenBudgetBase):
    """Schema for token budget response."""
    id: int
    used_tokens: int = 0
    remaining_tokens: int = 0
    created_at: datetime
    updated_at: datetime
    last_reset_at: Optional[datetime] = None
    usage_percentage: float = 0.0

    model_config = {"from_attributes": True}


class TokenBudgetListResponse(BaseModel):
    """Schema for paginated token budget list."""
    items: List[TokenBudgetResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TokenBudgetUsageUpdate(BaseModel):
    """Request to update token usage."""
    tokens_used: int = Field(..., gt=0, description="Number of tokens to add")


class TokenBudgetPeriodReset(BaseModel):
    """Request to reset budget period."""
    new_period_start: datetime = Field(..., description="Start of new period")
    new_period_end: Optional[datetime] = Field(None, description="End of new period")


# =============================================================================
# Token Quota Schemas
# =============================================================================

class TokenQuotaBase(BaseModel):
    """Base schema for token quota."""
    user_id: int = Field(..., description="User ID")
    name: str = Field(..., min_length=1, max_length=255, description="Quota name")
    description: Optional[str] = Field(None, max_length=500, description="Quota description")
    period_type: str = Field(default="daily", description="Period: daily, weekly, monthly")
    reset_strategy: str = Field(default="calendar", description="Reset strategy: rolling, calendar")
    period_start: datetime = Field(default_factory=datetime.utcnow, description="Period start")
    period_end: Optional[datetime] = Field(None, description="Period end")
    total_tokens: int = Field(..., ge=0, description="Total token quota")
    priority: int = Field(default=5, ge=1, le=10, description="Priority (1-10)")
    enforcement_mode: str = Field(default="soft", description="Enforcement: soft, hard, monitoring")
    status: str = Field(default="active", description="Status: active, inactive, exhausted")
    alert_thresholds: Dict[str, float] = Field(
        default={"warning": 80, "critical": 90, "emergency": 95},
        description="Alert thresholds as percentages"
    )
    config_data: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration data")

    @field_validator('period_type')
    @classmethod
    def validate_period_type(cls, v: str) -> str:
        """Validate period type."""
        allowed = {'daily', 'weekly', 'monthly'}
        if v not in allowed:
            raise ValueError(f"period_type must be one of {allowed}")
        return v

    @field_validator('reset_strategy')
    @classmethod
    def validate_reset_strategy(cls, v: str) -> str:
        """Validate reset strategy."""
        allowed = {'rolling', 'calendar'}
        if v not in allowed:
            raise ValueError(f"reset_strategy must be one of {allowed}")
        return v


class TokenQuotaCreate(TokenQuotaBase):
    """Schema for creating a token quota."""
    pass


class TokenQuotaUpdate(BaseModel):
    """Schema for updating a token quota."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    period_type: Optional[str] = Field(None)
    reset_strategy: Optional[str] = Field(None)
    period_start: Optional[datetime] = Field(None)
    period_end: Optional[datetime] = Field(None)
    total_tokens: Optional[int] = Field(None, ge=0)
    priority: Optional[int] = Field(None, ge=1, le=10)
    enforcement_mode: Optional[str] = Field(None)
    status: Optional[str] = Field(None)
    alert_thresholds: Optional[Dict[str, float]] = Field(None)
    config_data: Optional[Dict[str, Any]] = Field(None)


class TokenQuotaResponse(TokenQuotaBase):
    """Schema for token quota response."""
    id: int
    used_tokens: int = 0
    remaining_tokens: int = 0
    created_at: datetime
    updated_at: datetime
    last_reset_at: Optional[datetime] = None
    usage_percentage: float = 0.0

    model_config = {"from_attributes": True}


class TokenQuotaListResponse(BaseModel):
    """Schema for paginated token quota list."""
    items: List[TokenQuotaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Token Alert Schemas
# =============================================================================

class TokenAlertBase(BaseModel):
    """Base schema for token alert."""
    alert_type: str = Field(..., description="Alert type")
    severity: str = Field(default="warning", description="Severity: info, warning, critical, emergency")
    budget_id: Optional[int] = Field(None, description="Associated budget ID")
    quota_id: Optional[int] = Field(None, description="Associated quota ID")
    user_id: Optional[int] = Field(None, description="Associated user ID")
    threshold_type: str = Field(default="percentage", description="Threshold type: percentage, absolute")
    threshold_value: float = Field(..., description="Threshold that was triggered")
    current_value: float = Field(..., description="Current value when triggered")
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Metrics snapshot")
    message: str = Field(..., description="Alert message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    enforcement_action: Optional[str] = Field(None, description="Action taken")
    enforcement_result: Dict[str, Any] = Field(default_factory=dict, description="Enforcement result")

    @field_validator('alert_type')
    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        """Validate alert type."""
        allowed = {'budget_warning', 'budget_exceeded', 'quota_warning', 'quota_exceeded', 'enforcement_action'}
        if v not in allowed:
            raise ValueError(f"alert_type must be one of {allowed}")
        return v

    @field_validator('severity')
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity."""
        allowed = {'info', 'warning', 'critical', 'emergency'}
        if v not in allowed:
            raise ValueError(f"severity must be one of {allowed}")
        return v


class TokenAlertCreate(TokenAlertBase):
    """Schema for creating a token alert."""
    pass


class TokenAlertResponse(TokenAlertBase):
    """Schema for token alert response."""
    id: int
    is_acknowledged: bool = False
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    notifications_sent: Dict[str, bool] = Field(default_factory=dict)
    notification_errors: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenAlertListResponse(BaseModel):
    """Schema for paginated token alert list."""
    items: List[TokenAlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TokenAlertAcknowledge(BaseModel):
    """Request to acknowledge an alert."""
    acknowledged: bool = Field(..., description="Acknowledgment status")


class TokenAlertResolve(BaseModel):
    """Request to resolve an alert."""
    resolved: bool = Field(..., description="Resolution status")


# =============================================================================
# Token Usage Schemas
# =============================================================================

class TokenUsageResponse(BaseModel):
    """Schema for token usage with budget/quota tracking."""
    id: int
    agent_type: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    duration_ms: int
    cost_rmb: Optional[float] = None
    budget_id: Optional[int] = None
    quota_id: Optional[int] = None
    priority: Optional[int] = None
    enforcement_action: Optional[str] = None
    user_id: Optional[int] = None
    test_run_id: Optional[str] = None
    thread_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenUsageEnforcementRequest(BaseModel):
    """Request to check token usage enforcement."""
    agent_type: str = Field(..., description="Agent type")
    estimated_tokens: int = Field(..., gt=0, description="Estimated tokens to use")
    user_id: Optional[int] = Field(None, description="User ID")
    test_definition_id: Optional[int] = Field(None, description="Test definition ID")
    test_suite_id: Optional[int] = Field(None, description="Test suite ID")


class TokenUsageEnforcementResponse(BaseModel):
    """Response from token usage enforcement check."""
    allowed: bool = Field(..., description="Whether usage is allowed")
    enforcement_action: Optional[str] = Field(None, description="Action taken")
    budget_id: Optional[int] = Field(None, description="Budget ID if applicable")
    quota_id: Optional[int] = Field(None, description="Quota ID if applicable")
    remaining_tokens: int = Field(..., description="Remaining tokens")
    usage_percentage: float = Field(..., description="Current usage percentage")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")

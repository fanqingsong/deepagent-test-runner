"""
Pydantic Schemas for Test Suite Management
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SuiteEntry(BaseModel):
    """A single test entry within a suite."""
    test_definition_id: int
    order: int
    enabled: bool = True
    depends_on: List[int] = Field(default_factory=list)
    condition: str = Field(default="always", pattern="^(always|on_success|on_failure)$")


class TestSuiteBase(BaseModel):
    """Base schema for TestSuite"""
    name: str = Field(..., min_length=1, max_length=255, description="Suite name")
    description: Optional[str] = Field(None, description="Suite description")
    test_definition_ids: List[int] = Field(
        default_factory=list,
        description="List of test definition IDs in this suite"
    )
    tags: dict = Field(default_factory=dict, description="Metadata tags")
    execution_mode: str = Field(default="sequential", pattern="^(sequential|parallel)$")
    max_concurrency: int = Field(default=1, ge=1, le=10)
    fail_strategy: str = Field(default="continue", pattern="^(continue|fail_fast)$")
    retry_config: Dict[str, Any] = Field(default_factory=dict)
    environment_vars: Dict[str, Any] = Field(default_factory=dict)
    suite_entries: List[SuiteEntry] = Field(default_factory=list)

    # Dynamic suite support
    is_dynamic: bool = False
    dynamic_tag_rule: Dict[str, Any] = Field(default_factory=dict)

    # Setup/teardown
    setup_test_id: Optional[int] = None
    teardown_test_id: Optional[int] = None

    # Schedule configuration
    schedule_enabled: bool = False
    cron_expression: Optional[str] = None
    timezone: str = "Asia/Shanghai"
    schedule_allow_concurrent: bool = False
    schedule_max_retries: int = Field(default=0, ge=0, le=10)
    schedule_retry_interval: int = Field(default=60, ge=10, le=3600)


class TestSuiteCreate(TestSuiteBase):
    """Schema for creating a new test suite"""
    pass


class TestSuiteUpdate(BaseModel):
    """Schema for updating a test suite"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    test_definition_ids: Optional[List[int]] = Field(None, min_length=1)
    tags: Optional[dict] = None
    execution_mode: Optional[str] = Field(None, pattern="^(sequential|parallel)$")
    max_concurrency: Optional[int] = Field(None, ge=1, le=10)
    fail_strategy: Optional[str] = Field(None, pattern="^(continue|fail_fast)$")
    retry_config: Optional[Dict[str, Any]] = None
    environment_vars: Optional[Dict[str, Any]] = None
    suite_entries: Optional[List[SuiteEntry]] = None
    is_dynamic: Optional[bool] = None
    dynamic_tag_rule: Optional[Dict[str, Any]] = None
    setup_test_id: Optional[int] = None
    teardown_test_id: Optional[int] = None
    schedule_enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    schedule_allow_concurrent: Optional[bool] = None
    schedule_max_retries: Optional[int] = Field(None, ge=0, le=10)
    schedule_retry_interval: Optional[int] = Field(None, ge=10, le=3600)


class TestSuiteResponse(TestSuiteBase):
    """Schema for test suite response"""
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    schedule_id: Optional[int] = None
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    review_status: str = "draft"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

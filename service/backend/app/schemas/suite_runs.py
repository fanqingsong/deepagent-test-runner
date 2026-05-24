"""
Pydantic Schemas for Suite Run Management
"""

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class SuiteRunEntryResponse(BaseModel):
    """Single entry within a suite run."""
    id: int
    suite_run_id: int
    test_definition_id: int
    test_run_id: Optional[str] = None
    entry_order: int
    status: str
    condition: str = "always"
    started_at: Optional[int] = None
    finished_at: Optional[int] = None
    duration: Optional[int] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SuiteRunResponse(BaseModel):
    """Full suite run with entries."""
    id: int
    suite_id: int
    run_id: str
    status: str
    execution_mode: str = "sequential"
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    error: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    total_duration: Optional[int] = None
    environment: dict = Field(default_factory=dict)
    triggered_by: str = "manual"
    created_at: datetime
    entries: List[SuiteRunEntryResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SuiteRunListResponse(BaseModel):
    """Suite run without entries (for list views)."""
    id: int
    suite_id: int
    run_id: str
    status: str
    execution_mode: str = "sequential"
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    total_duration: Optional[int] = None
    triggered_by: str = "manual"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuiteRunTriggerResponse(BaseModel):
    """Response after triggering a suite run."""
    run_id: str
    status: str = "pending"


class SuiteRunTriggerRequest(BaseModel):
    """Request body for triggering a suite run."""
    environment: dict = Field(default_factory=dict)

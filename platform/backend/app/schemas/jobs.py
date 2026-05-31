"""
Pydantic Schemas for Job Management

Request and response models for test execution jobs.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    """Schema for creating a new job."""
    test_definition_ids: List[int] = Field(..., description="List of test definition IDs to execute")
    environment: Dict[str, Any] = Field(default_factory=dict, description="Environment variables for tests")
    priority: int = Field(default=5, ge=1, le=10, description="Job priority (1-10, 10 is highest)")
    scheduled: bool = Field(default=False, description="Whether this is a scheduled job")


class JobResponse(BaseModel):
    """Schema for job response."""
    job_id: str
    status: str
    test_definition_ids: List[int]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


class JobStatusResponse(BaseModel):
    """Schema for job status."""
    job_id: str
    status: str
    progress: float  # 0.0 to 1.0
    message: Optional[str] = None
    results: Optional[Dict[str, Any]] = None

"""
Pydantic Schemas for Suite Versions

Request and response models for suite version API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TestSuiteVersionSnapshot(BaseModel):
    """Schema for suite version snapshot response."""
    id: int
    test_suite_id: int
    version: int
    snapshot: dict = Field(default_factory=dict, description="Full suite configuration snapshot")
    change_description: Optional[str] = None
    review_status: str = "draft"
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    created_by: str = "system"

    model_config = {"from_attributes": True}

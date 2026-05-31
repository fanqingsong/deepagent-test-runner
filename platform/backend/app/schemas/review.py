"""
Pydantic Schemas for Review/Approval Workflow
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ReviewActionRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for rejection (required for reject)")


class ReviewItemResponse(BaseModel):
    id: int
    type: str  # "test" or "suite"
    name: str
    description: Optional[str] = None
    review_status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    version_id: Optional[int] = None
    version_number: Optional[int] = None

    model_config = {"from_attributes": True}


class PendingReviewListResponse(BaseModel):
    tests: List[ReviewItemResponse] = Field(default_factory=list)
    suites: List[ReviewItemResponse] = Field(default_factory=list)

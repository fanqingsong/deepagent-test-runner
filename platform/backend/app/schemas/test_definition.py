"""
Pydantic Schemas for Test Definitions

Request and response models for test definition API endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TestStepBase(BaseModel):
    """Base schema for test step."""
    step_number: int = Field(..., ge=1, description="Step order number")
    description: str = Field(..., min_length=1, description="Step description")
    type: str = Field(..., min_length=1, description="Step type (e.g., 'navigate', 'click', 'fill')")
    params: dict = Field(default_factory=dict, description="Step parameters")
    expected_result: Optional[str] = Field(None, description="Expected result of this step")


class TestStepCreate(TestStepBase):
    """Schema for creating a test step."""
    pass


class TestStepUpdate(BaseModel):
    """Schema for updating a test step."""
    step_number: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, min_length=1)
    type: Optional[str] = Field(None, min_length=1)
    params: Optional[dict] = None
    expected_result: Optional[str] = None


class TestStepResponse(TestStepBase):
    """Schema for test step response."""
    id: int
    test_definition_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TestStepsReplaceRequest(BaseModel):
    """Schema for replacing all test steps of a test definition."""

    test_steps: List[TestStepCreate] = Field(
        default_factory=list,
        description="Full replacement set of test steps (existing steps will be deleted)",
    )


class TestDefinitionBase(BaseModel):
    """Base schema for test definition."""
    name: str = Field(..., min_length=1, max_length=255, description="Test name")
    description: Optional[str] = Field(None, description="Test description")
    test_id: str = Field(..., min_length=1, max_length=100, description="Unique test identifier")
    url: Optional[str] = Field(None, max_length=500, description="Base URL for test")
    environment: dict = Field(default_factory=dict, description="Environment variables")
    tags: List[str] = Field(default_factory=list, description="Test tags")
    test_goal: Optional[str] = Field(None, description="AI planning: Natural language test goal")
    test_context: dict = Field(default_factory=dict, description="AI planning: Additional context")


class TestDefinitionCreate(TestDefinitionBase):
    """Schema for creating a test definition."""
    test_steps: List[TestStepCreate] = Field(
        default_factory=list,
        description="Test steps for this definition (optional if using AI planning)"
    )


class TestDefinitionUpdate(BaseModel):
    """Schema for updating a test definition."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    url: Optional[str] = Field(None, max_length=500)
    environment: Optional[dict] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    test_goal: Optional[str] = Field(None, description="AI planning: Natural language test goal")
    test_context: Optional[dict] = Field(None, description="AI planning: Additional context")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """Ensure tags list doesn't contain duplicates."""
        if v is not None:
            return list(set(v))
        return v


class TestDefinitionResponse(TestDefinitionBase):
    """Schema for test definition response."""
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None  # Allow None for unauthenticated/system-created tests
    version: int
    is_active: bool
    test_steps: List[TestStepResponse] = []

    model_config = {"from_attributes": True}


class TestDefinitionListResponse(BaseModel):
    """Schema for paginated test definition list."""
    items: List[TestDefinitionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TestVersionSnapshot(BaseModel):
    """Schema for test version snapshot."""
    id: int
    test_definition_id: int
    version: int
    snapshot: dict
    change_description: Optional[str]
    created_at: datetime
    created_by: int

    model_config = {"from_attributes": True}

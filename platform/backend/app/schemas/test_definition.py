"""
Pydantic Schemas for Test Definitions

Request and response models for test definition API endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


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
    execution_mode: str = Field(default="script", description="Execution mode: 'script'")


class TestDefinitionCreate(TestDefinitionBase):
    """Schema for creating a test definition."""
    pass


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
    execution_mode: Optional[str] = Field(None, description="Execution mode: 'script'")

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
    created_by: Optional[int] = None
    version: int
    is_active: bool
    playwright_script: Optional[str] = None
    script_status: str = "none"
    script_metadata: dict = {}

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


class ScriptGenerationRequest(BaseModel):
    """Request to generate a Playwright script."""
    force_regenerate: bool = Field(default=False, description="Regenerate even if script exists")


class ScriptResponse(BaseModel):
    """Response with script content and metadata."""
    playwright_script: Optional[str] = None
    script_status: str
    script_metadata: dict = {}
    execution_mode: str

    model_config = {"from_attributes": True}


class ScriptUpdateRequest(BaseModel):
    """Update script content (user edits)."""
    playwright_script: str = Field(..., min_length=1)

"""
Pydantic Schemas for App API Endpoints

Request and response models for the LLM-APP-style test workspace.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AppCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="APP name")
    description: Optional[str] = Field(None, description="APP description")
    url: str = Field(..., min_length=1, max_length=500, description="Target URL")
    test_goal: str = Field(..., min_length=1, description="Natural language test goal")
    test_context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    icon: str = Field(default="test-tube", max_length=50, description="APP icon identifier")
    color: str = Field(default="#0f62fe", max_length=20, description="APP accent color")


class AppUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    test_goal: Optional[str] = None
    test_context: Optional[Dict[str, Any]] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    current_plan: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class AppSummaryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    status: str
    test_goal: Optional[str] = None
    icon: str
    color: str
    iteration_count: int = 0
    latest_result: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    status: str
    test_goal: Optional[str] = None
    test_context: Dict[str, Any] = Field(default_factory=dict)
    current_plan: Dict[str, Any] = Field(default_factory=dict)
    test_definition_id: Optional[int] = None
    latest_run_id: Optional[str] = None
    latest_result: Dict[str, Any] = Field(default_factory=dict)
    iteration_count: int = 0
    icon: str
    color: str
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AppRunRequest(BaseModel):
    force_regenerate: bool = Field(
        default=False, description="Force regenerate plan even if one exists"
    )
    use_existing_plan: bool = Field(
        default=False, description="Use current_plan as-is without regeneration"
    )


class AppRefineRequest(BaseModel):
    feedback: str = Field(..., min_length=1, description="User feedback for plan refinement")


class AppRunResponse(BaseModel):
    job_id: str
    run_id: str
    status: str


class AppPublishResponse(BaseModel):
    app_id: int
    test_definition_id: int
    test_id: str
    name: str
    status: str

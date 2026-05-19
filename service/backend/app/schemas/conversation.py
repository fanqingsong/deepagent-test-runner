"""
Pydantic Schemas for Conversation API Endpoints

Request and response models for human-in-the-loop test planning
conversations between users and the AI planner agent.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Message schemas
# ---------------------------------------------------------------------------

class ConversationMessageCreate(BaseModel):
    """Schema for creating a conversation message."""
    content: str = Field(..., min_length=1, description="Message content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")


class ConversationMessageResponse(BaseModel):
    """Schema for a conversation message in API responses."""
    id: int
    thread_id: int
    role: str = Field(..., description="Message role: user | assistant | system")
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Conversation thread schemas
# ---------------------------------------------------------------------------

class ConversationCreate(BaseModel):
    """Schema for creating a new conversation thread."""
    test_definition_id: int = Field(..., description="Associated test definition ID")
    thread_type: str = Field(
        default="planning",
        description="Thread type: planning | failure_recovery",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Thread-level metadata (e.g. run_id for failure recovery)",
    )


class ConversationResponse(BaseModel):
    """Schema for a conversation thread in API responses, including messages."""
    id: int
    test_definition_id: Optional[int] = None
    thread_type: str
    status: str = Field(..., description="Thread status: active | approved | closed")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    messages: List[ConversationMessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Send message (user feedback) schemas
# ---------------------------------------------------------------------------

class SendMessageRequest(BaseModel):
    """Schema for sending user feedback into an active conversation."""
    content: str = Field(..., min_length=1, description="User feedback text")


class SendMessageResponse(BaseModel):
    """Schema returned after sending user feedback, with AI reply."""
    assistant_message: ConversationMessageResponse
    updated_plan: Optional[Dict[str, Any]] = Field(
        None, description="Refined plan (null if unchanged)"
    )


# ---------------------------------------------------------------------------
# Plan approval schemas
# ---------------------------------------------------------------------------

class PlanModification(BaseModel):
    """Schema for a single step modification during approval."""
    step_number: int = Field(..., ge=1, description="Step number to modify")
    description: Optional[str] = Field(None, description="Updated step description")
    type: Optional[str] = Field(None, description="Updated step type")
    verification: Optional[str] = Field(None, description="Updated verification criteria")


class ApproveRequest(BaseModel):
    """Schema for approving a plan, with optional step modifications."""
    modifications: List[PlanModification] = Field(
        default_factory=list,
        description="Optional step modifications to apply before approval",
    )


# ---------------------------------------------------------------------------
# Failure recovery schemas
# ---------------------------------------------------------------------------

class FailureConversationResponse(BaseModel):
    """Schema for a failure-recovery conversation, including failed step details."""
    thread: ConversationResponse
    failed_steps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Failed test case details from the associated run",
    )


class FailureRecoveryRequest(BaseModel):
    """Schema for a user's recovery action on a failed run."""
    action: str = Field(
        ...,
        description="Recovery action: regenerate_step | edit | retry",
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters",
    )


# ---------------------------------------------------------------------------
# Regression test schemas
# ---------------------------------------------------------------------------

class SaveRegressionRequest(BaseModel):
    """Schema for saving a passed run as a regression test."""
    run_id: str = Field(..., min_length=1, description="Test run ID to save as regression")


class RegressionTestResponse(BaseModel):
    """Schema for a regression test definition response."""
    id: int
    test_id: str
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_regression: bool
    regression_source_run_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

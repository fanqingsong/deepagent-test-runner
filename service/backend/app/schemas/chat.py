"""
Chat Schemas

Request and response models for chat conversations and messages.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict

from pydantic import BaseModel, Field


class ChatMessageResponse(BaseModel):
    """A single message in a chat conversation."""

    id: int
    role: str  # "user" | "assistant" | "tool"
    content: str
    tool_calls: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatConversationResponse(BaseModel):
    """A chat conversation."""

    id: int
    user_id: int
    title: str
    thread_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ChatConversationCreate(BaseModel):
    """Request to create a new conversation."""

    title: Optional[str] = Field(None, max_length=255)


class ChatMessageCreate(BaseModel):
    """Request to send a message."""

    content: str = Field(..., min_length=1, max_length=4096)
    new_conversation: Optional[bool] = Field(
        default=False,
        description="Start a new conversation. If true, a new session ID will be generated."
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID to continue a specific conversation. If not provided, uses user-based session."
    )


class ChatResponse(BaseModel):
    """Response from the chat agent."""

    response: str
    tool_calls: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []

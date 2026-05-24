"""
Pydantic Schemas for Tag Management
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TagResponse(BaseModel):
    """A tag with its usage count."""
    name: str
    count: int


class BulkTagApply(BaseModel):
    """Apply tags to multiple test definitions."""
    test_definition_ids: List[int] = Field(..., min_length=1)
    tags: List[str] = Field(..., min_length=1)
    mode: str = Field(default="add", pattern="^(add|replace|remove)$")

"""
Pydantic Schemas for Run Configuration Templates
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


class RunConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    browser_config: Dict[str, Any] = Field(default_factory=dict)
    timeout_config: Dict[str, Any] = Field(default_factory=dict)
    environment_vars: Dict[str, Any] = Field(default_factory=dict)
    retry_policy: Dict[str, Any] = Field(default_factory=dict)
    execution_config: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class RunConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    browser_config: Optional[Dict[str, Any]] = None
    timeout_config: Optional[Dict[str, Any]] = None
    environment_vars: Optional[Dict[str, Any]] = None
    retry_policy: Optional[Dict[str, Any]] = None
    execution_config: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None


class RunConfigResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    browser_config: Dict[str, Any]
    timeout_config: Dict[str, Any]
    environment_vars: Dict[str, Any]
    retry_policy: Dict[str, Any]
    execution_config: Dict[str, Any]
    is_default: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

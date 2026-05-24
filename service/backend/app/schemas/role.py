"""
Role and Permission Schemas
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    resource: str
    action: str

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_system: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[PermissionResponse] = []

    class Config:
        from_attributes = True


class RoleSummary(BaseModel):
    """Minimal role info for nested responses."""
    id: int
    name: str
    description: Optional[str] = None
    is_system: bool = False

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    permission_ids: List[int] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None


class UserRoleAssign(BaseModel):
    role_ids: List[int]

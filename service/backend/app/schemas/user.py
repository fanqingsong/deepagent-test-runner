"""
User Schemas

Backend user management schemas (NOT authentication).
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    """User creation schema"""
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
    role_ids: List[int] = []


class UserUpdate(BaseModel):
    """User update schema"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    """User self-profile update schema (more restrictive than admin update)"""
    username: Optional[str] = None


class UserResponse(UserBase):
    """User response schema"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserWithRoles(UserResponse):
    """User with roles"""
    roles: List[str] = []


class Session(BaseModel):
    """User session response model"""
    id: int
    session_token: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_active: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class SessionsListResponse(BaseModel):
    """Sessions list response"""
    sessions: List[Session]
    total: int

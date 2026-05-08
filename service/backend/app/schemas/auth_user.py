from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class User(BaseModel):
    """User response model"""
    id: int
    email: str
    is_verified: bool
    mfa_enabled: bool
    status: str  # active, suspended, admin_suspended

    class Config:
        from_attributes = True


class Session(BaseModel):
    """User session response model"""
    id: int
    device: str
    ip_address: str
    last_active: datetime
    is_current: bool

    class Config:
        from_attributes = True


class SessionsListResponse(BaseModel):
    """List of sessions response"""
    sessions: list[Session]

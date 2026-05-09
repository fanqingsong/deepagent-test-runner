from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.schemas.auth_user import User as AuthUser


class RegistrationRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)


class RegistrationResponse(BaseModel):
    """User registration response"""
    message: str
    user_id: int


class EmailVerificationRequest(BaseModel):
    """Email verification request"""
    token: str


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False


class LoginResponse(BaseModel):
    """User login response"""
    access_token: str
    refresh_token: str
    session_token: str
    mfa_required: bool
    user: AuthUser


class LogoutResponse(BaseModel):
    """Logout response"""
    message: str

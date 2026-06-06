from pydantic import BaseModel


class User(BaseModel):
    """User response model"""
    id: int
    email: str
    is_verified: bool
    mfa_enabled: bool
    status: str  # active, suspended, admin_suspended
    is_admin: bool = False
    roles: list[str] = []
    permissions: list[str] = []

    class Config:
        from_attributes = True

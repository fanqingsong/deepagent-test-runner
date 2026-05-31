from pydantic import BaseModel, Field
from typing import Optional, List


class MFAVerificationRequest(BaseModel):
    """MFA code verification request"""
    code: Optional[str] = Field(None, pattern=r'^[0-9]{6}$')
    recovery_code: Optional[str] = Field(None, pattern=r'^[A-Z0-9]{8}$')


class MFASetupResponse(BaseModel):
    """MFA setup initiation response"""
    qr_code_url: str
    secret: str
    backup_codes: List[str]


class MFAEnableRequest(BaseModel):
    """MFA enable request"""
    code: str = Field(..., pattern=r'^[0-9]{6}$')


class MFAEnabledResponse(BaseModel):
    """MFA enabled confirmation response"""
    message: str
    backup_codes: List[str]


class MFADisableRequest(BaseModel):
    """MFA disable request (requires password confirmation)"""
    password: str

from pydantic import BaseModel


class Error(BaseModel):
    """Error response model"""
    error: str
    message: str


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str

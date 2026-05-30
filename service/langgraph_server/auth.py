"""
LangGraph Platform Server custom authentication handler.

Verifies JWT Bearer tokens using the same secret and algorithm
as the FastAPI backend (security.py).
"""

import os
import logging

from jose import jwt, JWTError
from langgraph_sdk import Auth

logger = logging.getLogger(__name__)

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4")
ALGORITHM = "HS256"

auth = Auth()


@auth.authenticate
async def authenticate(authorization: str | None) -> tuple[list[str], str]:
    """Verify JWT Bearer token and return user identity."""
    if not authorization:
        raise Auth.exceptions.HTTPException(401, "Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise Auth.exceptions.HTTPException(401, "Invalid authorization scheme")

    token = authorization[7:]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise Auth.exceptions.HTTPException(401, "Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise Auth.exceptions.HTTPException(401, "Invalid token payload")

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise Auth.exceptions.HTTPException(401, "Invalid user ID in token")

    logger.info("Authenticated user_id=%s", user_id)
    return [], str(user_id)

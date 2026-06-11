"""
LangGraph Proxy API Endpoints

Proxies requests to LangGraph Platform Server with authentication.
The frontend can call these endpoints with cookie-based auth,
and the backend will forward requests with proper Bearer token auth.
"""

import os
from typing import Any, Optional
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User

# LangGraph server URL (internal Docker network)
LANGGRAPH_SERVER_URL = os.environ.get(
    "LANGGRAPH_SERVER_URL",
    "http://deepagent-tester-langgraph:2024"
)

router = APIRouter()

# JWT secret key for LangGraph auth (same as LangGraph server uses)
LANGGRAPH_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4")
LANGGRAPH_ALGORITHM = "HS256"


def create_langgraph_token(user_id: int) -> str:
    """
    Create a JWT token for LangGraph Platform Server authentication.

    Args:
        user_id: User ID to encode in the token

    Returns:
        str: JWT token as Bearer token
    """
    from datetime import datetime

    # Create token with the same format LangGraph expects
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, LANGGRAPH_SECRET_KEY, algorithm=LANGGRAPH_ALGORITHM)
    return f"Bearer {token}"


@router.get("/threads")
async def list_threads(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    List LangGraph threads for the current user.

    Proxies to LangGraph Platform Server's /threads endpoint.
    """
    # Create Bearer token for LangGraph
    auth_header = create_langgraph_token(current_user.id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{LANGGRAPH_SERVER_URL}/threads",
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
                params={"limit": limit, "offset": offset},
                timeout=30.0,
            )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="LangGraph authentication failed"
                )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"LangGraph error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LangGraph server unavailable: {str(e)}"
            )


@router.post("/threads/search")
async def search_threads(
    payload: dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """
    Search LangGraph threads.

    Proxies to LangGraph Platform Server's /threads/search endpoint.
    Returns threads list directly (not wrapped in dict).
    """
    # Create Bearer token for LangGraph
    auth_header = create_langgraph_token(current_user.id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{LANGGRAPH_SERVER_URL}/threads/search",
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="LangGraph authentication failed"
                )

            response.raise_for_status()
            # Return JSON response directly - LangGraph returns a list
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"LangGraph error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LangGraph server unavailable: {str(e)}"
            )


@router.post("/threads")
async def create_thread(
    payload: dict[str, Any],
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Create a new LangGraph thread.

    Proxies to LangGraph Platform Server's /threads endpoint.
    """
    # Create Bearer token for LangGraph
    auth_header = create_langgraph_token(current_user.id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{LANGGRAPH_SERVER_URL}/threads",
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30.0,
            )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="LangGraph authentication failed"
                )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"LangGraph error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LangGraph server unavailable: {str(e)}"
            )


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get a specific LangGraph thread.

    Proxies to LangGraph Platform Server's /threads/{thread_id} endpoint.
    """
    # Create Bearer token for LangGraph
    auth_header = create_langgraph_token(current_user.id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{LANGGRAPH_SERVER_URL}/threads/{thread_id}",
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="LangGraph authentication failed"
                )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"LangGraph error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LangGraph server unavailable: {str(e)}"
            )


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Delete a LangGraph thread.

    Proxies to LangGraph Platform Server's /threads/{thread_id} endpoint.
    """
    # Create Bearer token for LangGraph
    auth_header = create_langgraph_token(current_user.id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                f"{LANGGRAPH_SERVER_URL}/threads/{thread_id}",
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="LangGraph authentication failed"
                )

            response.raise_for_status()
            return response.json() if response.content else {"deleted": True}

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"LangGraph error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LangGraph server unavailable: {str(e)}"
            )


@router.get("/threads/{thread_id}/history")
async def get_thread_history(
    thread_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get thread history/messages.

    Proxies to LangGraph Platform Server's /threads/{thread_id}/history endpoint.
    """
    # Create Bearer token for LangGraph
    auth_header = create_langgraph_token(current_user.id)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{LANGGRAPH_SERVER_URL}/threads/{thread_id}/history",
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
                params={"limit": limit},
                timeout=30.0,
            )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="LangGraph authentication failed"
                )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"LangGraph error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LangGraph server unavailable: {str(e)}"
            )

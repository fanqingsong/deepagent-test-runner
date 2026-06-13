"""
Admin Chat Monitoring Endpoints

Provides admin access to chat session data, metrics, and conversation history.
All endpoints require admin privileges.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.services.langgraph_reader import langgraph_reader
from app.services.chat_session_service import chat_session_service

router = APIRouter()


@router.get("/active-sessions")
async def list_active_sessions(
    current_user: User = Depends(get_current_admin_user),
):
    """List currently active chat sessions."""
    data = await langgraph_reader.list_threads(limit=200)
    return [item for item in data["items"] if item["status"] == "active"]


@router.get("/sessions")
async def list_sessions(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_admin_user),
):
    """Browse all chat sessions from LangGraph server."""
    return await langgraph_reader.list_threads(user_id=user_id, status=status, offset=offset, limit=limit)


@router.get("/sessions/{thread_id}")
async def get_session_detail(
    thread_id: str,
    current_user: User = Depends(get_current_admin_user),
):
    """Get full detail of a chat session from LangGraph server."""
    try:
        messages = await langgraph_reader.get_thread_messages(thread_id)
        # Get thread info from list_threads
        threads_data = await langgraph_reader.list_threads(limit=200)
        thread_info = None
        for item in threads_data["items"]:
            if item["thread_id"] == thread_id:
                thread_info = item
                break
        if not thread_info:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            **thread_info,
            "messages": messages,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/sessions/{thread_id}/messages")
async def get_session_messages(
    thread_id: str,
    current_user: User = Depends(get_current_admin_user),
):
    """Get full message history for a conversation."""
    messages = await langgraph_reader.get_thread_messages(thread_id)
    return {"thread_id": thread_id, "messages": messages}


@router.get("/metrics")
async def get_conversation_metrics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_admin_user),
):
    """Aggregated conversation metrics from LangGraph server."""
    return await langgraph_reader.get_session_metrics(days=days)


@router.get("/subagent-usage")
async def get_subagent_usage(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Subagent usage breakdown from llm_usage table."""
    return await chat_session_service.get_subagent_usage(db, days)


@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_admin_user),
):
    """Get all chat sessions for a specific user."""
    return await langgraph_reader.list_threads(user_id=user_id, limit=limit)

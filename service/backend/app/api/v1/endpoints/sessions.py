from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.services.auth.session_service import SessionService
from app.schemas.user import Session as SessionSchema

router = APIRouter()


@router.get("", response_model=List[SessionSchema])
async def list_sessions(
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """List all active sessions for the current user"""
    # Get session token from header
    session_token = http_request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )

    # Validate session and get user_id
    session = await SessionService.validate_session_token(db, session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    # Get all sessions for user
    sessions = await SessionService.get_user_sessions(db, session.user_id)

    return [
        SessionSchema(
            id=s.id,
            session_token=s.session_token,
            user_agent=s.user_agent,
            ip_address=s.ip_address,
            last_active=s.last_active,
            expires_at=s.expires_at,
            created_at=s.created_at
        )
        for s in sessions
    ]


@router.delete("/{session_id}")
async def terminate_session(
    session_id: int,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Terminate a specific session"""
    # Get session token from header
    session_token = http_request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )

    # Validate session and get user_id
    session = await SessionService.validate_session_token(db, session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    # Terminate the specified session
    success = await SessionService.terminate_session(
        db=db,
        session_id=session_id,
        user_id=session.user_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return {"message": "Session terminated successfully"}


@router.delete("")
async def terminate_all_sessions(
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Terminate all sessions except the current one"""
    # Get session token from header
    session_token = http_request.headers.get("X-Session-Token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token required"
        )

    # Validate session and get user_id
    session = await SessionService.validate_session_token(db, session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session"
        )

    # Terminate all sessions except current
    await SessionService.terminate_all_user_sessions(
        db=db,
        user_id=session.user_id,
        exclude_session_id=session.id
    )

    return {"message": "All other sessions terminated successfully"}

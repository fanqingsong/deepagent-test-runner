"""
Chat WebSocket Endpoint

Real-time streaming chat interface for the AI assistant.
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_ws
from app.models.chat import ChatConversation
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: str,
    token: str,
):
    """WebSocket endpoint for real-time chat.

    Args:
        websocket: WebSocket connection
        conversation_id: Thread ID for the conversation
        token: JWT authentication token
    """
    await websocket.accept()

    try:
        # For now, just send a connected message
        # The actual chat functionality will use REST API
        await websocket.send_json({
            "type": "connected",
            "conversation_id": conversation_id,
            "message": "WebSocket connected. Use REST API for chat functionality."
        })

        # Keep connection alive
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_json()

                # Echo back or process messages
                await websocket.send_json({
                    "type": "echo",
                    "data": data
                })

            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

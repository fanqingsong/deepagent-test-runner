"""
Chat WebSocket Endpoint

Real-time streaming chat interface for the AI assistant.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_current_user_ws
from app.models.chat import ChatConversation, ChatMessage
from app.agents.chat_agent import get_chat_agent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/chat/{conversation_id}")
async def chat_websocket(
    websocket: WebSocket,
    conversation_id: int,
    token: str,
):
    """WebSocket endpoint for real-time chat.

    Authenticates via JWT token, loads the conversation, and
    forwards messages to the ChatAgent.
    """
    await websocket.accept()

    # Authenticate via JWT token
    async with async_session_maker() as db:
        try:
            user = await get_current_user_ws(token, db)
            logger.info("WS auth success: user_id=%s", user.id)
        except Exception as e:
            logger.warning("WS auth failed: %s", e)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    try:
        await websocket.send_json({
            "type": "connected",
            "conversation_id": conversation_id,
        })

        chat_agent = get_chat_agent()

        while True:
            data = await websocket.receive_json()
            content = data.get("content", "").strip()
            if not content:
                continue

            # Look up the conversation to get its thread_id
            async with async_session_maker() as db:
                result = await db.execute(
                    select(ChatConversation).where(
                        ChatConversation.id == conversation_id,
                        ChatConversation.user_id == user.id,
                    )
                )
                conversation = result.scalar_one_or_none()

            if not conversation:
                await websocket.send_json({
                    "type": "error",
                    "content": "Conversation not found",
                })
                continue

            # Call the chat agent
            try:
                agent_result = await chat_agent.chat(
                    message=content,
                    thread_id=conversation.thread_id,
                    user_id=user.id,
                    current_user=user,
                )

                response_content = agent_result.get("response", "")

                # Save messages to DB
                async with async_session_maker() as db:
                    db.add(ChatMessage(
                        conversation_id=conversation_id,
                        role="user",
                        content=content,
                    ))
                    db.add(ChatMessage(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=response_content,
                        tool_calls=agent_result.get("tool_calls"),
                    ))
                    conversation.updated_at = datetime.utcnow()
                    await db.commit()

                await websocket.send_json({
                    "type": "assistant_message",
                    "content": response_content,
                    "tool_calls": [
                        {"name": tc.get("name"), "args": tc.get("args")}
                        for tc in (agent_result.get("tool_calls") or [])
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                })

            except Exception as e:
                logger.exception("Error processing chat message")
                await websocket.send_json({
                    "type": "error",
                    "content": str(e),
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: conversation_id=%s", conversation_id)
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass

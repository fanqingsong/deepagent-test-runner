"""
Chat API Endpoints

Conversational AI assistant for querying system data and executing actions.
"""

import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.chat_agent import get_chat_agent
from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage
from app.schemas.chat import (
    ChatConversationResponse,
    ChatConversationCreate,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def convert_messages_to_dicts(messages: List) -> List[dict]:
    """Convert LangChain message objects to dictionaries for JSON serialization."""
    return [msg.model_dump() if hasattr(msg, 'model_dump') else dict(msg) for msg in messages]


@router.post("/conversations", response_model=ChatConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ChatConversationCreate,
    current_user: User = Depends(RequirePermission("create:conversation")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat conversation."""
    thread_id = str(uuid.uuid4())

    conversation = ChatConversation(
        user_id=current_user.id,
        title=data.title or "New Conversation",
        thread_id=thread_id,
    )

    db.add(conversation)
    await db.commit()

    # Get message count
    count_stmt = select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == conversation.id)
    count_result = await db.execute(count_stmt)
    message_count = count_result.scalar() or 0

    response = ChatConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        thread_id=conversation.thread_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
    )

    return response


@router.get("/conversations", response_model=List[ChatConversationResponse])
async def list_conversations(
    current_user: User = Depends(RequirePermission("read:conversation")),
    db: AsyncSession = Depends(get_db),
):
    """List all conversations for the current user."""
    stmt = select(ChatConversation).where(ChatConversation.user_id == current_user.id).order_by(ChatConversation.updated_at.desc())

    result = await db.execute(stmt)
    conversations = result.scalars().all()

    response_list = []
    for conv in conversations:
        # Get message count
        count_stmt = select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == conv.id)
        count_result = await db.execute(count_stmt)
        message_count = count_result.scalar() or 0

        response_list.append(
            ChatConversationResponse(
                id=conv.id,
                user_id=conv.user_id,
                title=conv.title,
                thread_id=conv.thread_id,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=message_count,
            )
        )

    return response_list


@router.get("/conversations/{conversation_id}", response_model=ChatConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(RequirePermission("read:conversation")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single conversation by ID."""
    stmt = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id,
    )

    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get message count
    count_stmt = select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == conversation.id)
    count_result = await db.execute(count_stmt)
    message_count = count_result.scalar() or 0

    return ChatConversationResponse(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        thread_id=conversation.thread_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(RequirePermission("delete:conversation")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    stmt = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id,
    )

    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()


@router.get("/conversations/{conversation_id}/messages", response_model=List[ChatMessageResponse])
async def get_messages(
    conversation_id: int,
    current_user: User = Depends(RequirePermission("read:conversation")),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation."""
    # Verify ownership
    conv_stmt = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id,
    )
    conv_result = await db.execute(conv_stmt)
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
    )

    result = await db.execute(stmt)
    messages = result.scalars().all()

    return [ChatMessageResponse.model_validate(msg) for msg in messages]


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: int,
    data: ChatMessageCreate,
    current_user: User = Depends(RequirePermission("create:conversation")),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get AI response."""
    from app.agent_tools.tool_context import set_current_user_id, clear_current_user_id

    # Verify ownership
    conv_stmt = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id,
    )
    conv_result = await db.execute(conv_stmt)
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user message
    user_message = ChatMessage(
        conversation_id=conversation_id,
        role="user",
        content=data.content,
    )
    db.add(user_message)
    await db.flush()

    # Get chat agent and process
    chat_agent = get_chat_agent()

    try:
        # Set user context for tools to access
        set_current_user_id(current_user.id)

        result = await chat_agent.chat(
            message=data.content,
            thread_id=conversation.thread_id,
            user_id=current_user.id,
            current_user=current_user,
            db=db,
            enable_search=data.enable_search or False,
            enable_deep_thinking=data.enable_deep_thinking or False,
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")
    finally:
        # Clear user context
        clear_current_user_id()

    # Save assistant message
    assistant_message = ChatMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=result["response"],
        tool_calls=result.get("tool_calls") or {},
    )
    db.add(assistant_message)

    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()

    # Auto-rename conversation on first message
    new_title = None
    if conversation.title in ("New Chat", "New Conversation"):
        try:
            new_title = await chat_agent.generate_title(data.content)
            conversation.title = new_title
        except Exception:
            logger.debug("Title generation failed, keeping default")

    await db.commit()

    return ChatResponse(
        response=result["response"],
        tool_calls=result.get("tool_calls", []),
        messages=convert_messages_to_dicts(result.get("messages", [])),
        conversation_title=new_title,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_simple(
    data: ChatMessageCreate,
    current_user: User = Depends(RequirePermission("create:conversation")),
    db: AsyncSession = Depends(get_db),
):
    """Simple chat endpoint with persistent conversation memory.

    - By default, maintains conversation history per user using user-based thread_id
    - Set new_conversation=true to start a fresh conversation
    - Provide session_id to continue a specific conversation
    """
    from app.core.database import async_session_maker
    from app.agent_tools.tool_context import set_current_user_id

    chat_agent = get_chat_agent()

    try:
        # Set user context for tools to access
        set_current_user_id(current_user.id)

        # Use timeout to prevent hanging
        import asyncio
        import uuid

        # Determine thread_id based on request parameters
        if data.new_conversation:
            # Start a completely new conversation
            thread_id = f"session_{uuid.uuid4().hex}"
            logger.info(f"Starting new conversation: thread_id={thread_id}, user_id={current_user.id}")
        elif data.session_id:
            # Continue a specific conversation
            thread_id = f"session_{data.session_id}"
            logger.info(f"Continuing conversation: thread_id={thread_id}, user_id={current_user.id}")
        else:
            # Use user-based thread_id for persistent conversation history
            thread_id = f"user_{current_user.id}"
            logger.info(f"Using user thread_id: thread_id={thread_id}, user_id={current_user.id}")

        # Deep thinking mode needs longer timeout due to multi-step planning/subagent calls
        chat_timeout = 600.0 if data.enable_deep_thinking else 300.0
        result = await asyncio.wait_for(
            chat_agent.chat(
                message=data.content,
                thread_id=thread_id,
                user_id=current_user.id,
                current_user=current_user,
                db=db,
                enable_search=data.enable_search or False,
                enable_deep_thinking=data.enable_deep_thinking or False,
            ),
            timeout=chat_timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Chat request timed out after {chat_timeout:.0f} seconds")
        raise HTTPException(
            status_code=504,
            detail="Chat request timed out. Please try again or use a simpler query."
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")
    finally:
        # Clear user context
        from app.agent_tools.tool_context import clear_current_user_id
        clear_current_user_id()

    return ChatResponse(
        response=result["response"],
        tool_calls=result.get("tool_calls", []),
        messages=convert_messages_to_dicts(result.get("messages", [])),
    )


@router.post("/conversations/{conversation_id}/compress", response_model=ChatResponse)
async def compress_conversation(
    conversation_id: int,
    current_user: User = Depends(RequirePermission("update:conversation")),
    db: AsyncSession = Depends(get_db),
):
    """Compress a conversation by summarizing old messages."""
    from app.agent_tools.tool_context import set_current_user_id, clear_current_user_id

    # Verify ownership
    conv_stmt = select(ChatConversation).where(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id,
    )
    conv_result = await db.execute(conv_stmt)
    conversation = conv_result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get all messages
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
    )

    result = await db.execute(stmt)
    messages = result.scalars().all()

    if len(messages) < 4:
        raise HTTPException(status_code=400, detail="Conversation must have at least 4 messages to compress")

    # Keep the last 2 messages, compress the rest
    messages_to_compress = messages[:-2]
    messages_to_keep = messages[-2:]

    # Build a summary from messages to compress
    summary_parts = []
    for msg in messages_to_compress:
        role = msg.role.upper()
        summary_parts.append(f"{role}: {msg.content}")

    conversation_text = "\n\n".join(summary_parts)

    # Create a summary message
    summary_message = ChatMessage(
        conversation_id=conversation_id,
        role="system",
        content=f"[Previous conversation summary]\n\n{conversation_text}",
    )
    db.add(summary_message)

    # Delete old messages
    for msg in messages_to_compress:
        await db.delete(msg)

    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()

    await db.commit()

    return ChatResponse(
        response=f"Compressed {len(messages_to_compress)} messages into a summary. {len(messages_to_keep)} recent messages preserved.",
        tool_calls=[],
        messages=[],
    )

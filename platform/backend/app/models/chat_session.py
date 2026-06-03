"""
Chat Session ORM Model

Bridges LangGraph's thread_id with the platform user system for admin monitoring.
LangGraph manages its own tables (checkpoints, threads) — this model provides
the admin-facing metadata layer without touching LangGraph internals.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_user_id", "user_id"),
        Index("ix_chat_sessions_status", "status"),
        Index("ix_chat_sessions_langgraph_thread_id", "langgraph_thread_id"),
        Index("ix_chat_sessions_last_message_at", "last_message_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    langgraph_thread_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )

    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    subagents_used: Mapped[Optional[dict]] = mapped_column(
        "subagents_used", JSONB, nullable=True, server_default="[]"
    )

    total_tokens: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )
    total_duration_ms: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        server_default=func.now(),
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, thread='{self.langgraph_thread_id}', user={self.user_id}, status='{self.status}')>"

"""
Conversation Models for Human-in-the-Loop Test Planning

Stores multi-turn conversations between users and AI for test plan
generation, refinement, and failure recovery.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.test_definition import TestDefinition


class ConversationThread(Base):
    """A conversation thread between user and AI for test planning or failure recovery."""

    __tablename__ = "conversation_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_definition_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("test_definitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    thread_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "planning" | "failure_recovery"
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # "active" | "approved" | "closed"
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default={}, nullable=False
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow,
    )

    # Relationships
    messages: Mapped[List["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )
    test_definition: Mapped[Optional["TestDefinition"]] = relationship(
        "TestDefinition", foreign_keys=[test_definition_id]
    )

    def __repr__(self) -> str:
        return f"<ConversationThread(id={self.id}, type='{self.thread_type}', status='{self.status}')>"


class ConversationMessage(Base):
    """A single message within a conversation thread."""

    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        ForeignKey("conversation_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default={}, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # Relationships
    thread: Mapped["ConversationThread"] = relationship(
        "ConversationThread", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, role='{self.role}', thread_id={self.thread_id})>"

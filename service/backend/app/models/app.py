"""
App Model — LLM-APP-style test workspace.

Each App represents a single test case that the user iteratively creates
through a conversational interface: goal → plan → execute → refine/publish.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.conversation import ConversationThread
    from app.models.test_definition import TestDefinition
    from app.models.user import User


class App(Base):
    __tablename__ = "apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
        comment="draft|generating|testing|passed|pending_review|published|archived",
    )

    test_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_context: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    current_plan: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)

    conversation_thread_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("conversation_threads.id", ondelete="SET NULL"), nullable=True,
    )
    test_definition_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("test_definitions.id", ondelete="SET NULL"), nullable=True,
    )

    latest_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latest_result: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    iteration_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    icon: Mapped[str] = mapped_column(String(50), default="test-tube", nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#0f62fe", nullable=False)

    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now(),
        onupdate=datetime.utcnow,
    )

    conversation_thread: Mapped[Optional["ConversationThread"]] = relationship(
        "ConversationThread", foreign_keys=[conversation_thread_id],
    )
    test_definition: Mapped[Optional["TestDefinition"]] = relationship(
        "TestDefinition", foreign_keys=[test_definition_id],
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by],
    )

    def __repr__(self) -> str:
        return f"<App(id={self.id}, name='{self.name}', status='{self.status}')>"

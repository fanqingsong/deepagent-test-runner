"""
LLM Usage ORM Model

Tracks per-call token usage for all LLM-powered agents.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LlmUsage(Base):
    __tablename__ = "llm_usage"
    __table_args__ = (
        Index("ix_llm_usage_created_at", "created_at"),
        Index("ix_llm_usage_agent_type_created_at", "agent_type", "created_at"),
        Index("ix_llm_usage_user_id_created_at", "user_id", "created_at"),
        Index("ix_llm_usage_test_run_id", "test_run_id"),
        Index("ix_llm_usage_thread_id", "thread_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    prompt_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    test_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    thread_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<LlmUsage(id={self.id}, agent_type='{self.agent_type}', total_tokens={self.total_tokens})>"

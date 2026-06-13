"""
LLM Usage ORM Model

Tracks per-call token usage for all LLM-powered agents.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.token_budget import TokenBudget
    from app.models.token_quota import TokenQuota


class LlmUsage(Base):
    __tablename__ = "llm_usage"
    __table_args__ = (
        Index("ix_llm_usage_created_at", "created_at"),
        Index("ix_llm_usage_agent_type_created_at", "agent_type", "created_at"),
        Index("ix_llm_usage_user_id_created_at", "user_id", "created_at"),
        Index("ix_llm_usage_test_run_id", "test_run_id"),
        Index("ix_llm_usage_thread_id", "thread_id"),
        Index("ix_llm_usage_budget_id", "budget_id"),
        Index("ix_llm_usage_quota_id", "quota_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    prompt_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Token budget/quota tracking
    budget_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("token_budgets.id"),
        nullable=True,
        comment="Associated budget for this usage"
    )
    quota_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("token_quotas.id"),
        nullable=True,
        comment="Associated quota for this usage"
    )

    # Cost tracking (RMB)
    cost_rmb: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Cost in RMB for this usage"
    )

    # Priority and enforcement
    priority: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Priority level (1-10) if applicable"
    )
    enforcement_action: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Enforcement action: allowed, blocked, warning"
    )
    enforcement_details: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Details about enforcement decision"
    )

    # Original fields
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    test_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    thread_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    # Relationships
    budget: Mapped[Optional["TokenBudget"]] = relationship(
        "TokenBudget",
        back_populates="llm_usage_records",
        foreign_keys=[budget_id]
    )
    quota: Mapped[Optional["TokenQuota"]] = relationship(
        "TokenQuota",
        back_populates="llm_usage_records",
        foreign_keys=[quota_id]
    )

    def __repr__(self) -> str:
        return f"<LlmUsage(id={self.id}, agent_type='{self.agent_type}', total_tokens={self.total_tokens}, cost_rmb={self.cost_rmb})>"

    @property
    def was_blocked(self) -> bool:
        """Check if this usage was blocked by enforcement."""
        return self.enforcement_action == "blocked"

    @property
    def had_warning(self) -> bool:
        """Check if this usage triggered a warning."""
        return self.enforcement_action == "warning"

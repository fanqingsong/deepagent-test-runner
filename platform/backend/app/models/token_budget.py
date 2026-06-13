"""
Token Budget ORM Model

Hierarchical budget structure for token usage control at different levels:
organization → suite → test → user
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.test_definition import TestDefinition
    from app.models.test_suite import TestSuite
    from app.models.llm_usage import LlmUsage
    from app.models.token_alert import TokenAlert


class TokenBudget(Base):
    """
    Token Budget Model

    Hierarchical budget structure for controlling token usage across different scopes.
    Supports parent-child relationships and inheritance patterns.

    Scope types:
    - organization: Company-wide budget
    - suite: Test suite budget
    - test: Individual test budget
    - user: User-specific budget

    Budget status:
    - active: Currently enforcing limits
    - inactive: Not enforcing (paused)
    - exhausted: Limit reached, no more usage allowed
    """

    __tablename__ = "token_budgets"
    __table_args__ = (
        Index("ix_token_budgets_scope_type_scope_id", "scope_type", "scope_id"),
        Index("ix_token_budgets_parent_id", "parent_budget_id"),
        Index("ix_token_budgets_status", "status"),
        Index("ix_token_budgets_period_start_end", "period_start", "period_end"),
        Index("ix_token_budgets_priority_status", "priority", "status"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Budget identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Scope definition
    scope_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="organization, suite, test, user"
    )
    scope_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="ID of the scoped entity (user_id, test_definition_id, etc.)"
    )

    # Hierarchical structure
    parent_budget_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("token_budgets.id"),
        nullable=True,
        comment="Parent budget for inheritance"
    )

    # Period definition
    period_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="monthly",
        comment="hourly, daily, weekly, monthly, custom"
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Start of current period"
    )
    period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="End of current period"
    )

    # Token limits
    total_tokens: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Total token budget for the period"
    )
    used_tokens: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Tokens used in current period"
    )
    remaining_tokens: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Calculated: total_tokens - used_tokens"
    )

    # Priority and enforcement
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        comment="1-10, higher = more important"
    )
    enforcement_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="soft",
        comment="soft (warn), hard (block), monitoring (track only)"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="active, inactive, exhausted"
    )

    # Inheritance settings
    inherit_from_parent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Inherit limits from parent budget"
    )
    inherit_strategy: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="inherit_percentage, inherit_absolute, cascade"
    )

    # Alert thresholds
    alert_thresholds: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {
            "warning": 80,  # Alert at 80% usage
            "critical": 90,  # Alert at 90% usage
            "emergency": 95  # Alert at 95% usage
        },
        comment="Alert threshold percentages"
    )

    # Additional configuration
    config_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Additional budget configuration"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow
    )
    last_reset_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Last time period was reset"
    )

    # Relationships
    parent_budget: Mapped[Optional["TokenBudget"]] = relationship(
        "TokenBudget",
        remote_side=[id],
        backref="child_budgets"
    )
    llm_usage_records: Mapped[list["LlmUsage"]] = relationship(
        "LlmUsage",
        back_populates="budget",
        cascade="all, delete-orphan"
    )
    alerts: Mapped[list["TokenAlert"]] = relationship(
        "TokenAlert",
        back_populates="budget",
        cascade="all, delete-orphan",
        order_by="TokenAlert.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<TokenBudget(id={self.id}, name='{self.name}', scope_type='{self.scope_type}', status='{self.status}')>"

    @property
    def usage_percentage(self) -> float:
        """Calculate usage as percentage of total budget."""
        if self.total_tokens == 0:
            return 0.0
        return (self.used_tokens / self.total_tokens) * 100

    @property
    def is_exhausted(self) -> bool:
        """Check if budget is exhausted."""
        return self.used_tokens >= self.total_tokens

    @property
    def is_near_limit(self, threshold: float = 80.0) -> bool:
        """Check if usage is near the limit."""
        return self.usage_percentage >= threshold

    def update_usage(self, tokens_used: int) -> None:
        """Update used tokens and recalculate remaining."""
        self.used_tokens += tokens_used
        self.remaining_tokens = max(0, self.total_tokens - self.used_tokens)

        # Update status if exhausted
        if self.is_exhausted and self.status == "active":
            self.status = "exhausted"

    def reset_period(self, new_period_start: datetime, new_period_end: Optional[datetime] = None) -> None:
        """Reset the budget period and token usage."""
        self.period_start = new_period_start
        self.period_end = new_period_end
        self.used_tokens = 0
        self.remaining_tokens = self.total_tokens
        self.last_reset_at = datetime.utcnow()
        self.status = "active"

    def check_threshold_alerts(self) -> list[str]:
        """Check which alert thresholds have been triggered."""
        triggered_alerts = []
        usage_pct = self.usage_percentage

        if "emergency" in self.alert_thresholds and usage_pct >= self.alert_thresholds["emergency"]:
            triggered_alerts.append("emergency")
        elif "critical" in self.alert_thresholds and usage_pct >= self.alert_thresholds["critical"]:
            triggered_alerts.append("critical")
        elif "warning" in self.alert_thresholds and usage_pct >= self.alert_thresholds["warning"]:
            triggered_alerts.append("warning")

        return triggered_alerts

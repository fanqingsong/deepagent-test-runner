"""
Token Alert ORM Model

Alerts for budget/quota usage thresholds and enforcement actions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func, Index, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.token_budget import TokenBudget
    from app.models.token_quota import TokenQuota
    from app.models.user import User


class TokenAlert(Base):
    """
    Token Alert Model

    Tracks alerts triggered by budget/quota usage thresholds and enforcement actions.
    Provides audit trail and notification status tracking.

    Alert types:
    - budget_warning: Budget usage exceeded warning threshold
    - budget_exceeded: Budget limit exceeded
    - quota_warning: Quota usage exceeded warning threshold
    - quota_exceeded: Quota limit exceeded
    - enforcement_action: Enforcement action was triggered

    Severity levels:
    - info: Informational
    - warning: Warning level
    - critical: Critical level
    - emergency: Emergency level
    """

    __tablename__ = "token_alerts"
    __table_args__ = (
        Index("ix_token_alerts_budget_id", "budget_id"),
        Index("ix_token_alerts_quota_id", "quota_id"),
        Index("ix_token_alerts_user_id", "user_id"),
        Index("ix_token_alerts_severity", "severity"),
        Index("ix_token_alerts_alert_type_created_at", "alert_type", "created_at"),
        Index("ix_token_alerts_acknowledged", "is_acknowledged"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Alert classification
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="budget_warning, budget_exceeded, quota_warning, quota_exceeded, enforcement_action"
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="warning",
        comment="info, warning, critical, emergency"
    )

    # Scope tracking
    budget_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("token_budgets.id"),
        nullable=True,
        comment="Budget that triggered this alert"
    )
    quota_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("token_quotas.id"),
        nullable=True,
        comment="Quota that triggered this alert"
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="User associated with this alert"
    )

    # Threshold information
    threshold_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="percentage",
        comment="percentage, absolute"
    )
    threshold_value: Mapped[float] = mapped_column(
        nullable=False,
        default=0.0,
        comment="Threshold that was triggered"
    )
    current_value: Mapped[float] = mapped_column(
        nullable=False,
        default=0.0,
        comment="Current value when alert triggered"
    )

    # Metrics snapshot
    metrics_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Snapshot of metrics at alert time"
    )

    # Message and details
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable alert message"
    )
    details: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Additional alert details"
    )

    # Enforcement action
    enforcement_action: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Action taken: blocked, warning_logged, monitoring_only"
    )
    enforcement_result: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Result of enforcement action"
    )

    # Acknowledgment tracking
    is_acknowledged: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether alert has been acknowledged"
    )
    acknowledged_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="User who acknowledged the alert"
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When alert was acknowledged"
    )

    # Notification status
    notifications_sent: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Track notification delivery: {email: true, webhook: true}"
    )
    notification_errors: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        comment="Track notification failures: {email: error_message}"
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="When alert was resolved"
    )

    # Relationships
    budget: Mapped[Optional["TokenBudget"]] = relationship(
        "TokenBudget",
        back_populates="alerts"
    )
    quota: Mapped[Optional["TokenQuota"]] = relationship(
        "TokenQuota",
        back_populates="alerts"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[user_id],
        backref="token_alerts"
    )
    acknowledger: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[acknowledged_by]
    )

    def __repr__(self) -> str:
        return f"<TokenAlert(id={self.id}, alert_type='{self.alert_type}', severity='{self.severity}')>"

    def acknowledge(self, user_id: int) -> None:
        """Mark alert as acknowledged."""
        self.is_acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.utcnow()

    def resolve(self) -> None:
        """Mark alert as resolved."""
        self.resolved_at = datetime.utcnow()

    def mark_notification_sent(self, channel: str, success: bool = True, error: Optional[str] = None) -> None:
        """Mark notification status for a channel."""
        if success:
            if "notifications_sent" not in self.__dict__ or self.notifications_sent is None:
                self.notifications_sent = {}
            self.notifications_sent[channel] = True
        else:
            if "notification_errors" not in self.__dict__ or self.notification_errors is None:
                self.notification_errors = {}
            self.notification_errors[channel] = error

    @property
    def is_resolved(self) -> bool:
        """Check if alert is resolved."""
        return self.resolved_at is not None

    @property
    def is_critical(self) -> bool:
        """Check if alert is critical or emergency."""
        return self.severity in ["critical", "emergency"]

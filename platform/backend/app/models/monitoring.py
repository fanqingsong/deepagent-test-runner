"""
Monitoring ORM Models

Stores system health monitoring data, alerts, and alert configurations.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentMonitoring(Base):
    """Stores periodic health check snapshots from the Monitoring Agent."""

    __tablename__ = "agent_monitoring"
    __table_args__ = (
        Index("ix_agent_monitoring_check_time", "check_time"),
        Index("ix_agent_monitoring_status", "status"),
        Index("ix_agent_monitoring_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    check_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="normal",  # normal, warning, critical
    )

    metrics: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default={},  # {test_runs, agent_health, resources}
    )

    alerts_generated: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,  # Array of alert objects
    )

    report_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<AgentMonitoring(id={self.id}, status='{self.status}', check_time={self.check_time})>"


class AgentAlert(Base):
    """Stores alert history for monitoring events."""

    __tablename__ = "agent_alerts"
    __table_args__ = (
        Index("ix_agent_alerts_alert_type", "alert_type"),
        Index("ix_agent_alerts_severity", "severity"),
        Index("ix_agent_alerts_acknowledged", "acknowledged"),
        Index("ix_agent_alerts_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # high_failure_rate, agent_slow_response, token_budget_alert, etc
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # warning, critical
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    metrics_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,  # Relevant metrics at alert time
    )

    acknowledged: Mapped[bool] = mapped_column(
        Integer,
        nullable=False,
        default=False,  # Using Boolean as Integer for compatibility
    )

    acknowledged_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,  # Foreign key to users.id
    )

    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<AgentAlert(id={self.id}, type='{self.alert_type}', severity='{self.severity}')>"


class AlertConfiguration(Base):
    """Stores user-defined alert rules."""

    __tablename__ = "alert_configurations"
    __table_args__ = (
        Index("ix_alert_configurations_alert_type", "alert_type"),
        Index("ix_alert_configurations_enabled", "enabled"),
        Index("ix_alert_configurations_created_by", "created_by"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # test_failure, agent_performance, resource, scheduling
    )

    condition_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,  # {threshold, operator, metric, time_window}
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # warning, critical
    )

    enabled: Mapped[bool] = mapped_column(
        Integer,
        nullable=False,
        default=True,  # Using Boolean as Integer for compatibility
    )

    cooldown_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3600,  # 1 hour default cooldown
    )

    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,  # Foreign key to users.id
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<AlertConfiguration(id={self.id}, name='{self.name}', enabled={self.enabled})>"

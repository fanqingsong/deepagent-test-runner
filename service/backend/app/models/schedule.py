"""
Schedule ORM Model

Represents a test execution schedule with cron-based timing.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Schedule(Base):
    """
    Schedule Model

    Represents a scheduled test execution with timing configuration,
    target selection, and execution constraints.
    """

    __tablename__ = "schedules"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Basic fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Target configuration (mutually exclusive based on schedule_type)
    test_definition_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    test_definition_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    test_suite_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tag_filter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Schedule configuration
    preset_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)

    # Environment and execution configuration
    environment_overrides: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_concurrent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    run_config_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    next_run_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_run_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
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
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True  # Allow NULL for system-created schedules
    )

    # Relationships
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        backref="schedules"
    )

    def __repr__(self) -> str:
        return f"<Schedule(id={self.id}, name='{self.name}', type='{self.schedule_type}', active={self.is_active})>"

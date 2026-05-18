"""
Test Run ORM Model

Records the execution history of scheduled tests.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TestRun(Base):
    """
    Test Run Model

    Records the execution details and results of a scheduled test run.
    """

    __tablename__ = "test_runs"
    __table_args__ = (
        Index("ix_test_runs_created_at", "created_at"),
        Index("ix_test_runs_status_created_at", "status", "created_at"),
    )

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    # NOTE: schedule_id removed - not in current DB schema
    # NOTE: The production DB schema for `test_runs` does not include `user_id` in some
    # deployments. Keep scheduler-service compatible by not mapping this column at all.
    test_definition_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Run identification
    run_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Execution timing - NOTE: start_time/end_time are bigint (milliseconds) in DB, not datetime
    start_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    end_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    # NOTE: Column name is 'total_duration' in DB, not 'total_duration_ms'
    total_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Result statistics
    total_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<TestRun(id={self.id}, run_id='{self.run_id}', status='{self.status}')>"

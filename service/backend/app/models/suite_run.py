"""
SuiteRun and SuiteRunEntry ORM Models

Track test suite execution at the suite level and per-entry level.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SuiteRun(Base):
    """
    Suite Run Model

    Represents a single execution of a test suite, tracking overall
    status, timing, and aggregated results across all entries.
    """

    __tablename__ = "suite_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suite_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("test_suites.id"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    execution_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sequential"
    )
    total_tests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    end_time: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    total_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    environment: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    triggered_by: Mapped[str] = mapped_column(
        String(100), default="manual", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    entries: Mapped[list["SuiteRunEntry"]] = relationship(
        "SuiteRunEntry", backref="suite_run", lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<SuiteRun(id={self.id}, run_id='{self.run_id}', "
            f"status='{self.status}', suite_id={self.suite_id})>"
        )


class SuiteRunEntry(Base):
    """
    Suite Run Entry Model

    Tracks the status of each individual test within a suite run.
    """

    __tablename__ = "suite_run_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suite_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suite_runs.id", ondelete="CASCADE"), nullable=False
    )
    test_definition_id: Mapped[int] = mapped_column(Integer, nullable=False)
    test_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entry_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    condition: Mapped[str] = mapped_column(
        String(20), default="always", nullable=False
    )
    started_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    finished_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SuiteRunEntry(id={self.id}, order={self.entry_order}, "
            f"status='{self.status}', test_def={self.test_definition_id})>"
        )

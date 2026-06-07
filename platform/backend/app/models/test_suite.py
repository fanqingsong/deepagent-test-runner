"""
Test Suite ORM Model

Represents a group of test definitions with execution configuration
that can be scheduled and run together.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, Boolean, DateTime, func, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.test_suite_version import TestSuiteVersion
    from app.models.test_suite_permission import TestSuitePermission


class TestSuite(Base):
    """
    Test Suite Model

    A collection of test definitions with execution config (sequential/parallel,
    fail strategy, retry, environment) that can be run as a unit.
    """

    __tablename__ = "test_suites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Basic fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_definition_ids: Mapped[List[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )

    # Execution configuration
    execution_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sequential"
    )
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    fail_strategy: Mapped[str] = mapped_column(
        String(20), nullable=False, default="continue"
    )
    retry_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    environment_vars: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Ordered entries with per-entry config (canonical source when non-empty)
    suite_entries: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Dynamic suite support (resolved from tags at runtime)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dynamic_tag_rule: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Setup/teardown test definitions
    setup_test_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    teardown_test_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Schedule configuration (auto-synced to Schedule table)
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai", nullable=False)
    schedule_allow_concurrent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    schedule_max_retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    schedule_retry_interval: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    schedule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    next_run_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_run_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Review/approval workflow
    review_status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False,
        comment="draft|pending_review|approved|rejected",
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    tags: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow,
        onupdate=datetime.utcnow, server_default=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)

    # Relationships
    suite_versions: Mapped[List["TestSuiteVersion"]] = relationship(
        "TestSuiteVersion",
        back_populates="test_suite",
        cascade="all, delete-orphan"
    )
    suite_permissions: Mapped[List["TestSuitePermission"]] = relationship(
        "TestSuitePermission",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestSuite(id={self.id}, name='{self.name}', tests={len(self.test_definition_ids)})>"

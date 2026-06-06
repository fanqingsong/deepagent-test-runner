"""
Test Definition ORM Model

Represents a test case definition with metadata, steps, and versions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.test_version import TestVersion
    from app.models.user import User


class TestDefinition(Base):
    """
    Test Definition Model

    Represents a complete test case with metadata, environment configuration,
    and associated test steps.
    """

    __tablename__ = "test_definitions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Basic fields
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # JSON fields
    environment: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=[], nullable=False)

    # Test goal and context
    test_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_context: Mapped[dict] = mapped_column(JSONB, default={}, nullable=False)

    # Metadata
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
        nullable=True  # Allow NULL for existing records and system-created tests
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Regression test fields
    is_regression: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    regression_source_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # App workspace fields
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_app_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apps.id"), nullable=True,
    )

    # Script generation fields
    execution_mode: Mapped[str] = mapped_column(String(20), default="script", nullable=False)
    playwright_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    script_status: Mapped[str] = mapped_column(String(20), default="none", nullable=False)
    script_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Review/approval workflow
    review_status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False,
        comment="draft|pending_review|approved|rejected",
    )
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    test_versions: Mapped[List["TestVersion"]] = relationship(
        "TestVersion",
        back_populates="test_definition",
        cascade="all, delete-orphan",
        order_by="TestVersion.version.desc()"
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        backref="test_definitions"
    )

    def __repr__(self) -> str:
        return f"<TestDefinition(id={self.id}, test_id='{self.test_id}', name='{self.name}')>"

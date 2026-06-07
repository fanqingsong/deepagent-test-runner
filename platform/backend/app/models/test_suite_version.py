"""
Test Suite Version ORM Model

Represents historical snapshots of test suites for versioning.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.test_suite import TestSuite
    from app.models.user import User


class TestSuiteVersion(Base):
    """
    Test Suite Version Model

    Stores snapshots of test suites for version history and rollback.
    The snapshot field contains the complete test suite configuration as JSON.
    Each version can be independently submitted for review.
    """

    __tablename__ = "test_suite_versions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    test_suite_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_suites.id", ondelete="CASCADE"),
        nullable=False
    )

    # Version fields
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    change_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Review workflow
    review_status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False,
        comment="draft|pending_review|approved|rejected|published",
    )
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)

    # Relationships
    test_suite: Mapped["TestSuite"] = relationship(
        "TestSuite",
        back_populates="suite_versions"
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[reviewed_by],
    )

    def __repr__(self) -> str:
        return f"<TestSuiteVersion(id={self.id}, version={self.version}, review_status='{self.review_status}')>"

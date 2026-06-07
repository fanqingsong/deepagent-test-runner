"""
Test Suite Permission ORM Model

Controls access to test suites with fine-grained permissions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.test_suite import TestSuite
    from app.models.user import User


class TestSuitePermission(Base):
    """
    Test Suite Permission Model

    Controls suite-level access with fine-grained permissions.
    Each record grants a specific user a permission level on a test suite.
    """

    __tablename__ = "test_suite_permissions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    test_suite_id: Mapped[int] = mapped_column(
        ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    permission_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="view|edit|execute|admin",
    )
    granted_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now(),
    )

    # Relationships
    test_suite: Mapped["TestSuite"] = relationship(
        "TestSuite", foreign_keys=[test_suite_id], back_populates="suite_permissions",
    )
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id],
    )
    grantor: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[granted_by],
    )

    def __repr__(self) -> str:
        return f"<TestSuitePermission(suite_id={self.test_suite_id}, user_id={self.user_id}, type='{self.permission_type}')>"

"""
Test Step ORM Model

Represents individual steps within a test definition.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.test_definition import TestDefinition


class TestStep(Base):
    """
    Test Step Model

    Represents a single step in a test case, including the action type,
    parameters, and expected result.
    """

    __tablename__ = "test_steps"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    test_definition_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Step fields
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI Planning fields
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    parent_step_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("test_steps.id"), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )

    # Relationships
    test_definition: Mapped["TestDefinition"] = relationship(
        "TestDefinition",
        back_populates="test_steps"
    )

    def __repr__(self) -> str:
        return f"<TestStep(id={self.id}, step_number={self.step_number}, type='{self.type}')>"

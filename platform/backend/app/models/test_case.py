"""
Test Case Model

Represents a test case execution result.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TestCase(Base):
    """
    Test Case model representing execution results.

    Attributes:
        id: Primary key
        run_id: Foreign key to test_runs table
        test_definition_id: Foreign key to test_definitions table
        test_id: Test identifier string
        description: Test case description
        status: Test execution status (passed, failed, skipped, error)
        duration: Execution duration in milliseconds
        start_time: Execution start timestamp (milliseconds)
        end_time: Execution end timestamp (milliseconds)
        error_message: Error message if test failed
        screenshot_path: Path to screenshot if available
        created_at: Record creation timestamp
    """

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    test_definition_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    test_id: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    duration: Mapped[int] = mapped_column(BigInteger, nullable=False)
    start_time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_time: Mapped[int] = mapped_column(BigInteger, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now()
    )

    def __repr__(self):
        return (
            f"<TestCase(id={self.id}, test_id='{self.test_id}', "
            f"status='{self.status}', run_id={self.run_id})>"
        )

"""
Email Sent Log ORM Model

Tracks emails sent via the email agent for history queries.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmailSentLog(Base):
    __tablename__ = "email_sent_log"
    __table_args__ = (
        Index("ix_email_sent_log_sender_id", "sender_id"),
        Index("ix_email_sent_log_sent_at", "sent_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    sender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_preview: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cc: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    sent_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<EmailSentLog(id={self.id}, to='{self.to_email}', subject='{self.subject}')>"

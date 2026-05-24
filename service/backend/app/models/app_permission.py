"""
AppPermission Model — controls access to App workspaces.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.app import App
    from app.models.user import User


class AppPermission(Base):
    __tablename__ = "app_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    app_id: Mapped[int] = mapped_column(
        ForeignKey("apps.id", ondelete="CASCADE"), nullable=False,
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

    app: Mapped["App"] = relationship("App", foreign_keys=[app_id])
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    grantor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[granted_by])

    def __repr__(self) -> str:
        return f"<AppPermission(app_id={self.app_id}, user_id={self.user_id}, type='{self.permission_type}')>"

"""
TestWorkspacePermission Model — controls access to TestWorkspace workspaces.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.test_workspace import TestWorkspace
    from app.models.user import User


class TestWorkspacePermission(Base):
    __tablename__ = "test_workspace_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("test_workspace.id", ondelete="CASCADE"), nullable=False,
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

    workspace: Mapped["TestWorkspace"] = relationship("TestWorkspace", foreign_keys=[workspace_id])
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    grantor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[granted_by])

    def __repr__(self) -> str:
        return f"<TestWorkspacePermission(workspace_id={self.workspace_id}, user_id={self.user_id}, type='{self.permission_type}')>"

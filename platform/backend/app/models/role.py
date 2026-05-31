"""
Role and Permission ORM Models

Implements Role-Based Access Control (RBAC) for user management.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User

# Many-to-many relationship table: users <-> roles
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# Many-to-many relationship table: roles <-> permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base):
    """
    Permission Model

    Represents a specific permission that can be granted to roles.
    Permissions are granular actions (e.g., "create:test", "delete:user").
    """

    __tablename__ = "permissions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Permission fields
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )  # e.g., "create:test", "delete:user"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., "test", "user", "schedule"
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., "create", "read", "update", "delete"

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name}')>"


class Role(Base):
    """
    Role Model

    Represents a role that users can be assigned. Roles group permissions together.
    """

    __tablename__ = "roles"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Role fields
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )  # e.g., "admin", "tester", "viewer"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )  # System roles cannot be deleted

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
    )
    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"

    def has_permission(self, permission_name: str) -> bool:
        """Check if this role has a specific permission."""
        return any(p.name == permission_name for p in self.permissions)

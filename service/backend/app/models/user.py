"""
User ORM Model

Represents users for authentication and authorization.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.auth import UserSession, MFASecret, EmailToken, AuditLog


class User(Base):
    """
    User Model

    Unified user model for authentication and authorization.
    Combines the legacy users table (RBAC) and user_accounts table (auth).

    Authentication features:
    - Email-based login with password hashing
    - Email verification
    - Account status (active, suspended, admin_suspended)
    - MFA support
    - Failed login attempt tracking
    - Account lockout

    Authorization features:
    - Role-based access control (RBAC)
    - Permission-based access control
    - Admin flag for system-wide access
    """

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # User fields
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Authentication status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)

    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Security fields
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
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
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    mfa_secret: Mapped[Optional["MFASecret"]] = relationship(
        "MFASecret",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    email_tokens: Mapped[list["EmailToken"]] = relationship(
        "EmailToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email='{self.email}', status='{self.status}')>"

    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(r.name == role_name for r in self.roles)

    @property
    def permission_names(self) -> set[str]:
        """Cached set of all permission names from all roles."""
        if not hasattr(self, "_cached_permissions"):
            self._cached_permissions = {
                p.name for r in self.roles for p in r.permissions
            }
        return self._cached_permissions

    def has_permission(self, permission_name: str) -> bool:
        """Check if user has a specific permission through any of their roles."""
        return permission_name in self.permission_names

    # Security methods from UserAccount
    def is_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def lock_account(self, minutes: int = 15):
        """Lock account for specified minutes"""
        from datetime import timedelta
        self.locked_until = datetime.utcnow() + timedelta(minutes=minutes)

    def unlock_account(self):
        """Unlock account"""
        self.locked_until = None
        self.failed_login_attempts = 0

    def set_email_verified(self):
        """Mark email as verified"""
        self.is_verified = True

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()

    def suspend(self, reason: str = None):
        """Suspend user account"""
        self.status = "suspended"
        self.updated_at = datetime.utcnow()

    def reactivate(self):
        """Reactivate suspended user account"""
        self.status = "active"
        self.updated_at = datetime.utcnow()

    def is_suspended(self) -> bool:
        """Check if account is suspended"""
        return self.status in ["suspended", "admin_suspended"]

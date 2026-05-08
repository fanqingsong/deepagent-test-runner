from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class UserAccount(Base):
    """User account model for authentication"""

    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    status = Column(String(50), default="active", nullable=False, index=True)  # active, suspended, admin_suspended
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    mfa_secret = relationship("MFASecret", back_populates="user", uselist=False, cascade="all, delete-orphan")
    email_tokens = relationship("EmailToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

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


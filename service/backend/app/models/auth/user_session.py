from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class UserSession(Base):
    """User session model for managing active sessions"""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(255), nullable=False, unique=True, index=True)
    device_fingerprint = Column(String(255), nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    is_remember_me = Column(Boolean, default=False, nullable=False)
    last_active = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("UserAccount", back_populates="sessions")

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at

    def refresh_last_active(self):
        """Update last active timestamp"""
        self.last_active = datetime.utcnow()

    def terminate(self):
        """Terminate session by setting expiry to now"""
        from datetime import timedelta
        self.expires_at = datetime.utcnow() - timedelta(seconds=1)

    @staticmethod
    def generate_session_token() -> str:
        """Generate secure random session token"""
        import secrets
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_expires_at(remember_me: bool) -> datetime:
        """Calculate session expiration based on remember_me flag"""
        from datetime import timedelta
        if remember_me:
            return datetime.utcnow() + timedelta(days=30)
        else:
            return datetime.utcnow() + timedelta(hours=24)

    def is_valid(self) -> bool:
        """Check if session is still valid (not expired)"""
        return not self.is_expired()

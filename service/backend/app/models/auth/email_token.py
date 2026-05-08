from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class EmailToken(Base):
    """Email verification and password reset tokens"""

    __tablename__ = "email_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    token_type = Column(String(50), nullable=False)  # verification, password_reset
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("UserAccount", back_populates="email_tokens")

    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at

    def is_used(self) -> bool:
        """Check if token has been used"""
        return self.used_at is not None

    def mark_as_used(self):
        """Mark token as used"""
        self.used_at = datetime.utcnow()

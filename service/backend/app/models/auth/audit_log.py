from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.core.database import Base


class AuditLog(Base):
    """Audit log for tracking authentication events"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # login, logout, mfa_enabled, password_changed, etc.
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    event_metadata = Column(JSON, nullable=True)  # Additional event context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    auto_delete_at = Column(DateTime, nullable=False, index=True)

    # Relationships
    user = relationship("UserAccount", back_populates="audit_logs")

    @staticmethod
    def calculate_auto_delete_at(retention_days: int = 30) -> datetime:
        """Calculate auto-deletion date based on retention policy"""
        return datetime.utcnow() + timedelta(days=retention_days)

    def to_dict(self) -> dict:
        """Convert audit log to dictionary for logging"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.event_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

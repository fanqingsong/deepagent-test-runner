from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import secrets
import hashlib


class RecoveryCode(Base):
    """MFA recovery codes for backup authentication"""

    __tablename__ = "recovery_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mfa_id = Column(Integer, ForeignKey("mfa_secrets.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(255), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    mfa_secret = relationship("MFASecret", back_populates="recovery_codes")

    def mark_as_used(self):
        """Mark recovery code as used"""
        self.is_used = True
        self.used_at = datetime.utcnow()

    @staticmethod
    def generate_code() -> str:
        """Generate a secure 10-character alphanumeric recovery code"""
        # Generate 10-character code with groups of 4-3-3 for readability
        alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        code = ''.join(secrets.choice(alphabet) for _ in range(10))
        return f"{code[:4]}-{code[4:7]}-{code[7:]}"

    @staticmethod
    def hash_code(code: str) -> str:
        """Hash the recovery code for storage using SHA256"""
        return hashlib.sha256(code.upper().encode()).hexdigest()

    @staticmethod
    def verify_code(code: str, code_hash: str) -> bool:
        """Verify a recovery code against its hash"""
        return RecoveryCode.hash_code(code) == code_hash

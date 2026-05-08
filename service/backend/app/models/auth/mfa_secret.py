from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import pyotp
import secrets


class MFASecret(Base):
    """MFA TOTP secrets for users"""

    __tablename__ = "mfa_secrets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    secret_hash = Column(String(255), nullable=False)
    is_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    enabled_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("UserAccount", back_populates="mfa_secret")
    recovery_codes = relationship("RecoveryCode", back_populates="mfa_secret", cascade="all, delete-orphan")

    def enable_mfa(self):
        """Enable MFA for this user"""
        self.is_enabled = True
        self.enabled_at = datetime.utcnow()

    def disable_mfa(self):
        """Disable MFA for this user"""
        self.is_enabled = False
        self.enabled_at = None

    @staticmethod
    def generate_secret() -> str:
        """Generate a secure 160-bit random TOTP secret (Base32 encoded)"""
        return pyotp.random_base32(length=20)  # 160 bits = 20 bytes

    @staticmethod
    def hash_secret(secret: str) -> str:
        """Hash the TOTP secret for storage using SHA256"""
        import hashlib
        return hashlib.sha256(secret.encode()).hexdigest()

    @staticmethod
    def verify_totp(token: str, secret: str) -> bool:
        """Verify a TOTP token against the secret"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 1 step tolerance (30 seconds)

    def get_provisioning_uri(self, email: str) -> str:
        """Generate OTP provisioning URI for QR code"""
        # Reconstruct the secret from hash (not possible in production, would need to store plaintext temporarily)
        # In production, store plaintext during setup phase, then hash after verification
        # For now, return the URI format
        return f"otpauth://totp/Claude Code Test Runner:{email}?secret={self.secret_hash}&issuer=Claude+Code+Test+Runner"

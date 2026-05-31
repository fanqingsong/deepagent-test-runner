"""
Email client for sending transactional emails.
For validation testing, logs to console instead of sending actual emails.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmailClient:
    """Email client for sending transactional emails"""

    def __init__(self):
        """Initialize email client"""
        self.enabled = True

    def send_verification_email(self, to_email: str, verification_url: str) -> bool:
        """
        Send email verification link.

        Args:
            to_email: Recipient email address
            verification_url: Verification URL to send

        Returns:
            True if successful
        """
        try:
            logger.info(f"[EMAIL MOCK] Verification email to {to_email}: {verification_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")
            return False

    def send_password_reset_email(self, to_email: str, reset_url: str) -> bool:
        """
        Send password reset link.

        Args:
            to_email: Recipient email address
            reset_url: Password reset URL to send

        Returns:
            True if successful
        """
        try:
            logger.info(f"[EMAIL MOCK] Password reset email to {to_email}: {reset_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            return False

    def send_mfa_enabled_email(self, to_email: str) -> bool:
        """
        Send MFA enabled notification.

        Args:
            to_email: Recipient email address

        Returns:
            True if successful
        """
        try:
            logger.info(f"[EMAIL MOCK] MFA enabled notification to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send MFA enabled email: {str(e)}")
            return False

    def send_account_suspended_email(self, to_email: str, reason: Optional[str] = None) -> bool:
        """
        Send account suspension notification.

        Args:
            to_email: Recipient email address
            reason: Optional suspension reason

        Returns:
            True if successful
        """
        try:
            logger.info(f"[EMAIL MOCK] Account suspended notification to {to_email}, reason: {reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to send account suspended email: {str(e)}")
            return False


# Global email client instance
email_client = EmailClient()

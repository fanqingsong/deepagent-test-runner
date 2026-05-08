from celery import shared_task
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

from app.core.config import settings
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


class EmailSchema(BaseModel):
    """Email task schema with validation"""
    to_email: EmailStr
    subject: str
    template_name: str  # verification, password_reset, mfa_enabled, account_suspended
    context: Dict[str, Any]
    attempt: int = 1


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=700,  # 15 minutes max
    retry_kwargs={'max_retries': 3},
    retry_jitter=True
)
def send_email_task(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send email with exponential backoff retry strategy.
    Retry delays: 30s, 5m, 15m

    Args:
        email_data: Dictionary containing email details

    Returns:
        Dict with status and failure tracking info
    """
    schema = EmailSchema(**email_data)

    # Track failure attempts
    attempt = schema.attempt

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = schema.subject
        msg['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        msg['To'] = schema.to_email

        # Generate HTML content from template
        html_content = _render_email_template(
            schema.template_name,
            schema.context
        )

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Send email via SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {schema.to_email}")

        return {
            "status": "sent",
            "to_email": schema.to_email,
            "template": schema.template_name,
            "sent_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to send email to {schema.to_email} (attempt {attempt}): {str(e)}")

        # Check if this is the final attempt
        if attempt >= 3:
            # Mark as permanently failed after 3 attempts
            _mark_email_failed(schema.to_email, schema.template_name, str(e))

            return {
                "status": "failed",
                "to_email": schema.to_email,
                "template": schema.template_name,
                "error": str(e),
                "attempts": attempt,
                "failed_at": datetime.utcnow().isoformat()
            }

        # Re-raise to trigger Celery retry with incremented attempt count
        email_data['attempt'] = attempt + 1
        raise


def _render_email_template(template_name: str, context: Dict[str, Any]) -> str:
    """Render HTML email template with context"""
    templates = {
        "verification": _render_verification_template,
        "password_reset": _render_password_reset_template,
        "mfa_enabled": _render_mfa_enabled_template,
        "account_suspended": _render_account_suspended_template,
    }

    renderer = templates.get(template_name)
    if not renderer:
        raise ValueError(f"Unknown email template: {template_name}")

    return renderer(context)


def _render_verification_template(context: Dict[str, Any]) -> str:
    """Render email verification template"""
    verification_url = context.get("verification_url", "")
    return f"""
    <html>
    <body>
        <h2>Verify Your Email Address</h2>
        <p>Please click the link below to verify your email address:</p>
        <p><a href="{verification_url}">Verify Email</a></p>
        <p>This link will expire in 24 hours.</p>
    </body>
    </html>
    """


def _render_password_reset_template(context: Dict[str, Any]) -> str:
    """Render password reset template"""
    reset_url = context.get("reset_url", "")
    return f"""
    <html>
    <body>
        <h2>Reset Your Password</h2>
        <p>Please click the link below to reset your password:</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>This link will expire in 1 hour.</p>
    </body>
    </html>
    """


def _render_mfa_enabled_template(context: Dict[str, Any]) -> str:
    """Render MFA enabled confirmation template"""
    return """
    <html>
    <body>
        <h2>MFA Enabled Successfully</h2>
        <p>Multi-factor authentication has been enabled on your account.</p>
        <p>Your recovery codes are displayed below. Please save them in a secure location:</p>
        <p><strong>{recovery_codes}</strong></p>
    </body>
    </html>
    """.format(recovery_codes=", ".join(context.get("recovery_codes", [])))


def _render_account_suspended_template(context: Dict[str, Any]) -> str:
    """Render account suspension notification template"""
    reason = context.get("reason", "Security policy violation")
    return f"""
    <html>
    <body>
        <h2>Account Suspended</h2>
        <p>Your account has been suspended.</p>
        <p><strong>Reason:</strong> {reason}</p>
        <p>Please contact support for assistance.</p>
    </body>
    </html>
    """


def _mark_email_failed(to_email: str, template: str, error: str):
    """Track email delivery failure after 3 attempts"""
    # TODO: Store in database or alert monitoring system
    logger.critical(f"Email delivery permanently failed: {to_email} | {template} | {error}")

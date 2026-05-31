"""
Temporal Email Activities.

Activities for sending emails via SMTP.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

from temporalio import activity

from app.core.config import settings

logger = logging.getLogger(__name__)


@activity.defn
async def send_email(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send an email via SMTP.

    Args:
        email_data: Dictionary containing:
            - to_email: Recipient email address
            - subject: Email subject
            - template_name: Template name for rendering
            - context: Template context variables

    Returns:
        Dict with send status and metadata
    """
    activity_info = activity.info()
    logger.info(
        f"Sending email to {email_data.get('to_email')} "
        f"(attempt {activity_info.attempt})"
    )

    try:
        to_email = email_data["to_email"]
        subject = email_data["subject"]
        template_name = email_data["template_name"]
        context = email_data.get("context", {})

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        msg["To"] = to_email

        # Render and attach HTML content
        html_content = _render_email_template(template_name, context)
        msg.attach(MIMEText(html_content, "html"))

        # Send via SMTP
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()

        with server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}")

        return {
            "status": "sent",
            "to_email": to_email,
            "template": template_name,
        }

    except Exception as e:
        logger.error(
            f"Failed to send email to {email_data.get('to_email')}: {str(e)}"
        )
        raise


def _render_email_template(template_name: str, context: Dict[str, Any]) -> str:
    """Render an email template with context.

    Args:
        template_name: Name of the template to render
        context: Variables to substitute in the template

    Returns:
        Rendered HTML string
    """
    templates = {
        "verification": _render_verification_template,
        "password_reset": _render_password_reset_template,
        "mfa_enabled": _render_mfa_enabled_template,
        "account_suspended": _render_account_suspended_template,
        "test_failure": _render_test_failure_template,
        "test_completion": _render_test_completion_template,
    }

    renderer = templates.get(template_name)
    if not renderer:
        raise ValueError(f"Unknown email template: {template_name}")

    return renderer(context)


def _render_verification_template(context: Dict[str, Any]) -> str:
    """Render email verification template."""
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
    """Render password reset template."""
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
    """Render MFA enabled template."""
    recovery_codes = ", ".join(context.get("recovery_codes", []))
    return f"""
    <html>
    <body>
        <h2>MFA Enabled Successfully</h2>
        <p>Multi-factor authentication has been enabled on your account.</p>
        <p>Your recovery codes are displayed below. Please save them in a secure location:</p>
        <p><strong>{recovery_codes}</strong></p>
    </body>
    </html>
    """


def _render_account_suspended_template(context: Dict[str, Any]) -> str:
    """Render account suspension template."""
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


def _render_test_failure_template(context: Dict[str, Any]) -> str:
    """Render test failure notification template."""
    test_name = context.get("test_name", "Unknown Test")
    failure_reason = context.get("failure_reason", "Unknown error")
    dashboard_url = context.get("dashboard_url", "")
    return f"""
    <html>
    <body>
        <h2>Test Failure Alert</h2>
        <p>The following test has failed:</p>
        <p><strong>{test_name}</strong></p>
        <p><strong>Failure Reason:</strong> {failure_reason}</p>
        <p><a href="{dashboard_url}">View Details</a></p>
    </body>
    </html>
    """


def _render_test_completion_template(context: Dict[str, Any]) -> str:
    """Render test completion notification template."""
    test_name = context.get("test_name", "Unknown Test")
    status = context.get("status", "completed")
    dashboard_url = context.get("dashboard_url", "")
    return f"""
    <html>
    <body>
        <h2>Test Completion Notification</h2>
        <p>The following test has {status}:</p>
        <p><strong>{test_name}</strong></p>
        <p><a href="{dashboard_url}">View Details</a></p>
    </body>
    </html>
    """

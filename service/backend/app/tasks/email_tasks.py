try:
    from celery import shared_task
except ImportError:
    shared_task = None
from pydantic import BaseModel, EmailStr
from typing import Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailSchema(BaseModel):
    to_email: EmailStr
    subject: str
    template_name: str
    context: Dict[str, Any]


def send_email_sync(to_email: str, subject: str, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Send email directly via SMTP. Can be called from any process."""
    schema = EmailSchema(to_email=to_email, subject=subject, template_name=template_name, context=context)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = schema.subject
    msg['From'] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg['To'] = schema.to_email

    html_content = _render_email_template(schema.template_name, schema.context)
    msg.attach(MIMEText(html_content, 'html'))

    if settings.SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
    else:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
    with server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)

    logger.info(f"Email sent successfully to {schema.to_email}")
    return {"status": "sent", "to_email": schema.to_email, "template": schema.template_name}


async def send_email_async(to_email: str, subject: str, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Send email in a thread pool, non-blocking for async callers."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        send_email_sync,
        to_email, subject, template_name, context,
    )


def send_email_task(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Celery task wrapper for email sending."""
    try:
        return send_email_sync(
            to_email=email_data["to_email"],
            subject=email_data["subject"],
            template_name=email_data["template_name"],
            context=email_data["context"],
        )
    except Exception as e:
        logger.error(f"Failed to send email to {email_data.get('to_email')}: {str(e)}")
        raise


def _render_email_template(template_name: str, context: Dict[str, Any]) -> str:
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

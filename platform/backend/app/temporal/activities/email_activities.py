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
from app.utils.email_templates import render_email_template

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
        html_content = render_email_template(template_name, context)
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

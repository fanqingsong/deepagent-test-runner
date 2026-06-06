from pydantic import BaseModel, EmailStr
from typing import Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
import logging

from app.core.config import settings
from app.utils.email_templates import render_email_template

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

    html_content = render_email_template(schema.template_name, schema.context)
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

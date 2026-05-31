"""
Email Tools — Send emails and query sent email history.

Provides tools for the email subagent with a confirmation flow:
preview -> user confirms -> send.
"""

import asyncio
import json
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy import select

from app.core.config import settings
from app.core.database import sync_session_maker
from app.models.email_sent_log import EmailSentLog
from app.agents.chat_assistant.tool_context import get_current_user_id
from app.agents.chat_assistant.chat_tools import _resolve_user_id
from app.utils.email import is_valid_email_format

logger = logging.getLogger(__name__)


@tool
async def preview_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
) -> str:
    """Preview an email before sending. Does NOT send the email.

    Use this first to show the user what will be sent, then wait for
    explicit confirmation before calling send_email_tool.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content (plain text)
        cc: Optional CC email address
    """
    errors = []
    if not is_valid_email_format(to):
        errors.append(f"Invalid recipient address: {to}")
    if cc and not is_valid_email_format(cc):
        errors.append(f"Invalid CC address: {cc}")
    if not subject.strip():
        errors.append("Subject cannot be empty")
    if not body.strip():
        errors.append("Body cannot be empty")

    if errors:
        return json.dumps({"success": False, "errors": errors}, ensure_ascii=False)

    preview = {
        "success": True,
        "action": "preview",
        "email": {
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
            "to": to,
            "cc": cc or "(none)",
            "subject": subject,
            "body_preview": body[:300] + ("..." if len(body) > 300 else ""),
        },
        "message": "Please confirm to send this email.",
    }
    return json.dumps(preview, ensure_ascii=False)


@tool
async def send_email_tool(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
) -> str:
    """Send an email via SMTP and log it. Only call after user confirmation.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content (plain text)
        cc: Optional CC email address
    """
    if not is_valid_email_format(to):
        return json.dumps({"success": False, "error": f"Invalid recipient: {to}"}, ensure_ascii=False)
    if cc and not is_valid_email_format(cc):
        return json.dumps({"success": False, "error": f"Invalid CC: {cc}"}, ensure_ascii=False)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(body, "plain"))

    user_id = _resolve_user_id()

    try:
        result = await asyncio.get_running_loop().run_in_executor(
            None, _smtp_send_and_log, msg, user_id, to, subject, body[:200], cc,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return json.dumps({"success": False, "error": str(e)[:500]}, ensure_ascii=False)


def _smtp_send_and_log(msg, user_id, to, subject, body_preview, cc):
    """Blocking SMTP send + DB log, run in thread pool."""
    sent_at = datetime.utcnow()
    status = "sent"
    error_msg = None

    try:
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
        with server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email sent to {to}, subject='{subject}'")
    except Exception as e:
        status = "failed"
        error_msg = str(e)[:500]
        logger.error(f"Failed to send email to {to}: {e}")

    try:
        with sync_session_maker() as db:
            log = EmailSentLog(
                sender_id=user_id,
                to_email=to,
                subject=subject,
                body_preview=body_preview,
                cc=cc,
                status=status,
                error_message=error_msg,
                sent_at=sent_at,
            )
            db.add(log)
            db.commit()
    except Exception as e:
        logger.error(f"Could not log email sent record: {e}")

    if status == "sent":
        return json.dumps({"success": True, "to": to, "subject": subject}, ensure_ascii=False)
    else:
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)


@tool
async def query_sent_emails(
    limit: int = 10,
    recipient_filter: Optional[str] = None,
) -> str:
    """Query previously sent emails from the email agent.

    Args:
        limit: Maximum number of records to return (default 10, max 50)
        recipient_filter: Optional filter by recipient email (partial match)

    Returns:
        Formatted list of sent email records
    """
    if limit < 1:
        limit = 1
    elif limit > 50:
        limit = 50

    user_id = _resolve_user_id()

    try:
        return await asyncio.get_running_loop().run_in_executor(
            None, _query_sent_emails_sync, user_id, limit, recipient_filter,
        )
    except Exception as e:
        logger.error(f"Error querying sent emails: {e}")
        return f"Error querying sent emails: {str(e)}"


def _query_sent_emails_sync(user_id, limit, recipient_filter):
    """Blocking DB query, run in thread pool."""
    try:
        with sync_session_maker() as db:
            stmt = (
                select(EmailSentLog)
                .where(EmailSentLog.sender_id == user_id)
                .order_by(EmailSentLog.sent_at.desc())
                .limit(limit)
            )

            if recipient_filter:
                stmt = stmt.where(EmailSentLog.to_email.ilike(f"%{recipient_filter}%"))

            results = db.execute(stmt)
            logs = results.scalars().all()

            if not logs:
                return "No sent emails found."

            lines = [f"Found {len(logs)} sent email(s):\n"]
            for log in logs:
                status_icon = "OK" if log.status == "sent" else "FAIL"
                ts = log.sent_at.strftime("%Y-%m-%d %H:%M") if log.sent_at else "N/A"
                lines.append(
                    f"[{status_icon}] To: {log.to_email} | Subject: {log.subject} | {ts}"
                )
                if log.body_preview:
                    lines.append(f"     Preview: {log.body_preview}")
                if log.error_message:
                    lines.append(f"     Error: {log.error_message}")

            return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error in _query_sent_emails_sync: {e}")
        return f"Error querying sent emails: {str(e)}"

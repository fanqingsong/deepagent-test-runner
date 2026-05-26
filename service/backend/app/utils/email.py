import logging
from typing import Any, Dict
from uuid import uuid4
from email_validator import validate_email as email_validate

logger = logging.getLogger(__name__)


def is_valid_email_format(email: str) -> bool:
    try:
        email_validate(email, check_deliverability=False)
        return True
    except:
        return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def extract_email_domain(email: str) -> str:
    try:
        return email.split('@')[1].lower()
    except IndexError:
        return ""


async def send_email(
    to_email: str,
    subject: str,
    template_name: str,
    context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Send an email via Temporal workflow (fire-and-forget)."""
    email_data = {
        "to_email": to_email,
        "subject": subject,
        "template_name": template_name,
        "context": context or {},
    }
    try:
        from app.temporal import get_temporal_client
        from app.temporal.settings import settings as temporal_settings
        from app.workflows.emails import EmailWorkflow

        client = await get_temporal_client()
        handle = await client.start_workflow(
            EmailWorkflow.run,
            email_data,
            id=f"email-{uuid4().hex[:12]}",
            task_queue=temporal_settings.task_queue,
        )
        logger.info(f"Email workflow dispatched: {handle.id} for {to_email}")
        return {"status": "dispatched", "to": to_email, "subject": subject, "workflow_id": handle.id}
    except Exception as e:
        logger.warning(f"Temporal unavailable, email not sent to {to_email}: {e}")
        return {"status": "temporal_unavailable", "to": to_email, "subject": subject}

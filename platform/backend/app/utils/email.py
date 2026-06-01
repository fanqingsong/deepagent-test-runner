import re
import time
from typing import Tuple, Dict, Any
from email_validator import validate_email as email_validate


def is_valid_email_format(email: str) -> bool:
    """
    Validate email format using RFC 5322 standard.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise
    """
    try:
        email_validate(email, check_deliverability=False)
        return True
    except Exception:
        return False


def normalize_email(email: str) -> str:
    """
    Normalize email address (lowercase, trim whitespace).

    Args:
        email: Email address to normalize

    Returns:
        Normalized email address
    """
    return email.strip().lower()


def extract_email_domain(email: str) -> str:
    """
    Extract domain from email address.

    Args:
        email: Email address

    Returns:
        Domain portion of email
    """
    try:
        return email.split('@')[1].lower()
    except IndexError:
        return ""


async def send_email_via_temporal(
    to_email: str,
    subject: str,
    template_name: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Send email via Temporal workflow.

    Args:
        to_email: Recipient email address
        subject: Email subject
        template_name: Template name for rendering
        context: Template context variables

    Returns:
        Dict with send status and workflow_id
    """
    from app.temporal.client import get_temporal_client
    from app.temporal.workflows.emails import EmailWorkflow

    client = await get_temporal_client()
    workflow_id = f"email-{template_name}-{int(time.time())}"

    await client.start_workflow(
        EmailWorkflow.run,
        args=[to_email, subject, template_name, context],
        id=workflow_id,
        task_queue="unified-backend-task-queue",
    )

    return {"status": "queued", "workflow_id": workflow_id}


async def send_email(
    to_email: str,
    subject: str,
    template_name: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Send email using configured backend.

    Args:
        to_email: Recipient email address
        subject: Email subject
        template_name: Template name for rendering
        context: Template context variables

    Returns:
        Dict with send status
    """
    from app.core.config import settings

    if settings.EMAIL_BACKEND == "temporal":
        return await send_email_via_temporal(to_email, subject, template_name, context)
    else:  # sync
        from app.utils.email_tasks import send_email_sync
        return await send_email_sync(to_email, subject, template_name, context)

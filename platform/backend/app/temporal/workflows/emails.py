# service/backend/app/workflows/emails.py
"""
Workflow for sending emails.
"""
import logging
from datetime import timedelta
from typing import List, Dict, Any
from temporalio import workflow

from app.temporal.activities import get_default_retry_policy
from app.temporal.activities.email_activities import send_email

logger = logging.getLogger(__name__)


@workflow.defn(sandboxed=False)
class EmailWorkflow:
    """
    Workflow for sending emails using template system.
    """

    @workflow.run
    async def run(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send an email using a template.

        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Template name for rendering
            context: Template context variables

        Returns:
            Dict with send status
        """
        logger.info(f"Sending email to {to_email} using template: {template_name}")

        result = await workflow.execute_activity(
            send_email,
            {
                "to_email": to_email,
                "subject": subject,
                "template_name": template_name,
                "context": context,
            },
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=get_default_retry_policy()
        )

        return result

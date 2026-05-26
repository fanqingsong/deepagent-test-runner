# service/backend/app/workflows/emails.py
"""
Workflow for sending emails.
"""
import logging
from datetime import timedelta
from typing import Dict, Any
from temporalio import workflow

from app.activities import get_default_retry_policy
from app.activities.email_activities import send_email

logger = logging.getLogger(__name__)


@workflow.defn(sandboxed=False)
class EmailWorkflow:
    """
    Workflow for sending emails via Temporal.
    """

    @workflow.run
    async def run(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send an email.

        Args:
            email_data: Dict with keys: to_email, subject, template_name, context

        Returns:
            Dict with send status
        """
        logger.info(f"Sending email to {email_data.get('to_email')}")

        result = await workflow.execute_activity(
            send_email,
            email_data,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=get_default_retry_policy()
        )

        return result

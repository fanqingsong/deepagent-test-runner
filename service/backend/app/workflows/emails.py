# service/backend/app/workflows/emails.py
"""
Workflow for sending emails.
"""
import logging
from datetime import timedelta
from typing import List, Dict, Any
from temporalio import workflow

from app.activities import get_default_retry_policy
from app.activities.email_activities import send_email

logger = logging.getLogger(__name__)


@workflow.defn(sandboxed=False)
class EmailWorkflow:
    """
    Workflow for sending emails.
    """

    @workflow.run
    async def run(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        html_body: str = None
    ) -> Dict[str, Any]:
        """
        Send an email.

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body

        Returns:
            Dict with send status
        """
        logger.info(f"Sending email to {len(to_addresses)} recipients")

        result = await workflow.execute_activity(
            send_email,
            to_addresses,
            subject,
            body,
            html_body,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=get_default_retry_policy()
        )

        return result

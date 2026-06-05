# service/backend/app/activities/__init__.py
"""
Temporal Activities.

Activities are the basic units of work in Temporal. They are functions that
execute synchronously and can be retried on failure.
"""

from datetime import timedelta
from temporalio import activity
from temporalio.common import RetryPolicy

# Activity retry policies
def get_default_retry_policy() -> RetryPolicy:
    """Default retry policy for most activities."""
    return RetryPolicy(
        initial_interval=timedelta(seconds=1),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=1),
        maximum_attempts=3,
    )

def get_long_running_retry_policy() -> RetryPolicy:
    """Retry policy for long-running activities like browser automation."""
    return RetryPolicy(
        initial_interval=timedelta(seconds=5),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=2),
        maximum_attempts=2,
        non_retryable_error_types=["ValidationError", "AuthError"],
    )

from app.temporal.activities.test_activities import (
    prepare_test,
    run_browser_automation,
    save_results,
    mark_run_failed,
)

from app.temporal.activities.deepagents_activities import (
    run_deepagents_automation,
)

from app.temporal.activities.schedule_activities import (
    execute_scheduled_test,
)

from app.temporal.activities.email_activities import send_email

__all__ = [
    "get_default_retry_policy",
    "get_long_running_retry_policy",
    "prepare_test",
    "run_browser_automation",
    "run_deepagents_automation",
    "save_results",
    "mark_run_failed",
    "execute_scheduled_test",
    "send_email",
]

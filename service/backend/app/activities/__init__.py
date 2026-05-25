# service/backend/app/activities/__init__.py
"""
Temporal Activities.

Activities are the basic units of work in Temporal. They are functions that
execute synchronously and can be retried on failure.
"""

from datetime import timedelta
from temporalio import activity

# Activity retry policies
def get_default_retry_policy() -> activity.RetryPolicy:
    """Default retry policy for most activities."""
    return activity.RetryPolicy(
        initial_interval=timedelta(seconds=1),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=1),
        maximum_attempts=3,
    )

def get_long_running_retry_policy() -> activity.RetryPolicy:
    """Retry policy for long-running activities like browser automation."""
    return activity.RetryPolicy(
        initial_interval=timedelta(seconds=5),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=2),
        maximum_attempts=2,
        non_retryable_error_types=["ValidationError", "AuthError"],
    )

from app.activities.test_activities import (
    prepare_test,
    run_browser_automation,
    save_results,
    mark_run_failed,
)

from app.activities.schedule_activities import (
    get_active_schedules,
    update_schedule_next_run,
    execute_scheduled_test,
)

__all__ = [
    "get_default_retry_policy",
    "get_long_running_retry_policy",
    "prepare_test",
    "run_browser_automation",
    "save_results",
    "mark_run_failed",
    "get_active_schedules",
    "update_schedule_next_run",
    "execute_scheduled_test",
]

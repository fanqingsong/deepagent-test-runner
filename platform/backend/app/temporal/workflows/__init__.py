from datetime import timedelta
from temporalio import workflow

DEFAULT_EXECUTION_TIMEOUT = timedelta(hours=1)
DEFAULT_RUN_TIMEOUT = timedelta(minutes=10)

from app.temporal.workflows.test_execution import TestExecutionWorkflow, RetryTestWorkflow
from app.temporal.workflows.monitoring_workflow import MonitoringAgentWorkflow

__all__ = [
    "DEFAULT_EXECUTION_TIMEOUT",
    "DEFAULT_RUN_TIMEOUT",
    "TestExecutionWorkflow",
    "RetryTestWorkflow",
    "MonitoringAgentWorkflow",
]

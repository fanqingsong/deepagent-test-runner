from datetime import timedelta
from temporalio import workflow

DEFAULT_EXECUTION_TIMEOUT = timedelta(hours=1)
DEFAULT_RUN_TIMEOUT = timedelta(minutes=10)

__all__ = ["DEFAULT_EXECUTION_TIMEOUT", "DEFAULT_RUN_TIMEOUT"]

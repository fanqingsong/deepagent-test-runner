# service/backend/app/temporal/settings.py
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class TemporalSettings:
    """Temporal configuration settings."""

    host_url: str = os.getenv(
        "TEMPORAL_HOST_URL",
        "localhost:7233"
    )
    namespace: str = os.getenv(
        "TEMPORAL_NAMESPACE",
        "default"
    )
    task_queue: str = os.getenv(
        "TEMPORAL_TASK_QUEUE",
        "unified-backend-task-queue"
    )
    workflow_execution_timeout: int = int(
        os.getenv("TEMPORAL_EXECUTION_TIMEOUT", "3600")
    )  # 1 hour default

# Singleton instance
settings = TemporalSettings()
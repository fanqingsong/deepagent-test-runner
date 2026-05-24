"""
Celery Application Configuration for Unified Backend Service

Configures Celery for distributed task queue with Redis broker.
"""

import logging

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Celery application
celery_app = Celery(
    "unified_backend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.test_execution",
        "app.tasks.schedule_sync",
        "app.tasks.email_tasks",
        "app.tasks.maintenance_tasks"
    ]
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "app.tasks.test_execution.execute_test": {"queue": "test_execution"},
        "app.tasks.test_execution.retry_test_with_modifications": {"queue": "test_execution"},
        "app.tasks.test_execution.execute_suite": {"queue": "test_execution"},
        "app.tasks.schedule_sync.*": {"queue": "schedule_sync"},
        "app.tasks.email_tasks.*": {"queue": "email_tasks"},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
    },

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Task timeout — kill tasks that run too long (10 min hard, 9 min soft)
    task_time_limit=600,
    task_soft_time_limit=540,

    # Task result settings
    result_expires=3600,  # 1 hour
    task_track_started=True,

    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# After fork, recreate DB engine to avoid "Future attached to a different loop"
@worker_process_init.connect
def _on_worker_process_init(**kwargs):
    try:
        import app.core.database as db
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        db.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
        db.async_session_maker = async_sessionmaker(
            db.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        logger.info("Recreated DB engine after worker fork")
    except Exception as exc:
        logger.warning("Failed to recreate engine after fork: %s", exc)


# Configure periodic tasks for Celery Beat
from celery.schedules import crontab

# Maintenance tasks only - user schedules are synced dynamically
celery_app.conf.beat_schedule = {
    # Sync schedules to Celery Beat every 5 minutes
    "sync-schedules-to-beat": {
        "task": "app.tasks.schedule_sync.sync_schedules_to_beat",
        "schedule": crontab(minute='*/5'),
    },
    # Check for overdue schedules every minute
    "check-overdue-schedules": {
        "task": "app.tasks.schedule_sync.check_overdue_schedules",
        "schedule": crontab(minute='*'),
    },
    # Clean up old test runs daily at 2 AM
    "cleanup-old-test-runs": {
        "task": "app.tasks.schedule_sync.cleanup_old_test_runs",
        "schedule": crontab(hour=2, minute=0),
    },
    # Auth maintenance tasks
    "cleanup-expired-sessions": {
        "task": "app.tasks.maintenance_tasks.cleanup_expired_sessions_task",
        "schedule": crontab(minute='*/30'),  # Every 30 minutes
    },
    "cleanup-old-audit-logs": {
        "task": "app.tasks.maintenance_tasks.cleanup_audit_logs_task",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "reset-locked-accounts": {
        "task": "app.tasks.maintenance_tasks.reset_locked_accounts_task",
        "schedule": crontab(minute='*/5'),  # Every 5 minutes
    },
}

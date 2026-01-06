from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "cloudshift",
    broker=settings.REDIS_URL or "redis://localhost:6379/0",
    backend=settings.REDIS_URL or "redis://localhost:6379/0",
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Recycle worker after 50 tasks
    task_acks_late=True,  # Only ack after task completion
    task_reject_on_worker_lost=True,
    result_expires=3600,  # Results expire after 1 hour
)

# Task retry configuration
celery_app.conf.task_default_retry_delay = 60  # Retry after 60 seconds
celery_app.conf.task_max_retries = 3

# Auto-discover tasks from all installed apps
celery_app.autodiscover_tasks(["app.services"])

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "check-scheduled-transfers": {
        "task": "app.services.transfers.check_scheduled_transfers",
        "schedule": crontab(minute="*"),  # Run every minute
    },
    "cleanup-old-audit-logs": {
        "task": "app.services.audit.cleanup_old_logs",
        "schedule": crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
}

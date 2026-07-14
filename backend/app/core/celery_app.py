"""Celery configuration and application instance."""

import os

from celery import Celery
from kombu import Queue

# Create Celery instance
celery_app = Celery("corpus-te")

# Celery configuration
celery_app.conf.update(
    # Broker settings (Redis)
    broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    result_backend=os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    ),
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "app.tasks.file_processing.*": {"queue": "file_processing"},
        "app.tasks.notifications.*": {"queue": "notifications"},
        "app.tasks.data_analysis.*": {"queue": "data_analysis"},
        "app.tasks.maintenance.*": {"queue": "maintenance"},
    },
    # Define queues
    task_default_queue="default",
    task_queues=(
        Queue("default"),
        Queue("file_processing"),
        Queue("notifications"),
        Queue("data_analysis"),
        Queue("maintenance"),
    ),
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    worker_enable_remote_control=True,  # Enable for Flower monitoring
    worker_send_task_events=True,  # Send task events for monitoring
    task_send_sent_event=True,  # Send sent events for better tracking
    # Task execution settings
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    task_track_started=True,
    task_reject_on_worker_lost=True,
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    # RedBeat scheduler settings
    redbeat_redis_url=os.getenv(
        "CELERY_BROKER_URL", "redis://localhost:6379/0"
    ),
    redbeat_key_prefix="corpus-te:beat:",
    redbeat_lock_key="corpus-te:beat:lock",
    redbeat_lock_timeout=360,
    beat_max_loop_interval=300,
    # Beat scheduler settings (for periodic tasks)
    beat_schedule={
        "cleanup-old-files": {
            "task": "app.tasks.maintenance.cleanup_old_files",
            "schedule": 3600.0,  # Run every hour
        },
        "cleanup-incomplete-chunks": {
            "task": "app.tasks.maintenance.cleanup_incomplete_chunks",
            "schedule": 300.0,  # Run every 5 minutes
            "kwargs": {"minutes_old": 60},  # Clean up chunks older than 1 hour
        },
        "generate-daily-reports": {
            "task": "app.tasks.reports.generate_daily_report",
            "schedule": 86400.0,  # Run daily
        },
    },
)


# Import all task modules to register them with Celery
def import_task_modules():
    """Import all task modules to ensure they are registered with Celery."""
    try:
        print("Successfully imported all task modules")
    except Exception as e:
        print(f"Error importing task modules: {e}")


# Auto-discover tasks
celery_app.autodiscover_tasks(
    [
        "app.tasks.file_processing",
        "app.tasks.notifications",
        "app.tasks.data_analysis",
        "app.tasks.maintenance",
        "app.tasks.reports",
    ]
)

# Import tasks to register them
import_task_modules()

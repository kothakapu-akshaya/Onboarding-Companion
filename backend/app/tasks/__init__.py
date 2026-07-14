"""Task registration module for Celery.

Import all task modules to ensure they're registered with Celery.
"""

# Import all task modules to register them with Celery
from . import (
    data_analysis,
    file_processing,
    maintenance,
    notifications,
    reports,
)
from .data_analysis import (
    analyze_audio_content,
    batch_language_detection,
    generate_corpus_statistics,
)

# Re-export commonly used tasks for convenience
from .file_processing import process_audio_file, upload_to_storage
from .maintenance import (
    backup_database,
    cleanup_old_files,
    health_check,
    optimize_database,
)
from .notifications import (
    send_bulk_notification,
    send_email,
    send_processing_complete_notification,
    send_system_alert,
)
from .reports import (
    export_user_data,
    generate_daily_report,
    generate_system_health_report,
    generate_user_report,
)

__all__ = [
    # Task modules (imported for Celery registration)
    "file_processing",
    "notifications",
    "data_analysis",
    "maintenance",
    "reports",
    # File processing tasks
    "process_audio_file",
    "upload_to_storage",
    # Notification tasks
    "send_email",
    "send_processing_complete_notification",
    "send_bulk_notification",
    "send_system_alert",
    # Data analysis tasks
    "analyze_audio_content",
    "generate_corpus_statistics",
    "batch_language_detection",
    # Maintenance tasks
    "cleanup_old_files",
    "optimize_database",
    "health_check",
    "backup_database",
    # Reporting tasks
    "generate_daily_report",
    "generate_user_report",
    "generate_system_health_report",
    "export_user_data",
]

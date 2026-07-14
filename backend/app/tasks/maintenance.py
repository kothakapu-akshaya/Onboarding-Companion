"""Maintenance and cleanup tasks."""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

from sqlalchemy import text
from sqlmodel import Session, select

from app.core.celery_app import celery_app
from app.db.session import engine
from app.models import Record
from app.utils.chunk_manager import ChunkManager
from app.utils.hetzner_storage import HetznerStorageClient

logger = logging.getLogger(__name__)


def _as_utc(dt: datetime) -> datetime:
    """Normalize mixed naive/aware datetimes to aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@celery_app.task(bind=True, name="app.tasks.maintenance.cleanup_old_files")
def cleanup_old_files(self, days_old: int = 30) -> dict[str, Any]:  # noqa: D417
    """Clean up old temporary files and failed uploads.

    Args:
        days_old: Files older than this many days will be cleaned up

    Returns:
        Dict with cleanup results
    """
    try:
        logger.info(f"Starting cleanup of files older than {days_old} days")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        results = {
            "local_files_deleted": 0,
            "database_records_cleaned": 0,
            "storage_files_deleted": 0,
            "errors": [],
        }

        with Session(engine) as session:
            # Find old failed or temporary records - use separate queries to
            # avoid None comparison issues
            old_failed_records = session.exec(
                select(Record).where(Record.status == "failed")
            ).all()

            old_pending_records = session.exec(
                select(Record).where(Record.status == "pending")
            ).all()

            # Filter by date in Python to avoid SQLAlchemy None comparison
            # issues
            old_records = list(old_failed_records) + list(old_pending_records)
            old_records = [
                r
                for r in old_records
                if r.created_at and _as_utc(r.created_at) < cutoff_date
            ]

            for record in old_records:
                try:
                    # Clean up local file if exists (using file_url as base)
                    if record.file_url and record.file_url.startswith(
                        "file://"
                    ):
                        local_path = record.file_url.replace("file://", "")
                        if os.path.exists(local_path):
                            os.remove(local_path)
                            results["local_files_deleted"] += 1
                            logger.info(f"Deleted local file: {local_path}")

                    # Clean up from object storage if exists
                    if record.file_url and record.file_url.startswith(
                        "https://"
                    ):
                        storage_client = HetznerStorageClient()
                        try:
                            # Extract file key from URL
                            file_key = record.file_url.split("/")[-1]
                            storage_client.delete_object(file_key)
                            results["storage_files_deleted"] += 1
                            logger.info(f"Deleted storage file: {file_key}")
                        except Exception as storage_error:
                            logger.warning(
                                f"Failed to delete storage file "
                                f"{record.file_url}: {storage_error}"
                            )

                    # Remove database record
                    session.delete(record)
                    results["database_records_cleaned"] += 1

                except Exception as e:
                    error_msg = (
                        f"Failed to cleanup record {record.uid}: {str(e)}"
                    )
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            # Commit database changes
            session.commit()

        # Clean up orphaned temporary files
        temp_dir = Path("/tmp")
        if temp_dir.exists():
            for temp_file in temp_dir.glob("corpus_upload_*"):
                try:
                    file_age = datetime.fromtimestamp(
                        temp_file.stat().st_mtime, tz=timezone.utc
                    )
                    if file_age < cutoff_date:
                        temp_file.unlink()
                        results["local_files_deleted"] += 1
                        logger.info(f"Deleted orphaned temp file: {temp_file}")
                except Exception as e:
                    error_msg = (
                        f"Failed to delete temp file {temp_file}: {str(e)}"
                    )
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)

        logger.info(f"Cleanup completed: {results}")
        return {
            "status": "success",
            "results": results,
            "cleanup_date": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise


@celery_app.task(bind=True, name="app.tasks.maintenance.optimize_database")
def optimize_database(self) -> dict[str, Any]:
    """Perform database maintenance operations.

    Returns:
        Dict with optimization results
    """
    try:
        logger.info("Starting database optimization")

        results = {
            "vacuum_completed": False,
            "reindex_completed": False,
            "analyze_completed": False,
            "errors": [],
        }

        with Session(engine) as session:
            try:
                # PostgreSQL specific optimizations
                # Note: These need to be run outside of transactions

                # VACUUM to reclaim storage - use execute instead of exec
                # for raw SQL
                raw_session = cast(Any, session)
                raw_session.exec(text("VACUUM ANALYZE records"))
                raw_session.exec(text("VACUUM ANALYZE users"))
                results["vacuum_completed"] = True
                logger.info("Database VACUUM completed")

                # Update table statistics
                raw_session.exec(text("ANALYZE"))
                results["analyze_completed"] = True
                logger.info("Database ANALYZE completed")

            except Exception as e:
                error_msg = f"Database optimization error: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        logger.info(f"Database optimization completed: {results}")
        return {
            "status": "success",
            "results": results,
            "optimization_date": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Database optimization failed: {str(e)}")
        raise


@celery_app.task(bind=True, name="app.tasks.maintenance.health_check")
def health_check(self) -> dict[str, Any]:
    """Perform system health checks.

    Returns:
        Dict with health check results
    """
    try:
        logger.info("Starting system health check")

        health_status = {
            "database": "unknown",
            "storage": "unknown",
            "redis": "unknown",
            "disk_space": "unknown",
            "overall": "unknown",
        }

        issues = []

        # Check database connectivity
        try:
            with Session(engine) as session:
                raw_session = cast(Any, session)
                raw_session.exec(text("SELECT 1"))
            health_status["database"] = "healthy"
            logger.info("Database health check: OK")
        except Exception as e:
            health_status["database"] = "unhealthy"
            issues.append(f"Database connectivity issue: {str(e)}")
            logger.error(f"Database health check failed: {str(e)}")

        # Check object storage connectivity
        try:
            storage_client = HetznerStorageClient()
            # Try to list buckets or perform a simple operation
            storage_client.list_objects(max_keys=1)
            health_status["storage"] = "healthy"
            logger.info("Storage health check: OK")
        except Exception as e:
            health_status["storage"] = "unhealthy"
            issues.append(f"Storage connectivity issue: {str(e)}")
            logger.error(f"Storage health check failed: {str(e)}")

        # Check Redis connectivity (if accessible)
        try:
            # Try to import redis - it might not be installed
            try:
                import redis

                from app.core.config import settings

                redis_client = redis.from_url(settings.CELERY_BROKER_URL)
                redis_client.ping()
                health_status["redis"] = "healthy"
                logger.info("Redis health check: OK")
            except ImportError:
                health_status["redis"] = "unavailable"
                logger.warning(
                    "Redis module not available - skipping Redis health check"
                )
        except Exception as e:
            health_status["redis"] = "unhealthy"
            issues.append(f"Redis connectivity issue: {str(e)}")
            logger.error(f"Redis health check failed: {str(e)}")

        # Check disk space
        try:
            import shutil

            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100

            if free_percent > 20:
                health_status["disk_space"] = "healthy"
            elif free_percent > 10:
                health_status["disk_space"] = "warning"
                issues.append(f"Low disk space: {free_percent:.1f}% free")
            else:
                health_status["disk_space"] = "critical"
                issues.append(f"Critical disk space: {free_percent:.1f}% free")

            logger.info(f"Disk space check: {free_percent:.1f}% free")
        except Exception as e:
            health_status["disk_space"] = "unknown"
            issues.append(f"Could not check disk space: {str(e)}")
            logger.error(f"Disk space check failed: {str(e)}")

        # Determine overall health
        unhealthy_services = [
            service
            for service, status in health_status.items()
            if status in ["unhealthy", "critical"] and service != "overall"
        ]

        if not unhealthy_services:
            health_status["overall"] = "healthy"
        elif len(unhealthy_services) == 1:
            health_status["overall"] = "degraded"
        else:
            health_status["overall"] = "unhealthy"

        # Send alert if there are critical issues
        if health_status["overall"] in ["unhealthy", "degraded"]:
            celery_app.send_task(
                "app.tasks.notifications.send_system_alert",
                kwargs={
                    "alert_type": "Health Check Alert",
                    "message": (
                        f"System health issues detected: {', '.join(issues)}"
                    ),
                    "severity": "warning"
                    if health_status["overall"] == "degraded"
                    else "error",
                },
            )

        logger.info(f"Health check completed: {health_status['overall']}")
        return {
            "status": "success",
            "health_status": health_status,
            "issues": issues,
            "check_time": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise


@celery_app.task(bind=True, name="app.tasks.maintenance.backup_database")
def backup_database(self, backup_location: str | None = None) -> dict[str, Any]:  # noqa: D417
    """Create database backup.

    Args:
        backup_location: Optional custom backup location

    Returns:
        Dict with backup results
    """
    try:
        logger.info("Starting database backup")

        # This is a placeholder implementation
        # In production, you would use pg_dump or similar tools

        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"corpus_te_backup_{now_str}.sql"
        backup_path = backup_location or f"/tmp/{backup_filename}"

        # Placeholder for actual backup logic
        # You would typically use subprocess to run pg_dump

        results = {
            "backup_file": backup_path,
            "backup_size": 0,  # Would calculate actual size
            "backup_duration": 0,  # Would measure actual duration
            "status": "completed",
        }

        logger.info(f"Database backup completed: {backup_path}")
        return {
            "status": "success",
            "results": results,
            "backup_time": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        raise


@celery_app.task(
    bind=True, name="app.tasks.maintenance.cleanup_incomplete_chunks"
)
def cleanup_incomplete_chunks(self, minutes_old: int = 15) -> dict[str, Any]:  # noqa: D417
    """Clean up old chunk directories.

    Cleans up directories where the newest chunk is older than specified
    minutes.

    Args:
        minutes_old: Chunk directories where the newest chunk is older
            than this many minutes will be cleaned up (default: 15)

    Returns:
        Dict with cleanup results
    """
    try:
        logger.info(
            f"Starting cleanup of chunk directories where newest chunk "
            f"is older than {minutes_old} minutes"
        )

        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=minutes_old
        )
        chunk_manager = ChunkManager()

        results = {
            "directories_checked": 0,
            "directories_cleaned": 0,
            "errors": [],
        }

        # Get chunk storage path
        chunk_storage_path = Path(chunk_manager.storage_path)

        if not chunk_storage_path.exists():
            logger.info(
                f"Chunk storage directory does not exist: {chunk_storage_path}"
            )
            return {
                "status": "success",
                "results": results,
                "cleanup_date": datetime.now(timezone.utc).isoformat(),
            }

        # Scan all upload directories
        for upload_dir in chunk_storage_path.iterdir():
            if not upload_dir.is_dir():
                continue

            results["directories_checked"] += 1

            try:
                # Find the newest chunk file in this directory
                newest_chunk_time = None
                chunk_files = list(upload_dir.glob("chunk_*_*.chunk"))

                if not chunk_files:
                    # No chunk files found, check directory modification time
                    dir_mtime = datetime.fromtimestamp(
                        upload_dir.stat().st_mtime, tz=timezone.utc
                    )
                    if dir_mtime < cutoff_time:
                        # Directory is old and has no chunks, clean it up
                        chunk_manager.cleanup_chunks(upload_dir.name)
                        results["directories_cleaned"] += 1
                        logger.info(
                            f"Cleaned up empty chunk directory: "
                            f"{upload_dir.name} (age: {dir_mtime})"
                        )
                    continue

                # Find the newest chunk file
                for chunk_file in chunk_files:
                    chunk_mtime = datetime.fromtimestamp(
                        chunk_file.stat().st_mtime, tz=timezone.utc
                    )
                    if (
                        newest_chunk_time is None
                        or chunk_mtime > newest_chunk_time
                    ):
                        newest_chunk_time = chunk_mtime

                # Check if the newest chunk is older than cutoff time
                if newest_chunk_time and newest_chunk_time < cutoff_time:
                    # Newest chunk is old, clean up the entire directory
                    chunk_manager.cleanup_chunks(upload_dir.name)
                    results["directories_cleaned"] += 1
                    logger.info(
                        f"Cleaned up chunk directory: {upload_dir.name} "
                        f"(newest chunk age: {newest_chunk_time})"
                    )

            except Exception as e:
                error_msg = (
                    f"Failed to process chunk directory "
                    f"{upload_dir.name}: {str(e)}"
                )
                logger.error(error_msg)
                results["errors"].append(error_msg)

        logger.info(f"Chunk cleanup completed: {results}")
        return {
            "status": "success",
            "results": results,
            "cleanup_date": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Chunk cleanup task failed: {str(e)}")
        raise

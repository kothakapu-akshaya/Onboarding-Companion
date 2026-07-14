"""Logging configuration for the application."""

import logging
import os
import sys
from pathlib import Path


def setup_logging(level: str = "INFO"):
    """Setup application logging with console and file handlers."""
    log_level = getattr(logging, level.upper(), logging.WARNING)

    # Create logs directory if it doesn't exist
    # Use /tmp/logs for Docker containers to avoid permission issues
    log_dir = Path("/tmp/logs")

    # Debug logging for permissions
    logger = logging.getLogger(__name__)

    # Check /tmp permissions
    tmp_path = Path("/tmp")
    if tmp_path.exists():
        tmp_stat = tmp_path.stat()
        logger.debug(f"/tmp permissions: {oct(tmp_stat.st_mode)[-3:]}")
        logger.debug(f"/tmp owner: {tmp_stat.st_uid}, group: {tmp_stat.st_gid}")
        logger.debug(f"Current process uid: {os.getuid()}, gid: {os.getgid()}")

        # Check if we can write to /tmp
        try:
            test_file = tmp_path / f"test_write_{os.getpid()}"
            test_file.touch()
            test_file.unlink()
            logger.debug("✓ Can write to /tmp directory")
        except (PermissionError, OSError) as e:
            logger.error(f"✗ Cannot write to /tmp directory: {e}")
    else:
        logger.error("/tmp directory does not exist")

    # Check if log_dir already exists and its permissions
    if log_dir.exists():
        log_dir_stat = log_dir.stat()
        logger.debug(
            f"Existing {log_dir} permissions: {oct(log_dir_stat.st_mode)[-3:]}"
        )
        logger.debug(
            f"Existing {log_dir} owner: {log_dir_stat.st_uid}, "
            f"group: {log_dir_stat.st_gid}"
        )

        # Check if we can write to existing log_dir
        try:
            test_file = log_dir / f"test_write_{os.getpid()}"
            test_file.touch()
            test_file.unlink()
            logger.debug(f"✓ Can write to existing {log_dir} directory")
        except (PermissionError, OSError) as e:
            logger.error(f"✗ Cannot write to existing {log_dir} directory: {e}")
    else:
        logger.debug(f"{log_dir} does not exist, will attempt to create")

    # Attempt to create log_dir with detailed error handling
    try:
        log_dir.mkdir(exist_ok=True)
        logger.debug(f"✓ Successfully created/verified {log_dir} directory")

        # Check final permissions after creation
        if log_dir.exists():
            final_stat = log_dir.stat()
            logger.debug(
                f"Final {log_dir} permissions: {oct(final_stat.st_mode)[-3:]}"
            )
            logger.debug(
                f"Final {log_dir} owner: {final_stat.st_uid}, "
                f"group: {final_stat.st_gid}"
            )
    except PermissionError as e:
        logger.error(f"✗ Permission denied creating {log_dir}: {e}")
        logger.error(
            "Required permissions: read/write/execute (755 or 775) on /tmp"
        )
        logger.error("Current user needs write access to /tmp directory")
    except OSError as e:
        logger.error(f"✗ OS error creating {log_dir}: {e}")
    except Exception as e:
        logger.error(f"✗ Unexpected error creating {log_dir}: {e}")

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            # logging.FileHandler(log_dir / "app.log", mode="a"),
        ],
    )

    # Set specific loggers to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Suppress watchfiles INFO messages (common in development with reload=True)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

    # Also suppress other common development noise
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)

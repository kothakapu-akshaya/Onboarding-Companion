#!/usr/bin/env python3
"""CLI utilities for backfill operations.

Provides common command-line argument parsing and setup functionality.
"""

import argparse
import logging
import os
from typing import Any


def create_common_cli_parser(description: str) -> argparse.ArgumentParser:
    """Create a common CLI parser with standard backfill arguments.

    Args:
        description: Description for the specific backfill operation

    Returns:
        Configured ArgumentParser with common arguments
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making database changes",
    )

    parser.add_argument(
        "--limit", type=int, help="Maximum number of records to process"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of concurrent workers for processing (default: 3)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of records to process in each batch (default: 10)",
    )

    parser.add_argument(
        "--reset-progress",
        action="store_true",
        help="Reset progress tracking (start from beginning)",
    )

    return parser


def handle_common_cli_setup(args: Any, progress_file: str) -> None:
    """Handle common CLI setup tasks.

    Args:
        args: Parsed command line arguments
        progress_file: Name of the progress file to potentially reset
    """
    # Reset progress if requested
    if args.reset_progress:
        if os.path.exists(progress_file):
            os.remove(progress_file)
            logging.getLogger().info("Progress tracking reset")


def validate_worker_count(
    workers: int, max_recommended: int = 4, operation_name: str = "processing"
) -> None:
    """Validate and warn about worker count.

    Args:
        workers: Number of workers requested
        max_recommended: Maximum recommended workers for the operation
        operation_name: Name of the operation for warning messages
    """
    logger = logging.getLogger()

    if workers > max_recommended:
        logger.warning(
            f"Using more than {max_recommended} workers for "
            f"{operation_name} may cause high system resource usage"
        )
        logger.warning(
            "Consider using fewer workers if system becomes unresponsive"
        )

    if workers < 1:
        logger.error("Worker count must be at least 1")
        raise ValueError("Invalid worker count")


def validate_batch_size(batch_size: int, max_recommended: int = 50) -> None:
    """Validate batch size parameter.

    Args:
        batch_size: Batch size requested
        max_recommended: Maximum recommended batch size
    """
    logger = logging.getLogger()

    if batch_size > max_recommended:
        logger.warning(
            f"Batch size {batch_size} is larger than "
            f"recommended maximum of {max_recommended}"
        )
        logger.warning("Large batch sizes may cause memory issues")

    if batch_size < 1:
        logger.error("Batch size must be at least 1")
        raise ValueError("Invalid batch size")


def setup_logging(log_file: str, log_level: str = "INFO") -> None:
    """Set up logging configuration for backfill operations.

    Args:
        log_file: Name of the log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    import sys

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )


def add_media_type_argument(
    parser: argparse.ArgumentParser,
    choices: list[str] | None = None,
    default: str = "all",
) -> None:
    """Add media type argument to parser.

    Args:
        parser: ArgumentParser to add argument to
        choices: List of valid media type choices
        default: Default media type value
    """
    if choices is None:
        choices = ["text", "audio", "video", "image", "document", "all"]

    parser.add_argument(
        "--media-type",
        choices=choices,
        default=default,
        help=f"Filter by media type (default: {default})",
    )


def add_algorithm_argument(
    parser: argparse.ArgumentParser,
    choices: list[str] | None = None,
    default: str = "sha256",
) -> None:
    """Add algorithm argument to parser (for hashing operations).

    Args:
        parser: ArgumentParser to add argument to
        choices: List of valid algorithm choices
        default: Default algorithm value
    """
    if choices is None:
        choices = ["sha256", "sha1", "md5", "sha512"]

    parser.add_argument(
        "--algorithm",
        choices=choices,
        default=default,
        help=f"Algorithm to use (default: {default})",
    )


def handle_script_specific_validation(args: Any, script_type: str) -> None:
    """Handle script-specific validation and warnings.

    Args:
        args: Parsed command line arguments
        script_type: Type of script (duration, hashing, snr_frequency)
    """
    logger = logging.getLogger()

    if script_type == "snr_frequency":
        validate_worker_count(
            args.workers, max_recommended=4, operation_name="SNR calculation"
        )
        if args.batch_size > 5:
            logger.warning(
                "SNR calculation is CPU intensive - "
                "consider using smaller batch sizes"
            )

    elif script_type == "hashing":
        validate_worker_count(
            args.workers, max_recommended=5, operation_name="file hashing"
        )
        validate_batch_size(args.batch_size, max_recommended=20)

    elif script_type == "duration":
        validate_worker_count(
            args.workers,
            max_recommended=4,
            operation_name="duration calculation",
        )
        validate_batch_size(args.batch_size, max_recommended=15)

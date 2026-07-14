#!/usr/bin/env python3
"""Base class for backfill operations providing common functionality."""

import argparse
import json
import logging
import os
import sys
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generic, TypeVar
from urllib.parse import urlparse

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.record import Record
from app.utils.hetzner_storage import get_storage_client

# Type variables for generic typing
T = TypeVar("T")  # For the computed value type (int, str, float, etc.)
type BackfillStats = dict[str, int | float | list[str]]


class BaseBackfiller(ABC, Generic[T]):
    """Base class for all backfill operations providing common infrastructure.

    This class handles:
    - Progress tracking and resume capability
    - File downloading from object storage
    - Concurrent processing with thread safety
    - Database batch updates
    - Error handling and statistics
    - CLI argument parsing
    """

    def __init__(
        self,
        progress_file: str,
        dry_run: bool = False,
        max_workers: int = 3,
        batch_size: int = 10,
    ) -> None:
        """Initialize the base backfiller.

        Args:
            progress_file: Name of the JSON file to track progress
            dry_run: If True, don't make actual database changes
            max_workers: Number of concurrent workers for processing
            batch_size: Number of records to process in each batch
        """
        self.dry_run = dry_run
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.storage_client = get_storage_client()
        self.progress_file = progress_file
        self.processed_uids = self._load_progress()
        self.stats: BackfillStats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }
        self._stats_lock = threading.Lock()

        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)

    def _load_progress(self) -> set[str]:
        """Load previously processed record UIDs from progress file."""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file) as f:
                    data = json.load(f)
                    return set(data.get("processed_uids", []))
        except Exception as e:
            self.logger.warning(f"Could not load progress file: {e}")
        return set()

    def _save_progress(self, record_uid: str) -> None:
        """Save a processed record UID to progress file."""
        try:
            self.processed_uids.add(str(record_uid))
            progress_data = {
                "processed_uids": list(self.processed_uids),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not save progress: {e}")

    def _update_stats(
        self,
        stat_key: str,
        increment: int = 1,
        error_msg: str | None = None,
    ) -> None:
        """Thread-safe stats updating."""
        with self._stats_lock:
            current_value = self.stats.get(stat_key)
            if isinstance(current_value, int):
                self.stats[stat_key] = current_value + increment
            else:
                self.stats[stat_key] = increment
            if error_msg and stat_key == "failed":
                errors = self.stats.get("errors")
                if isinstance(errors, list):
                    errors.append(error_msg)

    def download_file_to_temp(self, record: Record) -> str | None:
        """Download a file from object storage to a temporary location.

        Args:
            record: Record containing file information

        Returns:
            Path to temporary file, or None if download failed
        """
        if not record.file_url:
            self.logger.warning(f"Record {record.uid} has no file_url")
            return None

        try:
            # Extract object key from file_url
            # using proper URL parsing
            parsed_url = urlparse(record.file_url)
            object_key = parsed_url.path.lstrip("/")

            if not object_key:
                self.logger.error(
                    f"Could not extract object key from {record.file_url}"
                )
                return None

            # Create temporary file
            file_extension = (
                Path(record.file_name or object_key).suffix
                if record.file_name
                else ""
            )
            if not file_extension:
                # Try to determine extension from object key
                file_extension = Path(object_key).suffix

            # Create temp file with proper extension
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=file_extension,
                prefix=(f"{self.__class__.__name__.lower()}_{record.uid}_"),
            )
            temp_path = temp_file.name
            temp_file.close()

            self.logger.info(f"Downloading {object_key} to {temp_path}")

            # Download file from object storage
            self.storage_client.client.fget_object(
                bucket_name=self.storage_client.bucket_name,
                object_name=object_key,
                file_path=temp_path,
            )

            # Verify file was downloaded and has content
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                self.logger.info(
                    f"Successfully downloaded {object_key} "
                    f"({os.path.getsize(temp_path)} bytes)"
                )
                return temp_path
            else:
                self.logger.error(
                    f"Downloaded file {temp_path} is empty or doesn't exist"
                )
                return None

        except Exception as e:
            self.logger.error(
                f"Failed to download file for record {record.uid}: {e}"
            )
            return None

    def cleanup_temp_file(self, file_path: str) -> None:
        """Clean up temporary file.

        Args:
            file_path: Path to temporary file to delete
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                self.logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            self.logger.warning(
                f"Failed to clean up temporary file {file_path}: {e}"
            )

    def process_record(self, record: Record) -> tuple[str, T] | None:
        """Process a single record: download, compute value.

        Args:
            record: Record to process

        Returns:
            Tuple of (record_uid, computed_value)
            if successful, None if failed
        """
        temp_file_path = None

        try:
            self.logger.info(
                f"Processing record {record.uid} "
                f"({record.media_type.value}): {record.title}"
            )

            # Download file to temporary location
            temp_file_path = self.download_file_to_temp(record)
            if not temp_file_path:
                self._update_stats(
                    "failed",
                    error_msg=(f"Record {record.uid}: Failed to download file"),
                )
                return None

            # Compute the value using specific implementation
            computed_value = self.compute_value(temp_file_path, record)
            if not self.is_valid_result(computed_value, record):
                self._update_stats(
                    "failed",
                    error_msg=(
                        f"Record {record.uid}: "
                        f"{self.get_computation_error_message(record)}"
                    ),
                )
                return None

            # Save progress
            self._save_progress(str(record.uid))

            return (str(record.uid), computed_value)

        except Exception as e:
            self.logger.error(
                f"Unexpected error processing record {record.uid}: {e}"
            )
            self._update_stats(
                "failed",
                error_msg=(f"Record {record.uid}: {str(e)}"),
            )
            return None

        finally:
            # Always clean up temporary file
            if temp_file_path:
                self.cleanup_temp_file(temp_file_path)

    def process_records_batch(
        self, records: list[Record]
    ) -> list[tuple[str, T]]:
        """Process a batch of records concurrently.

        Args:
            records: List of records to process

        Returns:
            List of (record_uid, computed_value) tuples
            for successful processing
        """
        successful_updates = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_record = {
                executor.submit(self.process_record, record): record
                for record in records
            }

            # Collect results as they complete
            for future in as_completed(future_to_record):
                record = future_to_record[future]
                self._update_stats("total_processed")

                try:
                    result = future.result()
                    if result:
                        successful_updates.append(result)
                        self._update_stats("successful")
                        self.logger.info(
                            f"✓ Successfully processed record {record.uid}"
                        )
                    else:
                        self.logger.error(
                            f"✗ Failed to process record {record.uid}"
                        )

                except Exception as e:
                    self.logger.error(
                        f"✗ Exception processing record {record.uid}: {e}"
                    )
                    self._update_stats(
                        "failed",
                        error_msg=(f"Record {record.uid}: {str(e)}"),
                    )

        return successful_updates

    def run_backfill(
        self,
        media_type: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Run the complete backfill process.

        Args:
            media_type: Filter by media type (implementation-specific)
            limit: Maximum number of records to process

        Returns:
            Statistics about the backfill process
        """
        self.logger.info(
            f"Starting {self.get_operation_name()} backfill process"
        )
        self.logger.info(f"Dry run: {self.dry_run}")
        self.logger.info(
            f"Media type filter: "
            f"{media_type or self.get_default_media_type_description()}"
        )
        self.logger.info(f"Limit: {limit or 'no limit'}")

        start_time = time.time()

        # Get records to process
        records = self.get_records_to_process(media_type, limit)

        if not records:
            self.logger.info(
                f"No records found that need "
                f"{self.get_operation_name()} backfill"
            )
            return self.stats

        self.logger.info(
            f"Processing {len(records)} records in batches of "
            f"{self.batch_size} with {self.max_workers} workers..."
        )

        # Process records in batches
        total_records = len(records)
        for i in range(0, total_records, self.batch_size):
            batch = records[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (
                total_records + self.batch_size - 1
            ) // self.batch_size
            progress_percent = (
                self._get_numeric_stat("total_processed") / total_records * 100
            )

            self.logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} records)"
            )
            self.logger.info(
                f"Overall progress: "
                f"{min(i + self.batch_size, total_records)}/"
                f"{total_records} "
                f"({progress_percent:.1f}%)"
            )

            # Process batch concurrently
            successful_updates = self.process_records_batch(batch)

            # Update database in batch if we have
            # successful results
            if successful_updates:
                updated_count = self.update_records_batch(successful_updates)
                self.logger.info(
                    f"Batch {batch_num}: {updated_count} "
                    f"records updated in database"
                )

            self.logger.info(
                f"Batch {batch_num} completed: "
                f"{len(successful_updates)}/{len(batch)} "
                f"records processed successfully"
            )

        # Calculate final statistics
        total_time = time.time() - start_time
        self.stats["total_time_seconds"] = total_time
        self.stats["average_time_per_record"] = (
            total_time / len(records) if records else 0
        )

        # Log final results
        self.logger.info("=" * 60)
        self.logger.info("BACKFILL COMPLETED")
        self.logger.info("=" * 60)
        self.logger.info(f"Total processed: {self.stats['total_processed']}")
        self.logger.info(f"Successful: {self.stats['successful']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Skipped: {self.stats['skipped']}")
        self.logger.info(f"Total time: {total_time:.2f} seconds")
        self.logger.info(
            f"Average time per record: "
            f"{self.stats['average_time_per_record']:.2f} seconds"
        )

        errors = self._get_errors()
        if errors:
            self.logger.info("Errors encountered:")
            for error in errors:
                self.logger.error(f"  - {error}")

        return self.stats

    def _get_numeric_stat(self, stat_key: str) -> int | float:
        """Get a numeric statistic, defaulting to zero."""
        value = self.stats.get(stat_key, 0)
        return value if isinstance(value, int | float) else 0

    def _get_errors(self) -> list[str]:
        """Get the current error list."""
        errors = self.stats.get("errors", [])
        return errors if isinstance(errors, list) else []

    # Abstract methods that subclasses must implement

    @abstractmethod
    def get_records_to_process(
        self,
        media_type: str | None = None,
        limit: int | None = None,
    ) -> list[Record]:
        """Get records that need processing.

        For this specific backfill operation.
        """
        pass

    @abstractmethod
    def compute_value(self, file_path: str, record: Record) -> T:
        """Compute the specific value for this backfill operation."""
        pass

    @abstractmethod
    def is_valid_result(self, computed_value: T, record: Record) -> bool:
        """Check if the computed value is valid for the given record."""
        pass

    @abstractmethod
    def update_records_batch(self, updates: list[tuple[str, T]]) -> int:
        """Update database records with computed values."""
        pass

    @abstractmethod
    def get_operation_name(self) -> str:
        """Get the name of this backfill operation for logging."""
        pass

    @abstractmethod
    def get_computation_error_message(self, record: Record) -> str:
        """Get error message for failed computation."""
        pass

    @abstractmethod
    def get_default_media_type_description(self) -> str:
        """Get description of default media types processed."""
        pass


def create_common_cli_parser(
    description: str,
) -> argparse.ArgumentParser:
    """Create a common CLI parser with standard backfill arguments.

    Args:
        description: Description for the specific backfill operation

    Returns:
        Configured ArgumentParser with common arguments
    """
    import argparse

    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=(argparse.RawDescriptionHelpFormatter),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=("Show what would be processed without making database changes"),
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of records to process",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help=("Number of concurrent workers for processing (default: 3)"),
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help=("Number of records to process in each batch (default: 10)"),
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
        progress_file: Name of the progress file
            to potentially reset
    """
    # Reset progress if requested
    if args.reset_progress:
        if os.path.exists(progress_file):
            os.remove(progress_file)
            logging.getLogger().info("Progress tracking reset")


def run_backfill_main(
    backfiller_class: type[Any],
    progress_file: str,
    additional_args_handler: Any = None,
) -> None:
    """Common main function for all backfill scripts.

    Args:
        backfiller_class: The specific backfiller class
            to instantiate
        progress_file: Name of the progress file
        additional_args_handler: Optional function to add
            script-specific CLI args
    """
    import sys

    # Get logger
    logger = logging.getLogger()

    try:
        # This would be called by each specific script
        # with their custom arguments
        # The implementation would be script-specific
        # but follow this pattern
        pass

    except KeyboardInterrupt:
        logger.info("Backfill interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Backfill failed with error: {e}")
        sys.exit(1)

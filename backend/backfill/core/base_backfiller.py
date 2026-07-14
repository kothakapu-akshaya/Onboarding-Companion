#!/usr/bin/env python3
"""Modularized base class for backfill operations.

Uses modular components for better separation of concerns and maintainability.
"""

import logging

# Add the app directory to the Python path
import os
import sys
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Generic, TypeVar

from .file_manager import FileManager
from .progress_tracker import ProgressTracker
from .statistics_manager import StatisticsManager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models.record import Record

# Type variables for generic typing
T = TypeVar("T")  # For the computed value type (int, str, float, etc.)


class BaseBackfiller(ABC, Generic[T]):
    """Modularized base class for all backfill operations.

    This class orchestrates modular components:
    - FileManager: Handles file download/cleanup operations
    - ProgressTracker: Manages progress saving/loading
    - StatisticsManager: Thread-safe statistics tracking

    Subclasses only need to implement the specific business logic.
    """

    def __init__(
        self,
        progress_file: str,
        dry_run: bool = False,
        max_workers: int = 3,
        batch_size: int = 10,
    ):
        """Initialize the modularized backfiller.

        Args:
            progress_file: Name of the JSON file
                to track progress
            dry_run: If True, don't make actual database changes
            max_workers: Number of concurrent workers for processing
            batch_size: Number of records to process in each batch
        """
        self.dry_run = dry_run
        self.max_workers = max_workers
        self.batch_size = batch_size

        # Initialize modular components
        self.file_manager = FileManager()
        self.progress_tracker = ProgressTracker(progress_file)
        self.stats_manager = StatisticsManager()

        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)

        # Backward compatibility properties
        self.processed_uids = self.progress_tracker.processed_uids
        self.progress_file = progress_file

    def process_record(self, record: Record) -> tuple[str, T] | None:
        """Process a single record using modular components.

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

            # Download file using file manager
            temp_file_path = self.file_manager.download_file_to_temp(
                record, self.__class__.__name__
            )
            if not temp_file_path:
                self.stats_manager.update_stat(
                    "failed",
                    error_msg=(f"Record {record.uid}: Failed to download file"),
                )
                return None

            # Compute the value using specific implementation
            computed_value = self.compute_value(temp_file_path, record)
            if not self.is_valid_result(computed_value, record):
                self.stats_manager.update_stat(
                    "failed",
                    error_msg=(
                        f"Record {record.uid}: "
                        f"{self.get_computation_error_message(record)}"
                    ),
                )
                return None

            # Save progress using progress tracker
            self.progress_tracker.save_progress(str(record.uid))

            return (str(record.uid), computed_value)

        except Exception as e:
            self.logger.error(
                f"Unexpected error processing record {record.uid}: {e}"
            )
            self.stats_manager.update_stat(
                "failed",
                error_msg=(f"Record {record.uid}: {str(e)}"),
            )
            return None

        finally:
            # Clean up temporary file using file manager
            if temp_file_path:
                self.file_manager.cleanup_temp_file(temp_file_path)

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
                self.stats_manager.update_stat("total_processed")

                try:
                    result = future.result()
                    if result:
                        successful_updates.append(result)
                        self.stats_manager.update_stat("successful")
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
                    self.stats_manager.update_stat(
                        "failed",
                        error_msg=(f"Record {record.uid}: {str(e)}"),
                    )

        return successful_updates

    def run_backfill(
        self,
        media_type: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Run the complete backfill process using modular components.

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

        time.time()

        # Get records to process
        records = self.get_records_to_process(media_type, limit)

        if not records:
            self.logger.info(
                f"No records found that need "
                f"{self.get_operation_name()} backfill"
            )
            return self.stats_manager.finalize_stats(0)

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

            self.logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} records)"
            )
            self.logger.info(
                f"Overall progress: "
                f"{min(i + self.batch_size, total_records)}/"
                f"{total_records} "
                f"({self.stats_manager.get_progress_percentage(total_records):.1f}%)"
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

        # Get final statistics from stats manager
        final_stats = self.stats_manager.finalize_stats(total_records)

        # Log final results
        self.logger.info("=" * 60)
        self.logger.info("BACKFILL COMPLETED")
        self.logger.info("=" * 60)
        self.logger.info(f"Total processed: {final_stats['total_processed']}")
        self.logger.info(f"Successful: {final_stats['successful']}")
        self.logger.info(f"Failed: {final_stats['failed']}")
        self.logger.info(f"Skipped: {final_stats['skipped']}")
        self.logger.info(
            f"Total time: {final_stats['total_time_seconds']:.2f} seconds"
        )
        self.logger.info(
            f"Average time per record: "
            f"{final_stats['average_time_per_record']:.2f} seconds"
        )
        self.logger.info(f"Success rate: {final_stats['success_rate']:.1f}%")

        if final_stats["errors"]:
            self.logger.info("Errors encountered:")
            for error in final_stats["errors"]:
                self.logger.error(f"  - {error}")

        return final_stats

    # Backward compatibility methods
    def _update_stats(
        self,
        stat_key: str,
        increment: int = 1,
        error_msg: str | None = None,
    ) -> None:
        """Backward compatibility wrapper for stats updates."""
        self.stats_manager.update_stat(stat_key, increment, error_msg)

    def _save_progress(self, record_uid: str) -> None:
        """Backward compatibility wrapper for progress saving."""
        self.progress_tracker.save_progress(record_uid)

    @property
    def stats(self) -> dict[str, Any]:
        """Backward compatibility property for accessing stats."""
        return self.stats_manager.get_stats()

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

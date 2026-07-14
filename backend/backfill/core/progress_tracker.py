#!/usr/bin/env python3
"""Progress tracking utilities for backfill operations.

Handles saving and loading progress state for resumable backfill operations.
"""

import json
import logging
import os
from datetime import datetime, timezone

type ProgressMetadata = dict[str, object]


class ProgressTracker:
    """Manages progress tracking for backfill operations.

    Responsibilities:
    - Load previously processed record UIDs from progress file
    - Save processed record UIDs to progress file
    - Handle progress file corruption and recovery
    """

    def __init__(self, progress_file: str):
        """Initialize the progress tracker.

        Args:
            progress_file: Name of the JSON file to track progress
        """
        self.progress_file = progress_file
        self.processed_uids: set[str] = set()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Load existing progress
        self._load_progress()

    def _load_progress(self) -> None:
        """Load previously processed record UIDs from progress file."""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file) as f:
                    data = json.load(f)
                    self.processed_uids = set(data.get("processed_uids", []))
                    self.logger.info(
                        f"Loaded {len(self.processed_uids)} processed "
                        f"UIDs from {self.progress_file}"
                    )
            else:
                self.logger.info(
                    f"No existing progress file found at {self.progress_file}"
                )
        except json.JSONDecodeError as e:
            self.logger.warning(
                f"Progress file {self.progress_file} is corrupted: {e}"
            )
            self.logger.warning(
                "Starting with empty progress - previous progress lost"
            )
            self.processed_uids = set()
        except Exception as e:
            self.logger.warning(f"Could not load progress file: {e}")
            self.processed_uids = set()

    def save_progress(
        self,
        record_uid: str,
        additional_metadata: ProgressMetadata | None = None,
    ) -> None:
        """Save a processed record UID to progress file.

        Args:
            record_uid: UID of the processed record
            additional_metadata: Optional additional data to save
        """
        try:
            self.processed_uids.add(str(record_uid))

            progress_data: ProgressMetadata = {
                "processed_uids": list(self.processed_uids),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_processed": len(self.processed_uids),
            }

            # Add any additional metadata
            if additional_metadata:
                progress_data.update(additional_metadata)

            with open(self.progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Could not save progress: {e}")

    def is_processed(self, record_uid: str) -> bool:
        """Check if a record has already been processed.

        Args:
            record_uid: UID to check

        Returns:
            True if already processed, False otherwise
        """
        return str(record_uid) in self.processed_uids

    def get_processed_count(self) -> int:
        """Get the number of processed records."""
        return len(self.processed_uids)

    def reset_progress(self) -> None:
        """Reset all progress tracking."""
        try:
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)
                self.logger.info(f"Progress file {self.progress_file} deleted")

            self.processed_uids.clear()
            self.logger.info("Progress tracking reset")

        except Exception as e:
            self.logger.error(f"Failed to reset progress: {e}")

    def get_progress_metadata(self) -> ProgressMetadata:
        """Get metadata from the progress file.

        Returns:
            Dictionary containing progress metadata
        """
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file) as f:
                    data = json.load(f)
                    # Remove the processed_uids list for cleaner metadata
                    metadata: ProgressMetadata = {
                        k: v for k, v in data.items() if k != "processed_uids"
                    }
                    return metadata
        except Exception as e:
            self.logger.warning(f"Could not load progress metadata: {e}")

        return {}

    def update_metadata(self, metadata: ProgressMetadata) -> None:
        """Update progress file with additional metadata.

        Args:
            metadata: Dictionary of metadata to add/update
        """
        try:
            progress_data: ProgressMetadata = {
                "processed_uids": list(self.processed_uids),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "total_processed": len(self.processed_uids),
            }
            progress_data.update(metadata)

            with open(self.progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Could not update progress metadata: {e}")

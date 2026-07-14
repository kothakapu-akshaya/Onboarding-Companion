#!/usr/bin/env python3
"""Backfill File Hash Script for Records - Refactored Version.

This script uses the BaseBackfiller class to provide common functionality
while implementing only the file-hashing-specific business logic.

Usage:
    python backfill/file_hashing_refactored.py
        [--dry-run] [--limit N]
        [--media-type TYPE] [--algorithm ALGO]
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.record import MediaType, Record
from app.utils.file_hashing import get_file_hash
from backfill.core.base_backfiller import BaseBackfiller
from backfill.core.cli_utils import (
    create_common_cli_parser,
    handle_common_cli_setup,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("backfill_file_hashing.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


class FileHashBackfiller(BaseBackfiller[str | None]):
    """Handles backfilling file hashes for uploaded records."""

    def __init__(
        self,
        dry_run: bool = False,
        max_workers: int = 3,
        batch_size: int = 10,
        algorithm: str = "sha256",
    ) -> None:
        """Initialize the FileHashBackfiller."""
        super().__init__(
            progress_file="backfill_file_hashing_progress.json",
            dry_run=dry_run,
            max_workers=max_workers,
            batch_size=batch_size,
        )
        self.algorithm = algorithm

        # Add algorithm to progress tracking
        self._update_progress_metadata()

    def _update_progress_metadata(self) -> None:
        """Update progress file with algorithm information."""
        try:
            progress_data = {
                "processed_uids": list(self.processed_uids),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "algorithm": self.algorithm,
            }
            with open(self.progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Could not update progress metadata: {e}")

    def get_records_to_process(
        self,
        media_type: str | None = None,
        limit: int | None = None,
    ) -> list[Record]:
        """Get records that don't have file_hash set."""
        with Session(engine) as session:
            query = select(Record).where(
                Record.file_hash is None,
                Record.file_url is not None,
                Record.status == "uploaded",
            )

            # Filter by media type if specified
            if media_type:
                if media_type.lower() == "text":
                    query = query.where(Record.media_type == MediaType.text)
                elif media_type.lower() == "audio":
                    query = query.where(Record.media_type == MediaType.audio)
                elif media_type.lower() == "video":
                    query = query.where(Record.media_type == MediaType.video)
                elif media_type.lower() == "image":
                    query = query.where(Record.media_type == MediaType.image)
                elif media_type.lower() == "document":
                    query = query.where(Record.media_type == MediaType.document)
                else:
                    raise ValueError(f"Invalid media type: {media_type}")

            # Apply limit if specified
            if limit:
                query = query.limit(limit)

            records = session.exec(query).all()

            # Filter out already processed records
            unprocessed_records = [
                r for r in records if str(r.uid) not in self.processed_uids
            ]

            self.logger.info(f"Found {len(records)} records without file hash")
            self.logger.info(
                f"Already processed: {len(records) - len(unprocessed_records)}"
            )
            self.logger.info(
                f"Remaining to process: {len(unprocessed_records)}"
            )

            return unprocessed_records

    def compute_value(self, file_path: str, record: Record) -> str | None:
        """Calculate hash for a file."""
        import time

        start_time = time.time()
        file_hash = get_file_hash(file_path, self.algorithm)
        calculation_time = time.time() - start_time

        if file_hash:
            self.logger.info(
                f"Calculated {self.algorithm} hash: "
                f"{file_hash[:16]}... "
                f"(took {calculation_time:.2f}s)"
            )
        else:
            self.logger.warning(
                f"Could not calculate hash (took {calculation_time:.2f}s)"
            )

        return file_hash

    def is_valid_result(
        self, computed_value: str | None, record: Record
    ) -> bool:
        """Check if the computed hash is valid."""
        return computed_value is not None and len(computed_value) > 0

    def update_records_batch(
        self, updates: list[tuple[str, str | None]]
    ) -> int:
        """Update multiple records with file hash.

        Done in a single transaction.
        """
        if not updates:
            return 0

        updated_count = 0
        try:
            with Session(engine) as session:
                for record_uid, file_hash in updates:
                    if file_hash is None:
                        self.logger.warning(
                            f"Skipping record {record_uid} with empty hash"
                        )
                        continue
                    db_record = session.get(Record, record_uid)
                    if db_record:
                        if self.dry_run:
                            self.logger.info(
                                f"[DRY RUN] Would update record "
                                f"{record_uid} with hash "
                                f"{file_hash[:16]}..."
                            )
                            updated_count += 1
                        else:
                            db_record.file_hash = file_hash
                            db_record.updated_at = datetime.now(timezone.utc)
                            session.add(db_record)
                            updated_count += 1
                    else:
                        self.logger.warning(
                            f"Record {record_uid} not found in database"
                        )

                if not self.dry_run:
                    session.commit()

                self.logger.info(
                    f"Batch update: {updated_count}/"
                    f"{len(updates)} records updated"
                )
                return updated_count

        except Exception as e:
            self.logger.error(f"Failed to batch update records: {e}")
            return 0

    def get_operation_name(self) -> str:
        """Get the name of this backfill operation."""
        return "file hash"

    def get_computation_error_message(self, record: Record) -> str:
        """Get error message for failed hash computation."""
        return f"Failed to calculate {self.algorithm} hash"

    def get_default_media_type_description(self) -> str:
        """Get description of default media types processed."""
        return "all media types"

    def run_backfill(
        self,
        media_type: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Override to add algorithm logging."""
        self.logger.info(f"Algorithm: {self.algorithm}")
        return super().run_backfill(media_type, limit)


def main() -> None:
    """Main entry point for the script."""
    parser = create_common_cli_parser(
        "Backfill file hashes for uploaded records"
    )

    parser.epilog = """
Examples:
  # Process all records without file hash
  python backfill/file_hashing_refactored.py
  
  # Dry run - show what would be processed
  # without making changes
  python backfill/file_hashing_refactored.py --dry-run
  
  # Process only audio files, limit to 10 records
  python backfill/file_hashing_refactored.py --media-type audio --limit 10
  
  # Process with 5 workers and batch size of 20,
  # using MD5 algorithm
  python backfill/file_hashing_refactored.py
      --workers 5 --batch-size 20 --algorithm md5
  
  # Reset progress and start fresh
  python backfill/file_hashing_refactored.py --reset-progress
        """

    # Add script-specific arguments
    parser.add_argument(
        "--media-type",
        choices=["text", "audio", "video", "image", "document", "all"],
        default="all",
        help="Filter by media type (default: all)",
    )

    parser.add_argument(
        "--algorithm",
        choices=["sha256", "sha1", "md5", "sha512"],
        default="sha256",
        help="Hashing algorithm to use (default: sha256)",
    )

    args = parser.parse_args()

    # Handle common setup
    handle_common_cli_setup(args, "backfill_file_hashing_progress.json")

    # Convert 'all' to None for internal processing
    media_type = None if args.media_type == "all" else args.media_type

    try:
        # Initialize backfiller
        backfiller = FileHashBackfiller(
            dry_run=args.dry_run,
            max_workers=args.workers,
            batch_size=args.batch_size,
            algorithm=args.algorithm,
        )

        # Run backfill
        stats = backfiller.run_backfill(media_type=media_type, limit=args.limit)

        # Exit with error code if there were failures
        if stats["failed"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        logging.getLogger().info("Backfill interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.getLogger().error(f"Backfill failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

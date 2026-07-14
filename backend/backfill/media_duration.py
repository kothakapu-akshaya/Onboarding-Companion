#!/usr/bin/env python3
"""Backfill Duration Script for Audio and Video Records.

Refactored Version.

This script uses the BaseBackfiller class to provide common functionality
while implementing only the duration-specific business logic.

Usage:
    python backfill/media_duration_refactored.py
        [--dry-run] [--limit N]
        [--media-type audio|video|both]
"""

import logging
import os
import sys
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlmodel import Session, select

from app.db.session import engine
from app.models.record import MediaType, Record
from app.utils.media_duration import get_media_duration_with_remux
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
        logging.FileHandler("backfill_duration.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


class DurationBackfiller(BaseBackfiller[int | None]):
    """Handles backfilling duration for audio and video records."""

    def __init__(
        self,
        dry_run: bool = False,
        max_workers: int = 3,
        batch_size: int = 10,
    ) -> None:
        """Initialize the DurationBackfiller."""
        super().__init__(
            progress_file="backfill_duration_progress.json",
            dry_run=dry_run,
            max_workers=max_workers,
            batch_size=batch_size,
        )

    def get_records_to_process(
        self,
        media_type: str | None = None,
        limit: int | None = None,
    ) -> list[Record]:
        """Get records that don't have duration_seconds set."""
        with Session(engine) as session:
            query = select(Record).where(
                Record.duration_seconds is None,
                Record.file_url is not None,
                Record.status == "uploaded",
            )

            # Filter by media type if specified
            if media_type:
                if media_type.lower() == "audio":
                    query = query.where(Record.media_type == MediaType.audio)
                elif media_type.lower() == "video":
                    query = query.where(Record.media_type == MediaType.video)
                else:
                    raise ValueError(f"Invalid media type: {media_type}")
            else:
                # Filter for audio and video only
                query = query.where(
                    (Record.media_type == MediaType.audio)
                    | (Record.media_type == MediaType.video)
                )

            # Apply limit if specified
            if limit:
                query = query.limit(limit)

            records = session.exec(query).all()

            # Filter out already processed records
            unprocessed_records = [
                r for r in records if str(r.uid) not in self.processed_uids
            ]

            self.logger.info(f"Found {len(records)} records without duration")
            self.logger.info(
                f"Already processed: {len(records) - len(unprocessed_records)}"
            )
            self.logger.info(
                f"Remaining to process: {len(unprocessed_records)}"
            )

            return unprocessed_records

    def compute_value(self, file_path: str, record: Record) -> int | None:
        """Compute duration for a media file."""
        import time

        start_time = time.time()
        duration = get_media_duration_with_remux(
            file_path, record.media_type.value
        )
        calculation_time = time.time() - start_time

        if duration is not None:
            self.logger.info(
                f"Calculated duration: {duration}s "
                f"(took {calculation_time:.2f}s)"
            )
        else:
            self.logger.warning(
                f"Could not calculate duration (took {calculation_time:.2f}s)"
            )

        return duration

    def is_valid_result(
        self, computed_value: int | None, record: Record
    ) -> bool:
        """Check if the computed duration is valid."""
        return computed_value is not None

    def update_records_batch(
        self, updates: list[tuple[str, int | None]]
    ) -> int:
        """Update multiple records with duration in a single transaction."""
        if not updates:
            return 0

        updated_count = 0
        try:
            with Session(engine) as session:
                for record_uid, duration in updates:
                    if duration is None:
                        self.logger.warning(
                            f"Skipping record {record_uid} with no duration"
                        )
                        continue
                    db_record = session.get(Record, record_uid)
                    if db_record:
                        if self.dry_run:
                            self.logger.info(
                                f"[DRY RUN] Would update record "
                                f"{record_uid} with duration "
                                f"{duration}s"
                            )
                            updated_count += 1
                        else:
                            db_record.duration_seconds = duration
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
        return "duration"

    def get_computation_error_message(self, record: Record) -> str:
        """Get error message for failed duration computation."""
        return "Failed to calculate duration"

    def get_default_media_type_description(self) -> str:
        """Get description of default media types processed."""
        return "both audio and video"


def main() -> None:
    """Main entry point for the script."""
    parser = create_common_cli_parser(
        "Backfill duration for audio and video records"
    )

    parser.epilog = """
Examples:
  # Process all audio and video records
  # without duration
  python backfill/media_duration_refactored.py
  
  # Dry run - show what would be processed
  # without making changes
  python backfill/media_duration_refactored.py --dry-run
  
  # Process only audio files, limit to 10 records
  python backfill/media_duration_refactored.py --media-type audio --limit 10
  
  # Process only video files with 5 workers
  # and batch size of 20
  python backfill/media_duration_refactored.py
      --media-type video --workers 5 --batch-size 20
  
  # Reset progress and start fresh
  python backfill/media_duration_refactored.py --reset-progress
        """

    # Add script-specific arguments
    parser.add_argument(
        "--media-type",
        choices=["audio", "video", "both"],
        default="both",
        help="Filter by media type (default: both)",
    )

    args = parser.parse_args()

    # Handle common setup
    handle_common_cli_setup(args, "backfill_duration_progress.json")

    # Convert 'both' to None for internal processing
    media_type = None if args.media_type == "both" else args.media_type

    try:
        # Initialize backfiller
        backfiller = DurationBackfiller(
            dry_run=args.dry_run,
            max_workers=args.workers,
            batch_size=args.batch_size,
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

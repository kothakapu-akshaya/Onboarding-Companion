#!/usr/bin/env python3
"""Backfill SNR Frequency Script for Audio and Video Records.

Refactored Version.

This script uses the BaseBackfiller class to provide common functionality
while implementing only the SNR-frequency-specific business logic.

Usage:
    python backfill/snr_frequency_refactored.py
        [--dry-run] [--limit N]
        [--media-type audio|video|both]
"""

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
from app.utils.snr_frequency import calculate_snr_frequency
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
        logging.FileHandler("backfill_snr_frequency.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


class SnrFrequencyBackfiller(BaseBackfiller[float | None]):
    """Handles backfilling SNR frequency for audio and video records."""

    def __init__(
        self,
        dry_run: bool = False,
        max_workers: int = 2,
        batch_size: int = 5,
    ) -> None:
        """Initialize the SnrFrequencyBackfiller."""
        super().__init__(
            progress_file="backfill_snr_frequency_progress.json",
            dry_run=dry_run,
            max_workers=max_workers,
            batch_size=batch_size,
        )

        # Add SNR-specific stats
        self.stats_manager.add_custom_stat("skipped_no_audio", 0)

    def get_records_to_process(
        self, media_type: str | None = None, limit: int | None = None
    ) -> list[Record]:
        """Get audio and video records that don't have snr_frequency set."""
        with Session(engine) as session:
            query = select(Record).where(
                Record.snr_frequency is None,
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
                # (SNR not applicable to text/image)
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

            self.logger.info(
                f"Found {len(records)} records without SNR frequency"
            )
            self.logger.info(
                f"Already processed: {len(records) - len(unprocessed_records)}"
            )
            self.logger.info(
                f"Remaining to process: {len(unprocessed_records)}"
            )

            return unprocessed_records

    def compute_value(self, file_path: str, record: Record) -> float | None:
        """Calculate SNR frequency for a media file."""
        import time

        start_time = time.time()
        snr_frequency = calculate_snr_frequency(
            file_path, record.media_type.value
        )
        calculation_time = time.time() - start_time

        if snr_frequency is not None:
            self.logger.info(
                f"Calculated SNR frequency: "
                f"{snr_frequency:.2f} dB "
                f"(took {calculation_time:.2f}s)"
            )
        else:
            if record.media_type == MediaType.video:
                self.logger.info(
                    f"Video file has no audio track - SNR "
                    f"calculation not applicable "
                    f"(took {calculation_time:.2f}s)"
                )
            else:
                self.logger.warning(
                    f"Could not calculate SNR frequency "
                    f"(took {calculation_time:.2f}s)"
                )

        return snr_frequency

    def is_valid_result(
        self, computed_value: float | None, record: Record
    ) -> bool:
        """Check if the computed SNR frequency is valid.

        For video files, None is acceptable (no audio track).
        For audio files, None means failure.
        """
        if record.media_type == MediaType.video:
            # For video files, None is acceptable (no audio track)
            return True
        else:
            # For audio files, we expect a valid SNR value
            return computed_value is not None

    def process_record(self, record: Record) -> tuple[str, float | None] | None:
        """Override to handle video files without audio specially."""
        result = super().process_record(record)

        # Handle special case for video files without audio
        if (
            result
            and result[1] is None
            and record.media_type == MediaType.video
        ):
            self._update_stats("skipped_no_audio")
            self.logger.info(
                f"Video file {record.uid} has no audio track - "
                f"marking as processed with NULL SNR"
            )

        return result

    def update_records_batch(
        self, updates: list[tuple[str, float | None]]
    ) -> int:
        """Update multiple records with SNR frequency.

        Done in a single transaction.
        """
        if not updates:
            return 0

        updated_count = 0
        try:
            with Session(engine) as session:
                for record_uid, snr_frequency in updates:
                    db_record = session.get(Record, record_uid)
                    if db_record:
                        if self.dry_run:
                            snr_display = (
                                f"{snr_frequency:.2f} dB"
                                if snr_frequency is not None
                                else "NULL (no audio)"
                            )
                            self.logger.info(
                                f"[DRY RUN] Would update record "
                                f"{record_uid} with SNR "
                                f"{snr_display}"
                            )
                            updated_count += 1
                        else:
                            db_record.snr_frequency = snr_frequency
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
        return "SNR frequency"

    def get_computation_error_message(self, record: Record) -> str:
        """Get error message for failed SNR computation."""
        if record.media_type == MediaType.audio:
            return "Failed to calculate SNR for audio file"
        else:
            return "Failed to process video file"

    def get_default_media_type_description(self) -> str:
        """Get description of default media types processed."""
        return "both audio and video"

    def run_backfill(
        self,
        media_type: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Override to add SNR-specific logging and warnings."""
        self.logger.info(
            "Note: Video files without audio tracks will be "
            "marked as processed with NULL SNR"
        )
        self.logger.warning(
            "SNR calculation is CPU intensive - "
            "using smaller batches for stability"
        )

        # Run the base backfill
        stats = super().run_backfill(media_type, limit)

        # Log SNR-specific statistics
        skipped_no_audio = self.stats_manager.get_stat("skipped_no_audio")
        if skipped_no_audio:
            self.logger.info(f"Video files without audio: {skipped_no_audio}")

        return stats


def main() -> None:
    """Main entry point for the script."""
    parser = create_common_cli_parser(
        "Backfill SNR frequency for audio and video records"
    )

    # Override default workers and batch size for SNR processing
    parser.set_defaults(workers=2, batch_size=5)

    parser.epilog = """
Examples:
  # Process all audio and video records without SNR frequency
  python backfill/snr_frequency_refactored.py
  
  # Dry run - show what would be processed without making changes
  python backfill/snr_frequency_refactored.py --dry-run
  
  # Process only audio files, limit to 10 records
  python backfill/snr_frequency_refactored.py --media-type audio --limit 10
  
  # Process only video files with 1 worker (CPU intensive)
  python backfill/snr_frequency_refactored.py --media-type video --workers 1
  
  # Reset progress and start fresh
  python backfill/snr_frequency_refactored.py --reset-progress
  
Note: SNR calculation is CPU intensive and may take longer
than other backfill operations.
Video files without audio tracks will be processed
successfully with NULL SNR values.
        """

    # Add script-specific arguments
    parser.add_argument(
        "--media-type",
        choices=["audio", "video", "both"],
        default="both",
        help="Filter by media type (default: both)",
    )

    args = parser.parse_args()

    # Validate worker count for SNR processing
    if args.workers > 4:
        logging.getLogger().warning(
            "Using more than 4 workers for SNR calculation "
            "may cause high CPU usage"
        )
        logging.getLogger().warning(
            "Consider using fewer workers if system becomes unresponsive"
        )

    # Handle common setup
    handle_common_cli_setup(args, "backfill_snr_frequency_progress.json")

    # Convert 'both' to None for internal processing
    media_type = None if args.media_type == "both" else args.media_type

    try:
        # Initialize backfiller
        backfiller = SnrFrequencyBackfiller(
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

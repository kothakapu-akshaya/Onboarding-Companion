#!/usr/bin/env python3
"""Backfill Text Metrics for Records.

Computes word_count, sentence_count, and character_count for records
that have extracted_text by parsing segment texts.

Usage:
    python backfill/word_count.py [--dry-run] [--limit N]
"""

import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, exists, select

from app.db.session import engine
from app.models.extracted_text import ExtractedText
from app.models.record import Record
from backfill.core.base_backfiller import BaseBackfiller
from backfill.core.cli_utils import (
    create_common_cli_parser,
    handle_common_cli_setup,
)
from backfill.core.progress_tracker import ProgressTracker
from backfill.core.statistics_manager import StatisticsManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("backfill_word_count.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


SQL_TEXT_METRICS = text(r"""
    SELECT
        COALESCE(sum(word_ct), 0) AS word_count,
        COALESCE(sum(char_ct), 0) AS character_count,
        COALESCE(sum(sentence_ct), 0) AS sentence_count
    FROM extractedtext et
    CROSS JOIN LATERAL jsonb_array_elements(et.segments) AS seg
    CROSS JOIN LATERAL (
        SELECT
            (
                SELECT count(*)
                FROM regexp_split_to_table(seg->>'text', '\s+') AS w
                WHERE w != ''
            ) AS word_ct,
            char_length(seg->>'text') AS char_ct,
            (
                SELECT count(*)
                FROM regexp_split_to_table(seg->>'text', '[.!?]+\s*') AS s
                WHERE s != ''
            ) AS sentence_ct
    ) AS calc
    WHERE et.record_id = :uid
      AND et.segments IS NOT NULL
      AND jsonb_typeof(et.segments) = 'array'
""")


def compute_text_metrics(record_uid: str) -> tuple[int, int, int]:
    """Compute word, sentence, and character counts from the database."""
    with Session(engine) as session:
        row = session.execute(SQL_TEXT_METRICS, {"uid": record_uid}).fetchone()
        if row:
            return (row[0] or 0, row[1] or 0, row[2] or 0)
        return (0, 0, 0)


class WordCountBackfiller(BaseBackfiller[tuple[int, int, int]]):
    """Backfills text metrics for records with extracted_text."""

    def __init__(
        self,
        dry_run: bool = False,
        max_workers: int = 3,
        batch_size: int = 10,
    ) -> None:
        """Initialize the WordCountBackfiller."""
        self.dry_run = dry_run
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.progress_tracker = ProgressTracker(
            "backfill_word_count_progress.json"
        )
        self.stats_manager = StatisticsManager()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.processed_uids = self.progress_tracker.processed_uids
        self.progress_file = "backfill_word_count_progress.json"

    def process_record(
        self, record: Record
    ) -> tuple[str, tuple[int, int, int]] | None:
        """Process a single record."""
        try:
            self.logger.info(f"Processing record {record.uid}")
            computed_value = self.compute_value("", record)
            if not self.is_valid_result(computed_value, record):
                self.stats_manager.update_stat(
                    "failed",
                    error_msg=(
                        f"Record {record.uid}: "
                        f"{self.get_computation_error_message(record)}"
                    ),
                )
                return None
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

    def get_records_to_process(
        self,
        media_type: str | None = None,
        limit: int | None = None,
    ) -> list[Record]:
        """Get records that have extracted_text with no character_count set.

        Note: media_type is unused since text metrics are computed for
        all records with extracted_text regardless of media type.
        """
        with Session(engine) as session:
            query = select(Record).where(
                exists().where(
                    col(ExtractedText.record_id) == col(Record.uid),
                    col(ExtractedText.character_count).is_(None),
                ),
            )
            if limit:
                query = query.limit(limit)
            records = session.exec(query).all()

            unprocessed = [
                r for r in records if str(r.uid) not in self.processed_uids
            ]
            self.logger.info(
                f"Found {len(records)} records with extracted_text "
                f"but no text metrics"
            )
            self.logger.info(
                f"Already processed: {len(records) - len(unprocessed)}"
            )
            self.logger.info(f"Remaining to process: {len(unprocessed)}")
            return unprocessed

    def compute_value(
        self, file_path: str, record: Record
    ) -> tuple[int, int, int]:
        """Compute text metrics for a record."""
        import time

        start = time.time()
        metrics = compute_text_metrics(str(record.uid))
        self.logger.info(
            f"Calculated metrics: word_count={metrics[0]}, "
            f"character_count={metrics[1]}, sentence_count={metrics[2]} "
            f"(took {time.time() - start:.2f}s)"
        )
        return metrics

    def is_valid_result(
        self, computed_value: tuple[int, int, int], record: Record
    ) -> bool:
        """Check if the computed metrics are valid."""
        wc, cc, sc = computed_value
        return wc >= 0 and cc >= 0 and sc >= 0

    def update_records_batch(
        self, updates: list[tuple[str, tuple[int, int, int]]]
    ) -> int:
        """Update extracted_text entries with text metrics."""
        if not updates:
            return 0

        if self.dry_run:
            for record_uid, (wc, cc, sc) in updates:
                self.logger.info(
                    f"[DRY RUN] Would update extracted_text for "
                    f"record {record_uid} with word_count={wc}, "
                    f"character_count={cc}, sentence_count={sc}"
                )
            return len(updates)

        now = datetime.now(timezone.utc)
        try:
            with Session(engine) as session:
                for record_uid, (wc, cc, sc) in updates:
                    session.execute(
                        sa_update(ExtractedText)
                        .where(col(ExtractedText.record_id) == record_uid)
                        .values(
                            word_count=wc,
                            character_count=cc,
                            sentence_count=sc,
                            updated_at=now,
                        )
                    )
                session.commit()
                self.logger.info(f"Batch update: {len(updates)} entries")
                return len(updates)
        except Exception as e:
            self.logger.error(
                f"Failed to batch update extracted_text entries: {e}"
            )
            return 0

    def get_operation_name(self) -> str:
        """Get the name of this backfill operation."""
        return "word_count"

    def get_computation_error_message(self, record: Record) -> str:
        """Get error message for failed text metrics computation."""
        return "Failed to determine text metrics"

    def get_default_media_type_description(self) -> str:
        """Get description of default media types processed."""
        return "all records with extracted_text"


def main() -> None:
    """Main entry point for the script."""
    parser = create_common_cli_parser(
        "Backfill text metrics for records with extracted_text"
    )
    args = parser.parse_args()
    handle_common_cli_setup(args, "backfill_word_count_progress.json")

    try:
        backfiller = WordCountBackfiller(
            dry_run=args.dry_run,
            max_workers=args.workers,
            batch_size=args.batch_size,
        )
        stats = backfiller.run_backfill(limit=args.limit)
        sys.exit(1 if stats["failed"] > 0 else 0)
    except KeyboardInterrupt:
        logging.getLogger().info("Backfill interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()

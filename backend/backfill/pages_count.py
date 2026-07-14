#!/usr/bin/env python3
"""Backfill Page Count Script for Document Records.

Mirrors ``backfill/media_duration_refactored.py``: uses the BaseBackfiller
class for the common download / concurrency / progress machinery and
implements only the page-count-specific business logic.

Usage:
    python backfill/pages_count.py
        [--dry-run] [--limit N]
        [--format pdf|docx|all]
"""

import logging
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlmodel import Session, col, select

from app.db.session import engine
from app.models.record import MediaType, Record
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
        logging.FileHandler("backfill_page_count.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

_SUPPORTED_FORMATS = {"pdf", "docx"}

# extended-properties namespace used by docProps/app.xml
_EP_NS = {
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
}


def get_document_page_count(
    file_path: str, media_type: str | None = None
) -> int | None:
    """Return the number of pages in a document, or None if undeterminable.

    PDF  : exact count via pypdf.
    DOCX : best-effort count from the cached <Pages> value in
           docProps/app.xml (present only if last saved by a paginating
           client; programmatically generated docx usually omit it).

    Never raises, so one bad file can't abort a backfill batch.
    """
    suffix = Path(file_path).suffix.lower()
    try:
        if suffix == ".pdf":
            return _count_pdf_pages(file_path)
        if suffix == ".docx":
            return _count_docx_pages(file_path)
        logging.getLogger(__name__).warning(
            "Unsupported document type for page counting: %s",
            suffix or "<no extension>",
        )
        return None
    except Exception as exc:  # noqa: BLE001 - must never raise
        logging.getLogger(__name__).error(
            "Failed to count pages for %s: %s", file_path, exc
        )
        return None


def _count_pdf_pages(file_path: str) -> int | None:
    """Exact page count for a PDF using pypdf."""
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(file_path)
        count = len(reader.pages)
        return count if count > 0 else None
    except PdfReadError as exc:
        logging.getLogger(__name__).warning(
            "Corrupt/unreadable PDF %s: %s", file_path, exc
        )
        return None


def _count_docx_pages(file_path: str) -> int | None:
    """Best-effort DOCX page count from the cached docProps/app.xml value."""
    try:
        with (
            zipfile.ZipFile(file_path) as zf,
            zf.open("docProps/app.xml") as fh,
        ):
            tree = ElementTree.parse(fh)
    except (KeyError, zipfile.BadZipFile, OSError) as exc:
        logging.getLogger(__name__).warning(
            "No usable app.xml in DOCX %s: %s", file_path, exc
        )
        return None

    pages_el = tree.find("ep:Pages", _EP_NS)
    if pages_el is None or not (pages_el.text or "").strip():
        logging.getLogger(__name__).info(
            "DOCX has no cached page count (likely generated): %s", file_path
        )
        return None
    pages_text = (pages_el.text or "").strip()
    try:
        pages = int(pages_text)
        return pages if pages > 0 else None
    except ValueError:
        return None


class PageCountBackfiller(BaseBackfiller[int | None]):
    """Handles backfilling page_count for document records."""

    def __init__(
        self,
        dry_run: bool = False,
        max_workers: int = 3,
        batch_size: int = 10,
    ) -> None:
        """Initialize the PageCountBackfiller."""
        super().__init__(
            progress_file="backfill_page_count_progress.json",
            dry_run=dry_run,
            max_workers=max_workers,
            batch_size=batch_size,
        )

    def run_backfill(
        self,
        doc_format: str | None = None,
        limit: int | None = None,
        **kwargs,
    ):
        """Run backfill, forwarding doc_format to get_records_to_process."""
        return super().run_backfill(media_type=doc_format, limit=limit)

    def get_records_to_process(
        self,
        doc_format: str | None = None,
        limit: int | None = None,
    ) -> list[Record]:
        """Get document records that don't have page_count set."""
        with Session(engine) as session:
            # NOTE: use col(...).is_(None) / .is_not(None) so SQLAlchemy emits
            # `IS NULL` / `IS NOT NULL`. Plain `Record.page_count is None`
            # evaluates in Python to a bool and silently breaks the filter.
            query = select(Record).where(
                col(Record.page_count).is_(None),
                col(Record.file_url).is_not(None),
                Record.status == "uploaded",
                Record.media_type == MediaType.document,
            )

            # Optionally restrict to a single document format by file_url suffix
            if doc_format and doc_format.lower() != "all":
                fmt = doc_format.lower()
                if fmt not in _SUPPORTED_FORMATS:
                    raise ValueError(f"Invalid document format: {doc_format}")
                query = query.where(col(Record.file_url).ilike(f"%.{fmt}"))

            # Apply limit if specified
            if limit:
                query = query.limit(limit)

            records = session.exec(query).all()

            # Filter out already processed records
            unprocessed_records = [
                r for r in records if str(r.uid) not in self.processed_uids
            ]

            self.logger.info(
                f"Found {len(records)} document records without page_count"
            )
            self.logger.info(
                f"Already processed: {len(records) - len(unprocessed_records)}"
            )
            self.logger.info(
                f"Remaining to process: {len(unprocessed_records)}"
            )

            return unprocessed_records

    def compute_value(self, file_path: str, record: Record) -> int | None:
        """Compute page count for a document file."""
        import time

        start_time = time.time()
        pages = get_document_page_count(file_path, record.media_type.value)
        calculation_time = time.time() - start_time

        if pages is not None:
            self.logger.info(
                f"Calculated page count: {pages} pages "
                f"(took {calculation_time:.2f}s)"
            )
        else:
            self.logger.warning(
                f"Could not determine page count (took {calculation_time:.2f}s)"
            )

        return pages

    def is_valid_result(
        self, computed_value: int | None, record: Record
    ) -> bool:
        """Check if the computed page count is valid."""
        return computed_value is not None and computed_value > 0

    def update_records_batch(
        self, updates: list[tuple[str, int | None]]
    ) -> int:
        """Update multiple records with page_count in a single transaction."""
        if not updates:
            return 0

        updated_count = 0
        try:
            with Session(engine) as session:
                for record_uid, pages in updates:
                    if pages is None:
                        self.logger.warning(
                            f"Skipping record {record_uid} with no page count"
                        )
                        continue
                    db_record = session.get(Record, record_uid)
                    if db_record:
                        if self.dry_run:
                            self.logger.info(
                                f"[DRY RUN] Would update record "
                                f"{record_uid} with page_count "
                                f"{pages}"
                            )
                            updated_count += 1
                        else:
                            db_record.page_count = pages
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
        return "page_count"

    def get_computation_error_message(self, record: Record) -> str:
        """Get error message for failed page count computation."""
        return "Failed to determine page count"

    def get_default_media_type_description(self) -> str:
        """Get description of default media types processed."""
        return "document records (pdf, docx)"


def main() -> None:
    """Main entry point for the script."""
    parser = create_common_cli_parser(
        "Backfill page_count for document records"
    )

    parser.epilog = """
Examples:
  # Process all document records without a page count
  python backfill/document_pages.py

  # Dry run - show what would be processed without making changes
  python backfill/document_pages.py --dry-run

  # Process only PDFs, limit to 10 records
  python backfill/document_pages.py --format pdf --limit 10

  # Process all documents with 5 workers and batch size of 20
  python backfill/document_pages.py --workers 5 --batch-size 20

  # Reset progress and start fresh
  python backfill/document_pages.py --reset-progress
        """

    # Add script-specific arguments
    parser.add_argument(
        "--format",
        choices=["pdf", "docx", "all"],
        default="all",
        help="Filter by document format (default: all)",
    )

    args = parser.parse_args()

    # Handle common setup
    handle_common_cli_setup(args, "backfill_page_count_progress.json")

    # Convert 'all' to None for internal processing
    doc_format = None if args.format == "all" else args.format

    try:
        # Initialize backfiller
        backfiller = PageCountBackfiller(
            dry_run=args.dry_run,
            max_workers=args.workers,
            batch_size=args.batch_size,
        )

        # Run backfill
        stats = backfiller.run_backfill(doc_format=doc_format, limit=args.limit)

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

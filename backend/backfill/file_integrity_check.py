#!/usr/bin/env python3
"""Check stored files for corruption across all media types.

For each media type, a corrupt file means something different:

  - audio/video: ffmpeg reports AVERROR_INVALIDDATA while decoding, or (for
    video) the file has no audio stream at all. These records have
    snr_frequency nulled out so the extraction-queue filter
    (snr_frequency IS NOT NULL) excludes them - the same fix applied in
    app/utils/snr_frequency.py for new uploads.

  - image: ffmpeg cannot decode the image (corrupt JPEG/PNG/etc).

  - document: pdfinfo cannot read the PDF (corrupt/truncated PDF).

  - text: file is empty or cannot be decoded as UTF-8.

There is currently no queue/serving filter keyed on image, document, or text
validity, so for those media types this script only *reports* findings (JSON
report file) for manual triage - it does not modify the database. Only
audio/video records get an automatic remediation (snr_frequency = NULL),
matching the existing extraction-queue guard.

Usage:
    # Preview what would change (no DB writes), check everything
    python backfill/file_integrity_check.py --dry-run

    # Process all records
    python backfill/file_integrity_check.py

    # Limit to N records (useful for testing)
    python backfill/file_integrity_check.py --limit 50

    # Only check specific media types
    python backfill/file_integrity_check.py --media-type audio video
    python backfill/file_integrity_check.py --media-type image document text
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlmodel import Session, col, select

from app.db.session import engine
from app.models.record import MediaType, Record
from app.utils.snr_frequency import _has_decode_errors
from backfill.core.file_manager import FileManager

PROGRESS_FILE = "backfill_file_integrity_progress.json"
REPORT_FILE = "file_integrity_report.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("backfill_file_integrity.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

ALL_MEDIA_TYPES = ["audio", "video", "image", "document", "text"]


# ---------------------------------------------------------------------------
# Per-media-type checks
# ---------------------------------------------------------------------------


def has_decode_errors(file_path: str) -> bool:
    """Run a full ffmpeg decode pass and check stderr for invalid data."""
    cmd = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return _has_decode_errors(result.stderr)


def has_audio_stream(file_path: str) -> bool:
    """Return True if ffprobe finds at least one audio stream."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "csv=p=0",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return bool(result.stdout.strip())


def check_audio_video(file_path: str, media_type: MediaType) -> str | None:
    """Return a failure reason string, or None if the file is OK."""
    if media_type == MediaType.video and not has_audio_stream(file_path):
        return "no_audio_stream"
    if has_decode_errors(file_path):
        return "corrupt_packets"
    return None


def check_image(file_path: str) -> str | None:
    """Return a failure reason string, or None if the image decodes OK."""
    cmd = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or result.stderr.strip():
        return "undecodable_image"
    return None


def check_document(file_path: str) -> str | None:
    """Return a failure reason string, or None if the PDF reads OK."""
    if Path(file_path).suffix.lower() != ".pdf":
        # Unknown document type - just confirm the file is non-empty.
        if Path(file_path).stat().st_size == 0:
            return "empty_file"
        return None

    result = subprocess.run(
        ["pdfinfo", file_path], capture_output=True, text=True
    )
    if result.returncode != 0:
        return "unreadable_pdf"
    return None


def check_text(file_path: str) -> str | None:
    """Return a failure reason string, or None if the text file is OK."""
    path = Path(file_path)
    if path.stat().st_size == 0:
        return "empty_file"
    try:
        path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "invalid_utf8"
    return None


# ---------------------------------------------------------------------------
# Progress / report tracking
# ---------------------------------------------------------------------------


def load_progress() -> set[str]:
    """Load the set of already-processed record UIDs."""
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE) as f:
            return set(json.load(f).get("processed", []))
    return set()


def save_progress(processed: set[str]) -> None:
    """Persist the set of processed record UIDs."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(
            {
                "processed": list(processed),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            f,
        )


def load_report() -> list[dict]:
    """Load previously recorded integrity findings."""
    if Path(REPORT_FILE).exists():
        with open(REPORT_FILE) as f:
            return json.load(f).get("findings", [])
    return []


def save_report(findings: list[dict]) -> None:
    """Persist integrity findings to the report file."""
    with open(REPORT_FILE, "w") as f:
        json.dump(
            {
                "findings": findings,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            f,
            indent=2,
        )


# ---------------------------------------------------------------------------
# DB queries / mutations
# ---------------------------------------------------------------------------


def get_records(
    media_types: list[str],
    limit: int | None,
    processed: set[str],
) -> list[Record]:
    """Fetch unprocessed records of the given media types to check."""
    with Session(engine) as session:
        query = select(Record).where(
            col(Record.file_url).is_not(None),
            Record.status == "uploaded",
            col(Record.media_type).in_(media_types),
        )

        # For audio/video, only re-check records that currently pass the
        # extraction-queue guard (snr_frequency set) - records that already
        # have snr_frequency = NULL are already excluded.
        av_types = {"audio", "video"} & set(media_types)
        other_types = set(media_types) - av_types

        records: list[Record] = []
        if av_types:
            av_query = query.where(
                col(Record.media_type).in_(list(av_types)),
                col(Record.snr_frequency).is_not(None),
            )
            records.extend(session.exec(av_query).all())
        if other_types:
            other_query = select(Record).where(
                col(Record.file_url).is_not(None),
                Record.status == "uploaded",
                col(Record.media_type).in_(list(other_types)),
            )
            records.extend(session.exec(other_query).all())

        remaining = [r for r in records if str(r.uid) not in processed]
        return remaining[:limit] if limit else remaining


def nullify_snr(record_uid: str, dry_run: bool) -> None:
    """Set snr_frequency to NULL and flag record as invalid audio."""
    if dry_run:
        logger.info(
            f"[DRY RUN] Would set snr_frequency = NULL and "
            f"speech_not_detected = True for {record_uid}"
        )
        return
    with Session(engine) as session:
        record = session.get(Record, record_uid)
        if record:
            record.snr_frequency = None
            record.speech_not_detected = True
            record.updated_at = datetime.now(timezone.utc)
            session.add(record)
            session.commit()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(dry_run: bool, limit: int | None, media_types: list[str]) -> None:
    """Check records for the given media types and report/fix findings."""
    processed = load_progress()
    findings = load_report()
    logger.info(f"Already processed: {len(processed)} records")

    file_manager = FileManager()
    records = get_records(media_types, limit, processed)
    logger.info(f"Records to check: {len(records)}")

    stats: dict[str, int] = {"checked": 0, "bad": 0, "ok": 0, "error": 0}

    for record in records:
        uid = str(record.uid)
        media_type = record.media_type
        temp_path = None
        try:
            temp_path = file_manager.download_file_to_temp(
                record, "FileIntegrity"
            )
            if temp_path is None:
                logger.warning(f"{uid}: download failed - skipping")
                stats["error"] += 1
                processed.add(uid)
                continue

            stats["checked"] += 1

            if media_type in (MediaType.audio, MediaType.video):
                reason = check_audio_video(temp_path, media_type)
                if reason:
                    logger.warning(
                        f"{uid} ({media_type.value}): {reason} - "
                        "nullifying snr_frequency"
                    )
                    nullify_snr(uid, dry_run)
            elif media_type == MediaType.image:
                reason = check_image(temp_path)
            elif media_type == MediaType.document:
                reason = check_document(temp_path)
            elif media_type == MediaType.text:
                reason = check_text(temp_path)
            else:
                reason = None

            if reason:
                stats["bad"] += 1
                findings.append(
                    {
                        "uid": uid,
                        "media_type": media_type.value,
                        "reason": reason,
                        "file_url": record.file_url,
                        "checked_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                save_report(findings)
                logger.warning(f"{uid} ({media_type.value}): {reason}")
            else:
                stats["ok"] += 1
                logger.info(f"{uid} ({media_type.value}): OK")

            processed.add(uid)
            save_progress(processed)

        except Exception as e:
            logger.error(f"{uid}: unexpected error - {e}")
            stats["error"] += 1
        finally:
            if temp_path and Path(temp_path).exists():
                Path(temp_path).unlink(missing_ok=True)

    logger.info(
        f"\nDone - checked: {stats['checked']}, "
        f"bad: {stats['bad']}, "
        f"ok: {stats['ok']}, "
        f"errors: {stats['error']}"
    )
    if any(f["media_type"] in ("image", "document", "text") for f in findings):
        logger.info(
            f"Non-audio/video findings written to {REPORT_FILE} for "
            "manual review (no automatic remediation exists for these "
            "media types)."
        )


def main() -> None:
    """Parse CLI arguments and run the integrity check."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview audio/video DB changes without writing (reporting "
        "for other media types is unaffected)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max records to process"
    )
    parser.add_argument(
        "--media-type",
        nargs="+",
        choices=ALL_MEDIA_TYPES,
        default=ALL_MEDIA_TYPES,
        help="Media types to check (default: all)",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run, limit=args.limit, media_types=args.media_type)


if __name__ == "__main__":
    main()

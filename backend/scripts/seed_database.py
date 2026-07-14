#!/usr/bin/env python3
# ruff: noqa: E402
"""Seed a small deterministic local dataset for development.

This script creates:
- 1 fake admin user
- 1 fake regular user
- 4 sample records
- points events for those records
- record history/version data for one record

It is designed to be idempotent and safe to re-run.

Local usage:
    uv run python -m scripts.seed_database
    uv run python -m scripts.seed_database --clear
    uv run python -m scripts.seed_database --clear --no-seed

Docker usage:
    docker compose exec app uv run python -m scripts.seed_database
    docker compose exec app uv run python -m scripts.seed_database --clear
"""

from __future__ import annotations

import argparse
import enum
import sys
import uuid
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, cast

from geoalchemy2.elements import WKTElement
from sqlalchemy import delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql.dml import Delete
from sqlmodel import Session, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.auth import get_password_hash
from app.core.language_utils import LANGUAGE_NOT_AVAILABLE
from app.db.session import engine
from app.models import (
    Category,
    ExtractedText,
    LanguageEntry,
    PointsEvent,
    Record,
    RecordHistory,
    RecordRestore,
    RecordVersion,
    Role,
    RoleEnum,
    User,
    UserFollow,
    UserRoleLink,
)
from app.models.otp import OTP
from app.models.record import MediaType, ReleaseRights
from app.models.record_history import ChangeSource
from app.services.language_service import LanguageService
from app.services.record_history_service import (
    RecordHistoryService,
)
from setup_postgresql import seed_initial_data as run_base_seed

typed_base_seed: Callable[[], bool] = cast(Callable[[], bool], run_base_seed)

SEED_ADMIN_USER = {
    "phone": "+919900000000",
    "username": "local_seed_admin",
    "name": "Local Seed Admin",
    "email": "local.seed.admin@example.com",
    "gender": "other",
    "date_of_birth": date(1990, 1, 1),
    "current_place": "Hyderabad, India",
    "short_bio": "Seeded admin user for local API and database testing.",
    "profession": "Administrator",
    "organisation": "Corpus Dev",
    "has_given_consent": True,
}

SEED_ADMIN_PASSWORD = "SeedAdmin@123"  # nosec B105

SEED_USER = {
    "phone": "+919900000001",
    "username": "local_seed_user",
    "name": "Local Seed User",
    "email": "local.seed.user@example.com",
    "gender": "other",
    "date_of_birth": date(1995, 5, 14),
    "current_place": "Hyderabad, India",
    "short_bio": "Seeded user for local API and database testing.",
    "profession": "Research Assistant",
    "organisation": "Corpus Dev",
    "has_given_consent": True,
}

SEED_PASSWORD = "SeedUser@123"  # nosec B105

SEED_RECORDS = [
    {
        "key": "text-story",
        "title": "Seed Text Story",
        "description": (
            "A deterministic text record used for local testing of "
            "listing, detail, and extracted text related API flows."
        ),
        "media_type": MediaType.text,
        "file_name": "seed_text_story.txt",
        "file_url": "https://example.local/files/seed_text_story.txt",
        "status": "uploaded",
        "release_rights": ReleaseRights.creator,
        "creator": "Local Seed User",
        "published_date": date(2023, 6, 1),
        "language": LANGUAGE_NOT_AVAILABLE,
        "category_names": ["literature", "folk tales"],
        "source_label": "Local Seed Dataset",
        "source_url": "https://example.local/source/seed-text-story",
        "extracted_text": {
            "version": 1,
            "text": "This is seeded extracted text for local development.",
            "segments": [
                {"text": "This is seeded extracted text for local development."}
            ],
        },
        "reviewed": False,
        "include_history": True,
        "include_location": False,
    },
    {
        "key": "audio-song",
        "title": "Seed Audio Song",
        "description": (
            "A seeded audio record for media type coverage in "
            "local testing without requiring a real uploaded asset."
        ),
        "media_type": MediaType.audio,
        "file_name": "seed_audio_song.mp3",
        "file_url": "https://example.local/files/seed_audio_song.mp3",
        "status": "uploaded",
        "release_rights": ReleaseRights.creator,
        "creator": "Local Seed User",
        "published_date": date(2022, 11, 10),
        "language": "telugu",
        "category_names": ["music", "folk_songs"],
        "source_label": "Local Seed Dataset",
        "source_url": "https://example.local/source/seed-audio-song",
        "duration_seconds": 183,
        "reviewed": True,
        "include_history": False,
        "include_location": False,
    },
    {
        "key": "image-market",
        "title": "Seed Market Image",
        "description": (
            "A seeded image record to validate image record listing, "
            "category links, and metadata rendering in local environments."
        ),
        "media_type": MediaType.image,
        "file_name": "seed_market_image.jpg",
        "file_url": "https://example.local/files/seed_market_image.jpg",
        "status": "uploaded",
        "release_rights": ReleaseRights.others,
        "creator": "Community Archive",
        "published_date": date(2021, 8, 15),
        "language": LANGUAGE_NOT_AVAILABLE,
        "category_names": ["images", "culture", "people"],
        "source_label": "Community Archive",
        "source_url": "https://example.local/source/seed-market-image",
        "reviewed": False,
        "include_history": False,
        "include_location": True,
    },
    {
        "key": "document-history",
        "title": "Seed Local History Document",
        "description": (
            "A seeded document record representing scanned or archived "
            "local history material for testing document flows "
            "and metadata views."
        ),
        "media_type": MediaType.document,
        "file_name": "seed_local_history_document.pdf",
        "file_url": "https://example.local/files/seed_local_history_document.pdf",
        "status": "pending",
        "release_rights": ReleaseRights.downloaded,
        "creator": "Local Library",
        "published_date": date(1984, 1, 1),
        "language": "hindi",
        "category_names": ["local_history", "old_newspapers"],
        "source_label": "Local Library",
        "source_url": "https://example.local/source/seed-local-history-document",
        "reviewed": False,
        "include_history": False,
        "include_location": False,
    },
]

SEED_RECORD_TITLES = [payload["title"] for payload in SEED_RECORDS]


def ensure_base_seed() -> None:
    """Ensure required base data exists."""
    if not typed_base_seed():
        raise RuntimeError(
            "Failed to seed base roles/categories before fake data."
        )


def get_role(session: Session, role_name: RoleEnum) -> Role:
    """Fetch a role by enum name."""
    role = session.exec(select(Role).where(Role.name == role_name)).first()
    if not role:
        raise RuntimeError(
            f"Role '{role_name.value}' not found. Seed base data first."
        )
    return role


def get_or_create_user(
    session: Session,
    user_payload: dict[str, Any],
    password: str,
    role: Role,
) -> tuple[User, bool]:
    """Create a seed user if missing and ensure the role link exists."""
    user = session.exec(
        select(User).where(User.phone == user_payload["phone"])
    ).first()
    created = False

    if not user:
        user = User(
            phone=user_payload["phone"],
            username=user_payload["username"],
            name=user_payload["name"],
            email=user_payload["email"],
            gender=user_payload["gender"],
            date_of_birth=user_payload["date_of_birth"],
            current_place=user_payload["current_place"],
            short_bio=user_payload["short_bio"],
            profession=user_payload["profession"],
            organisation=user_payload["organisation"],
            hashed_password=get_password_hash(password),
            has_given_consent=user_payload["has_given_consent"],
            is_active=True,
            last_login_at=datetime.now(timezone.utc),
        )
        session.add(user)
        session.flush()
        created = True

    role_link = session.exec(
        select(UserRoleLink).where(
            UserRoleLink.user_id == user.id,
            UserRoleLink.role_id == role.id,
        )
    ).first()
    if not role_link:
        session.add(UserRoleLink(user_id=user.id, role_id=role.id))

    return user, created


def get_category_ids(session: Session, category_names: list[str]) -> list[Any]:
    """Resolve category UUIDs from seeded category names."""
    category_ids: list[str] = []
    for category_name in category_names:
        category = session.exec(
            select(Category).where(Category.name == category_name)
        ).first()
        if category and category.id:
            category_ids.append(str(category.id))
    return category_ids


def maybe_build_location(include_location: bool) -> Any | None:
    """Build a sample PostGIS point when requested."""
    if not include_location:
        return None
    return WKTElement("POINT(78.4867 17.3850)", srid=4326)


def get_or_create_record(
    session: Session, user: User, payload: dict[str, Any]
) -> tuple[Record, bool]:
    """Create a deterministic record if missing."""
    record = session.exec(
        select(Record).where(
            Record.user_id == user.id,
            Record.title == payload["title"],
        )
    ).first()
    created = False

    if not record:
        reviewed_by = user.id if payload.get("reviewed") else None
        reviewed_at = (
            datetime.now(timezone.utc) if payload.get("reviewed") else None
        )

        record = Record(
            title=payload["title"],
            description=payload["description"],
            media_type=payload["media_type"],
            file_url=payload.get("file_url"),
            file_name=payload.get("file_name"),
            status=payload.get("status", "pending"),
            release_rights=payload.get("release_rights", ReleaseRights.NA),
            creator=payload.get("creator"),
            published_date=payload.get("published_date"),
            language=payload.get("language", LANGUAGE_NOT_AVAILABLE),
            user_id=user.id,
            reviewed=payload.get("reviewed", False),
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            category_ids=get_category_ids(
                session, payload.get("category_names", [])
            ),
            duration_seconds=payload.get("duration_seconds"),
            source_label=payload.get("source_label"),
            source_url=payload.get("source_url"),
            location=maybe_build_location(
                payload.get("include_location", False)
            ),
        )
        session.add(record)
        session.flush()
        created = True

    ensure_extracted_text(session, record, payload)

    return record, created


def ensure_extracted_text(
    session: Session, record: Record, payload: dict[str, Any]
) -> bool:
    """Create or update extracted text row for seeded records when requested."""
    extracted_payload = payload.get("extracted_text")
    if not extracted_payload:
        return False

    extracted_entry = session.exec(
        select(ExtractedText).where(ExtractedText.record_id == record.uid)
    ).first()
    created = False

    if extracted_entry is None:
        extracted_entry = ExtractedText(
            record_id=record.uid,
            extraction_type=extracted_payload.get("extraction_type", "manual"),
        )
        created = True

    extracted_entry.confidence = extracted_payload.get("confidence")
    extracted_entry.language = payload.get("language", LANGUAGE_NOT_AVAILABLE)
    extracted_entry.extraction_type = extracted_payload.get(
        "extraction_type", "manual"
    )
    extracted_entry.quality_score = extracted_payload.get("quality_score")
    extracted_entry.notes = extracted_payload.get("notes")
    extracted_entry.summary = extracted_payload.get(
        "summary"
    ) or extracted_payload.get("text")
    extracted_entry.model_name = extracted_payload.get("model_name")
    extracted_entry.processing_date = extracted_payload.get("processing_date")
    extracted_entry.segments = to_json_safe(extracted_payload.get("segments"))
    extracted_entry.named_entities = to_json_safe(
        extracted_payload.get("named_entities")
    )
    extracted_entry.extraction_metadata = to_json_safe(
        extracted_payload.get("metadata")
    )

    session.add(extracted_entry)
    return created


def ensure_points_event(session: Session, user: User, record: Record) -> bool:
    """Ensure the seeded record has a matching points event."""
    event = session.exec(
        select(PointsEvent).where(PointsEvent.record_uid == record.uid)
    ).first()
    if event:
        return False

    session.add(
        PointsEvent(
            user_id=user.id,
            record_uid=record.uid,
            points=1.0,
            reason="record_created",
        )
    )
    return True


def to_json_safe(value: Any) -> Any:
    """Convert nested values into JSON-serializable primitives."""
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [to_json_safe(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, enum.Enum):
        return value.value
    return value


def ensure_history_version(
    session: Session, user: User, record: Record, seed_key: str
) -> tuple[bool, bool]:
    """Ensure one record has initial version/history metadata."""
    # We now use version 0 as the initial state
    version = session.exec(
        select(RecordVersion).where(RecordVersion.record_id == record.uid)
    ).first()
    history = session.exec(
        select(RecordHistory).where(
            RecordHistory.record_id == record.uid,
            RecordHistory.version_number == 0,
        )
    ).first()

    history_created = False
    version_created = False

    if not version or not history:
        history_service = RecordHistoryService(session)
        history_service.initialize_record_history(
            record=record,
            created_by=user.id,
            change_source=ChangeSource.system_process,
            change_reason=(
                f"Initial fake seed record creation (seed_key: {seed_key})"
            ),
        )
        history_created = True
        version_created = True

    return history_created, version_created


def clear_database(session: Session) -> dict[str, int]:
    """Clear existing app data for local reseeding.

    Preserves base role definitions.
    """
    summary = {
        "extracted_text_deleted": 0,
        "languages_deleted": 0,
        "record_restore_deleted": 0,
        "points_deleted": 0,
        "history_deleted": 0,
        "versions_deleted": 0,
        "follows_deleted": 0,
        "otp_deleted": 0,
        "records_deleted": 0,
        "categories_deleted": 0,
        "role_links_deleted": 0,
        "users_deleted": 0,
    }

    extracted_text_deleted = execute_delete(session, delete(ExtractedText))
    summary["extracted_text_deleted"] = extracted_text_deleted.rowcount or 0

    languages_deleted = execute_delete(session, delete(LanguageEntry))
    summary["languages_deleted"] = languages_deleted.rowcount or 0

    record_restore_deleted = execute_delete(session, delete(RecordRestore))
    summary["record_restore_deleted"] = record_restore_deleted.rowcount or 0

    points_deleted = execute_delete(session, delete(PointsEvent))
    summary["points_deleted"] = points_deleted.rowcount or 0

    history_deleted = execute_delete(session, delete(RecordHistory))
    summary["history_deleted"] = history_deleted.rowcount or 0

    versions_deleted = execute_delete(session, delete(RecordVersion))
    summary["versions_deleted"] = versions_deleted.rowcount or 0

    follows_deleted = execute_delete(session, delete(UserFollow))
    summary["follows_deleted"] = follows_deleted.rowcount or 0

    otp_deleted = execute_delete(session, delete(OTP))
    summary["otp_deleted"] = otp_deleted.rowcount or 0

    records_deleted = execute_delete(session, delete(Record))
    summary["records_deleted"] = records_deleted.rowcount or 0

    categories_deleted = execute_delete(session, delete(Category))
    summary["categories_deleted"] = categories_deleted.rowcount or 0

    role_links_deleted = execute_delete(session, delete(UserRoleLink))
    summary["role_links_deleted"] = role_links_deleted.rowcount or 0

    user_deleted = execute_delete(session, delete(User))
    summary["users_deleted"] = user_deleted.rowcount or 0

    return summary


def execute_delete(session: Session, statement: Delete) -> CursorResult[Any]:
    """Execute a delete statement and return the cursor result."""
    return session.connection().execute(statement)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Seed or clear local fake database data."
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help=(
            "Clear existing app data used for local testing before "
            "seeding fresh fake data."
        ),
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help=(
            "When used with --clear, clear the seeded dataset and "
            "exit without reseeding."
        ),
    )
    args = parser.parse_args()
    if args.no_seed and not args.clear:
        parser.error("--no-seed can only be used together with --clear")
    return args


def main() -> int:
    """Seed the local fake dataset."""
    args = parse_args()

    print("Seeding database with local corpus dataset")
    print("Configuration: 1 admin, 1 user, 4 records")

    summary = {
        "admin_created": 0,
        "user_created": 0,
        "records_created": 0,
        "points_created": 0,
        "history_created": 0,
        "versions_created": 0,
    }
    clear_summary = {
        "extracted_text_deleted": 0,
        "languages_deleted": 0,
        "points_deleted": 0,
        "history_deleted": 0,
        "versions_deleted": 0,
        "record_restore_deleted": 0,
        "follows_deleted": 0,
        "otp_deleted": 0,
        "records_deleted": 0,
        "categories_deleted": 0,
        "role_links_deleted": 0,
        "users_deleted": 0,
    }

    with Session(engine) as session:
        try:
            if args.clear:
                print("\nClearing existing data...")
                clear_summary = clear_database(session)
                session.commit()

            if args.no_seed:
                print(
                    "  Deleted "
                    f"{clear_summary['extracted_text_deleted']} "
                    "records from extractedtext"
                )
                print(
                    f"  Deleted {clear_summary['languages_deleted']} "
                    "records from language"
                )
                print(
                    f"  Deleted "
                    f"{clear_summary['record_restore_deleted']} "
                    f"records from recordrestore"
                )
                print(
                    f"  Deleted {clear_summary['points_deleted']} "
                    f"records from pointsevent"
                )
                print(
                    f"  Deleted {clear_summary['history_deleted']} "
                    f"records from recordhistory"
                )
                print(
                    f"  Deleted "
                    f"{clear_summary['versions_deleted']} "
                    f"records from recordversion"
                )
                print(
                    f"  Deleted {clear_summary['follows_deleted']} "
                    f"records from user_follows"
                )
                print(
                    f"  Deleted {clear_summary['otp_deleted']} records from otp"
                )
                print(
                    f"  Deleted {clear_summary['records_deleted']} "
                    f"records from record"
                )
                print(
                    f"  Deleted "
                    f"{clear_summary['categories_deleted']} "
                    f"records from category"
                )
                print(
                    f"  Deleted "
                    f"{clear_summary['role_links_deleted']} "
                    f"records from user_roles"
                )
                print(
                    f"  Deleted {clear_summary['users_deleted']} "
                    f"records from user"
                )
                print("Database cleared.\n")
                return 0

            ensure_base_seed()
            LanguageService.ensure_default_languages(session)

            print("\n=== Phase 1: Users ===")

            admin_role = get_role(session, RoleEnum.admin)
            user_role = get_role(session, RoleEnum.user)

            _, admin_created = get_or_create_user(
                session, SEED_ADMIN_USER, SEED_ADMIN_PASSWORD, admin_role
            )
            user, user_created = get_or_create_user(
                session, SEED_USER, SEED_PASSWORD, user_role
            )
            if admin_created:
                summary["admin_created"] += 1
            if user_created:
                summary["user_created"] += 1

            print("\n=== Phase 2: Records ===")
            for payload in SEED_RECORDS:
                record, record_created = get_or_create_record(
                    session, user, payload
                )
                if record_created:
                    summary["records_created"] += 1

                if ensure_points_event(session, user, record):
                    summary["points_created"] += 1

                if payload.get("include_history"):
                    seed_key = str(payload["key"])
                    history_created, version_created = ensure_history_version(
                        session, user, record, seed_key
                    )
                    if history_created:
                        summary["history_created"] += 1
                    if version_created:
                        summary["versions_created"] += 1

            session.commit()
        except Exception:
            session.rollback()
            raise

    if args.clear:
        print(
            "  Deleted "
            f"{clear_summary['extracted_text_deleted']} "
            "records from extractedtext"
        )
        print(
            f"  Deleted {clear_summary['languages_deleted']} "
            "records from language"
        )
        print(
            f"  Deleted "
            f"{clear_summary['record_restore_deleted']} "
            f"records from recordrestore"
        )
        print(
            f"  Deleted {clear_summary['points_deleted']} "
            f"records from pointsevent"
        )
        print(
            f"  Deleted {clear_summary['history_deleted']} "
            f"records from recordhistory"
        )
        print(
            f"  Deleted "
            f"{clear_summary['versions_deleted']} "
            f"records from recordversion"
        )
        print(
            f"  Deleted {clear_summary['follows_deleted']} "
            f"records from user_follows"
        )
        print(f"  Deleted {clear_summary['otp_deleted']} records from otp")
        print(
            f"  Deleted {clear_summary['records_deleted']} records from record"
        )
        print(
            f"  Deleted "
            f"{clear_summary['categories_deleted']} "
            f"records from category"
        )
        print(
            f"  Deleted "
            f"{clear_summary['role_links_deleted']} "
            f"records from user_roles"
        )
        print(f"  Deleted {clear_summary['users_deleted']} records from user")
        print("Database cleared.\n")

    print("=== Seeding Complete! ===")
    print("Users created:")
    print(f"  - Admin users: {summary['admin_created']}")
    print(f"  - Regular users: {summary['user_created']}")
    print()
    print(f"Records created: {summary['records_created']}")
    print(f"Points events created: {summary['points_created']}")
    print(f"Record history rows created: {summary['history_created']}")
    print(f"Record version rows created: {summary['versions_created']}")
    print()
    print("Database seeded successfully!\n")
    print("Sample login credentials (phone + password):")
    print(
        f"  Admin: {SEED_ADMIN_USER['name']} | "
        f"Phone: {SEED_ADMIN_USER['phone']} | "
        f"Pass: {SEED_ADMIN_PASSWORD}"
    )
    print(
        f"  User: {SEED_USER['name']} | "
        f"Phone: {SEED_USER['phone']} | "
        f"Pass: {SEED_PASSWORD}"
    )
    print()
    print("NOTE: Login using the phone/password endpoint at /api/v1/auth/login")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

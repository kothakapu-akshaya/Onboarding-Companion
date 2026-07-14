"""Resolve extracted text for a record with sibling fallback by file_hash."""

import copy
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import cast
from uuid import UUID

from sqlalchemy import func, tuple_
from sqlmodel import Session, select

from app.models.extracted_text import ExtractedText
from app.models.record import Record

SiblingRow = tuple[ExtractedText, UUID, str, UUID]


def _priority_tuple(
    et: ExtractedText,
) -> tuple[int, int, datetime]:
    ext_type = (et.extraction_type or "").lower()
    is_preferred = ext_type in ("asr", "ocr")
    has_segments = bool(et.segments)
    created = et.created_at or datetime.min.replace(tzinfo=timezone.utc)
    return (1 if is_preferred else 0, 1 if has_segments else 0, created)


def _best_from_rows(
    rows: Sequence[SiblingRow],
) -> tuple[ExtractedText, UUID]:
    best = max(rows, key=lambda r: _priority_tuple(r[0]))
    return best[0], best[1]


def _query_siblings(
    exclude_uids: list[UUID],
    pairs: list[tuple[str, UUID]],
    session: Session,
) -> list[SiblingRow]:
    query = (
        select(
            ExtractedText,
            Record.uid,
            Record.file_hash,
            Record.user_id,
        )
        .join(Record, ExtractedText.record_id == Record.uid)  # type: ignore[arg-type]
        .where(tuple_(Record.file_hash, Record.user_id).in_(pairs))  # type: ignore[union-attr]
        .where(Record.uid.notin_(exclude_uids))  # type: ignore[union-attr]
        .where(func.coalesce(ExtractedText.skipped, False).is_(False))
    )
    result = session.exec(query).all()
    return result  # type: ignore[return-value]


def _group_by_hash(
    rows: list[SiblingRow],
) -> dict[tuple[str, UUID], list[SiblingRow]]:
    groups: dict[tuple[str, UUID], list[SiblingRow]] = {}
    for row in rows:
        _, _, hash_val, owner_id = row
        groups.setdefault((hash_val, owner_id), []).append(row)
    return groups


class ExtractedTextResolver:
    """Resolves extracted text for a record, falling back to siblings.

    If a record has no extracted text of its own but another record with
    the same ``file_hash`` does, the sibling's extracted text is returned
    at read time.  A ``source_record_id`` is provided so the caller can
    indicate where the text originated.
    """

    @staticmethod
    def resolve(
        record: Record,
        session: Session,
    ) -> tuple[ExtractedText | None, UUID | None]:
        """Resolve extracted text for a record: own first, then sibling."""
        own_text = getattr(record, "extracted_text", None)
        if own_text is not None:
            return own_text, None

        file_hash = getattr(record, "file_hash", None)
        if not file_hash:
            return None, None

        exclude = [cast(UUID, record.uid)]
        owner_id = getattr(record, "user_id", None)
        if owner_id is None:
            return None, None

        rows = _query_siblings(
            exclude,
            [(file_hash, cast(UUID, owner_id))],
            session,
        )
        if not rows:
            return None, None
        return _best_from_rows(rows)

    @staticmethod
    def batch_resolve(
        records: Sequence[Record],
        session: Session,
    ) -> dict[UUID, tuple[ExtractedText, UUID]]:
        """Batch-resolve fallback text; one query per distinct hash."""
        needy = [
            r
            for r in records
            if getattr(r, "extracted_text", None) is None
            and getattr(r, "file_hash", None)
        ]
        if not needy:
            return {}

        all_exclude = [cast(UUID, r.uid) for r in needy]
        pairs = list(
            {
                (cast(str, r.file_hash), cast(UUID, r.user_id))
                for r in needy
                if getattr(r, "user_id", None)
            }
        )
        if not pairs:
            return {}

        rows = _query_siblings(all_exclude, pairs, session)

        hash_best: dict[tuple[str, UUID], tuple[ExtractedText, UUID]] = {}
        for key, group in _group_by_hash(rows).items():
            hash_best[key] = _best_from_rows(group)

        result: dict[UUID, tuple[ExtractedText, UUID]] = {}
        for r in needy:
            uid = cast(UUID, r.uid)
            fh = cast(str, r.file_hash)
            owner_id = cast(UUID, r.user_id)
            key = (fh, owner_id)
            if key in hash_best:
                result[uid] = hash_best[key]

        return result

    @staticmethod
    def copy_to_record(source: ExtractedText, record_id: UUID) -> ExtractedText:
        """Copy-on-write: clone *source* fields into a new ExtractedText.

        owned by *record_id*.

        Identity and audit fields (uid, created_at, updated_at) are
        omitted so SQLModel defaults regenerate them.
        """
        return ExtractedText(
            record_id=record_id,
            confidence=source.confidence,
            language=source.language,
            extraction_type=source.extraction_type,
            quality_score=source.quality_score,
            notes=source.notes,
            summary=source.summary,
            model_name=source.model_name,
            processing_date=source.processing_date,
            segments=copy.deepcopy(source.segments),
            named_entities=copy.deepcopy(source.named_entities),
            extraction_metadata=copy.deepcopy(source.extraction_metadata),
            dataset=source.dataset,
        )

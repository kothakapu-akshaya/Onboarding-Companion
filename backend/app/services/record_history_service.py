"""Optimized V2 Record History Service.

SERVICE ARCHITECTURE:
====================

This service implements the V2 unified history system, replacing
the multi-table V1 approach with a simplified, high-performance design.

Key Responsibilities:
1. Write Operations:
   - initialize_record_history: Create version 0 for new records
   - create_history_entry: Record changes with single insertion
   - capture_record_changes: Calculate and record field-level diffs
   - restore_record_version: Handle version restoration

2. Read Operations:
   - get_record_history: Paginated history with filters
   - get_record_version: Specific version retrieval
   - compare_versions: Diff calculation between versions
   - get_field_history: Field-level change tracking
   - get_version_summary: Quick version metadata

3. Analytics:
   - get_user_edit_metrics: User activity statistics
   - get_user_edit_activity: Dashboard-compatible metrics
   - get_history_count: Efficient count queries

DESIGN DECISIONS:
=================

1. Single-Table Writes:
   - Each history entry is ONE row in record_history_v2
   - field_changes stored as JSONB (not separate table)
   - Eliminates RecordFieldHistory table entirely

2. Version Tracking:
   - record_version_v2 updated atomically with each write
   - Aggregated counters avoid counting rows
   - Snapshot creation tracked via last_major_version

3. Snapshot Strategy:
   - Major snapshots created every 10 versions
   - Also created for version 1 and admin overrides
   - Stored in record_major_snapshot table

4. Field Change Format:
   {
       "field_name": {
           "old": "previous value",
           "new": "new value",
           "reason": "optional explanation"
       }
   }

TRANSACTION SAFETY:
===================

All write operations use session.flush() for immediate persistence
without committing the full transaction. This ensures:
- Version increments are atomic
- Partial failures rollback cleanly
- Caller controls commit/rollback

MIGRATION SUPPORT:
==================

Historical data is migrated within the Alembic migration
7d08531e7714_create_v2_history_schema.
"""

import logging
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast
from sqlalchemy import asc as sa_asc
from sqlalchemy import desc as sa_desc
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, and_, col, desc, func, select

from app.models.extracted_text import ExtractedText
from app.models.record import Record
from app.models.record_history import (
    ChangeSource,
    ChangeType,
    RecordHistory,
    RecordMajorSnapshot,
    RecordRestore,
    RecordVersion,
)

logger = logging.getLogger(__name__)


def _serialize_value(value: Any) -> Any:
    """Serialize values for field_changes comparison.

    Scalars are converted to strings for stable comparison.
    Complex types (dict, list) are kept as-is so snapshot
    reconstruction preserves their original structure.
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    return str(value)


# V1↔V2 field_changes key mapping
V1_FIELD_OLD = "old_value"
V1_FIELD_NEW = "new_value"
V1_FIELD_TYPE = "change_type"
V1_FIELD_REASON = "change_reason"

V2_FIELD_OLD = "old"
V2_FIELD_NEW = "new"
V2_FIELD_TYPE = "type"
V2_FIELD_REASON = "reason"


def _v2_field_changes_to_v1(
    v2_changes: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Transform V2 field_changes to V1 format."""
    v1_changes: dict[str, dict[str, Any]] = {}
    for field, change in v2_changes.items():
        old_val = change.get(V2_FIELD_OLD)
        new_val = change.get(V2_FIELD_NEW)
        stored_type = change.get(V2_FIELD_TYPE)
        if stored_type is not None:
            change_type = stored_type
        elif old_val is not None and new_val is None:
            change_type = "removed"
        elif old_val is not None:
            change_type = "updated"
        else:
            change_type = "added"
        v1_changes[field] = {
            V1_FIELD_OLD: old_val,
            V1_FIELD_NEW: new_val,
            V1_FIELD_TYPE: change_type,
            V1_FIELD_REASON: change.get(V2_FIELD_REASON),
        }
    return v1_changes


def _v1_field_changes_to_v2(
    v1_changes: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Transform V1 field_changes to V2 format."""
    v2_changes: dict[str, dict[str, Any]] = {}
    for field, change in v1_changes.items():
        v2_changes[field] = {
            V2_FIELD_OLD: change.get(V1_FIELD_OLD),
            V2_FIELD_NEW: change.get(V1_FIELD_NEW),
            V2_FIELD_TYPE: change.get(V1_FIELD_TYPE),
            V2_FIELD_REASON: change.get("change_reason"),
        }
    return v2_changes


def _v2_entry_to_v1_dict(entry: RecordHistory) -> dict[str, Any]:
    """Convert a RecordHistory ORM object to a V1-shaped dict."""
    return {
        "uid": entry.uid,
        "record_id": entry.record_id,
        "version_number": entry.version_number,
        "change_type": entry.change_type,
        "change_source": entry.change_source,
        "changed_by": entry.changed_by,
        "record_snapshot": entry.full_snapshot or {},
        "field_changes": _v2_field_changes_to_v1(entry.field_changes),
        "change_reason": entry.change_reason,
        "change_metadata": entry.change_metadata or {},
        "created_at": entry.created_at,
    }


class RecordHistoryService:
    """Optimized service for record history management - V2."""

    MAJOR_VERSION_INTERVAL = 10

    def __init__(self, session: Session):
        """Initialize the service."""
        self.session = session

    def initialize_record_history(
        self,
        record: Record,
        created_by: UUID,
        change_source: ChangeSource = ChangeSource.system_process,
        change_reason: str | None = None,
        change_metadata: dict[str, Any] | None = None,
    ) -> tuple[RecordHistory, RecordVersion]:
        """Initialize version 0 history for a newly created record."""
        initial_snapshot = self._create_record_snapshot(record)

        if record.uid is None:
            raise ValueError("Record must have a uid to initialize history")
        initial_history = RecordHistory(
            record_id=record.uid,
            version_number=0,
            change_type=ChangeType.created,
            change_source=change_source,
            changed_by=created_by,
            field_changes={},
            full_snapshot=initial_snapshot,
            change_reason=change_reason
            or "Initial record creation (version 0)",
            change_metadata=change_metadata
            or {"creation_type": "initial_state"},
        )

        version_info = self._get_or_create_version_info(record.uid)
        version_info.current_version = 0
        version_info.total_changes = 1
        version_info.last_changed_by = created_by
        version_info.last_change_at = datetime.now(timezone.utc)
        version_info.last_major_version = 0

        if change_source == ChangeSource.system_process:
            version_info.system_updates = 1
        elif change_source == ChangeSource.user_edit:
            version_info.user_edits = 1
        elif change_source == ChangeSource.admin_action:
            version_info.admin_edits = 1

        self.session.add(initial_history)
        self.session.add(version_info)

        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise ValueError(
                f"Record {record.uid} already has history initialized"
            ) from None

        return initial_history, version_info

    def create_history_entry(
        self,
        record: Record,
        changed_by: UUID,
        change_type: ChangeType,
        change_source: ChangeSource,
        field_changes: dict[str, dict[str, Any]],
        change_reason: str | None = None,
        change_metadata: dict[str, Any] | None = None,
    ) -> RecordHistory:
        """Create a new history entry with unified single-table storage."""
        if record.uid is None:
            raise ValueError("Record must have a uid to create history entry")
        version_info = self._get_or_create_version_info(record.uid)

        version_info.current_version += 1
        version_info.total_changes += 1
        version_info.last_changed_by = changed_by
        version_info.last_change_at = datetime.now(timezone.utc)

        if change_source == ChangeSource.user_edit:
            version_info.user_edits += 1
        elif change_source == ChangeSource.admin_action:
            version_info.admin_edits += 1
        elif change_source == ChangeSource.system_process:
            version_info.system_updates += 1

        record_snapshot = self._create_record_snapshot(record)

        is_major_version = (
            version_info.current_version % self.MAJOR_VERSION_INTERVAL == 0
        )
        is_admin_override = change_type == ChangeType.admin_override

        history_entry = RecordHistory(
            record_id=record.uid,
            version_number=version_info.current_version,
            change_type=change_type,
            change_source=change_source,
            changed_by=changed_by,
            field_changes=field_changes,
            full_snapshot=record_snapshot
            if is_major_version or is_admin_override
            else None,
            change_reason=change_reason,
            change_metadata=change_metadata or {},
        )

        self.session.add(history_entry)
        self.session.add(version_info)
        self.session.flush()

        if self._should_create_major_snapshot(
            version_info.current_version, change_type
        ):
            self._create_major_snapshot(
                record, version_info.current_version, changed_by
            )
            version_info.last_major_version = version_info.current_version
            version_info.last_snapshot_at = datetime.now(timezone.utc)

        return history_entry

    def capture_record_changes(
        self,
        record_id: UUID,
        old_values: dict[str, Any],
        new_values: dict[str, Any],
        changed_by: UUID,
        change_source: ChangeSource = ChangeSource.user_edit,
        change_reason: str | None = None,
    ) -> RecordHistory | None:
        """Capture and record changes between old and new values."""
        field_changes = self._calculate_field_changes(old_values, new_values)
        field_changes.pop("snapshot_timestamp", None)

        if not field_changes:
            return None

        record = self.session.get(Record, record_id)
        if not record:
            raise ValueError(f"Record {record_id} not found")

        change_type = ChangeType.updated
        if change_source == ChangeSource.admin_action:
            change_type = ChangeType.admin_override

        return self.create_history_entry(
            record=record,
            changed_by=changed_by,
            change_type=change_type,
            change_source=change_source,
            field_changes=field_changes,
            change_reason=change_reason,
        )

    def capture_extracted_text_change(
        self,
        record: Record,
        changed_by: UUID,
        change_source: ChangeSource,
        change_reason: str | None = None,
    ) -> RecordHistory | None:
        """Capture extracted text changes via snapshot/diff logic."""
        new_snapshot = self._create_record_snapshot(record)

        latest = self.session.exec(
            select(RecordHistory)
            .where(RecordHistory.record_id == record.uid)
            .order_by(desc(RecordHistory.version_number))
            .limit(1)
        ).first()

        old_snapshot = self._get_record_snapshot(latest) if latest else {}

        field_changes = self._calculate_field_changes(
            old_snapshot, new_snapshot
        )
        field_changes.pop("snapshot_timestamp", None)

        # Only keep extracted_text changes — this method is about ET only
        et_change = field_changes.get("extracted_text")
        field_changes.clear()
        if et_change is not None:
            field_changes["extracted_text"] = et_change

        if not field_changes:
            return None

        change_type = (
            ChangeType.admin_override
            if change_source == ChangeSource.admin_action
            else ChangeType.updated
        )

        return self.create_history_entry(
            record=record,
            changed_by=changed_by,
            change_type=change_type,
            change_source=change_source,
            field_changes=field_changes,
            change_reason=change_reason,
        )

    def get_record_history(
        self,
        record_id: UUID,
        limit: int = 50,
        offset: int = 0,
        change_type: ChangeType | None = None,
        change_source: ChangeSource | None = None,
    ) -> list[dict[str, Any]]:
        """Get history entries as V1-shaped dicts."""
        query = select(RecordHistory).where(
            RecordHistory.record_id == record_id
        )

        if change_type:
            query = query.where(RecordHistory.change_type == change_type)
        if change_source:
            query = query.where(RecordHistory.change_source == change_source)

        query = (
            query.order_by(desc(RecordHistory.version_number))
            .offset(offset)
            .limit(limit)
        )

        return [_v2_entry_to_v1_dict(e) for e in self.session.exec(query).all()]

    def get_record_version(
        self, record_id: UUID, version: int
    ) -> dict[str, Any] | None:
        """Get a specific version as a V1-shaped dict."""
        entry = self.session.exec(
            select(RecordHistory).where(
                and_(
                    RecordHistory.record_id == record_id,
                    RecordHistory.version_number == version,
                )
            )
        ).first()
        return _v2_entry_to_v1_dict(entry) if entry else None

    def compare_versions(
        self, record_id: UUID, from_version: int, to_version: int
    ) -> dict[str, Any]:
        """Compare two versions, return V1-shaped RecordDiff dict."""
        from_record = self.session.exec(
            select(RecordHistory).where(
                and_(
                    RecordHistory.record_id == record_id,
                    RecordHistory.version_number == from_version,
                )
            )
        ).first()
        to_record = self.session.exec(
            select(RecordHistory).where(
                and_(
                    RecordHistory.record_id == record_id,
                    RecordHistory.version_number == to_version,
                )
            )
        ).first()

        if not from_record or not to_record:
            raise ValueError("One or both versions not found")

        diff = self._calculate_diff(
            self._get_record_snapshot(from_record),
            self._get_record_snapshot(to_record),
        )
        return {
            "record_id": record_id,
            "from_version": from_version,
            "to_version": to_version,
            "added_fields": diff.get("added", {}),
            "removed_fields": diff.get("removed", {}),
            "changed_fields": diff.get("changed", {}),
            "total_changes": diff.get("total_changes", 0),
            "change_types": diff.get("change_types", []),
            "created_at": datetime.now(timezone.utc),
        }

    def get_field_history(
        self, record_id: UUID, field_name: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get field history shaped as V1 RecordFieldHistory dicts."""
        history_entries = self.session.exec(
            select(RecordHistory)
            .where(RecordHistory.record_id == record_id)
            .where(
                cast(RecordHistory.field_changes[field_name], String).isnot(
                    None
                )
            )
            .order_by(desc(RecordHistory.version_number))
            .limit(limit)
        ).all()

        field_history = []
        for entry in history_entries:
            change = entry.field_changes[field_name]
            field_history.append(
                {
                    "uid": entry.uid,
                    "record_history_id": entry.uid,
                    "record_id": record_id,
                    "field_name": field_name,
                    "old_value": change.get("old"),
                    "new_value": change.get("new"),
                    "change_reason": change.get("reason"),
                    "validation_errors": None,
                    "validation_warnings": None,
                    "created_at": entry.created_at,
                }
            )

        return field_history

    def restore_record_version(
        self,
        record_id: UUID,
        target_version: int,
        restored_by: UUID,
        restore_reason: str,
        fields_to_restore: list[str] | None = None,
        requires_approval: bool = False,
    ) -> RecordRestore:
        """Restore a record to a previous version."""
        record = self.session.get(Record, record_id)
        if not record:
            raise ValueError(f"Record {record_id} not found")

        target_history = self.session.exec(
            select(RecordHistory).where(
                and_(
                    RecordHistory.record_id == record_id,
                    RecordHistory.version_number == target_version,
                )
            )
        ).first()
        if not target_history:
            raise ValueError(f"Version {target_version} not found")

        version_info = self._get_or_create_version_info(record_id)
        current_version = version_info.current_version

        restore_record = RecordRestore(
            record_id=record_id,
            restored_from_version=current_version,
            restored_to_version=target_version,
            restored_by=restored_by,
            restore_reason=restore_reason,
            restored_fields=fields_to_restore or [],
            partial_restore=bool(fields_to_restore),
            requires_approval=requires_approval,
            approval_status="approved" if not requires_approval else "pending",
        )

        self.session.add(restore_record)

        if not requires_approval:
            self._apply_restoration(
                record, target_history, fields_to_restore, restored_by
            )

        self.session.flush()
        return restore_record

    def approve_restore(
        self, restore_id: UUID, approved_by: UUID
    ) -> RecordRestore:
        """Approve a pending restore operation."""
        restore_record = self.session.get(RecordRestore, restore_id)
        if not restore_record:
            raise ValueError("Restore record not found")

        if restore_record.approval_status != "pending":
            raise ValueError("Restore is not pending approval")

        record = self.session.get(Record, restore_record.record_id)
        target_history = self.session.exec(
            select(RecordHistory).where(
                and_(
                    RecordHistory.record_id == restore_record.record_id,
                    RecordHistory.version_number
                    == restore_record.restored_to_version,
                )
            )
        ).first()

        if record is None:
            raise ValueError(
                f"Record {restore_record.record_id} not found for restoration"
            )
        if target_history is None:
            raise ValueError(
                f"Target version {restore_record.restored_to_version} "
                f"not found for restoration"
            )

        restore_record.approved_by = approved_by
        restore_record.approval_status = "approved"
        restore_record.approved_at = datetime.now(timezone.utc)

        self._apply_restoration(
            record,
            target_history,
            restore_record.restored_fields
            if restore_record.partial_restore
            else None,
            approved_by,
        )

        self.session.add(restore_record)
        return restore_record

    def get_restore_details(self, restore_id: UUID) -> RecordRestore | None:
        """Get details of a specific restore operation."""
        return self.session.get(RecordRestore, restore_id)

    def get_pending_restores(self, limit: int = 50) -> Sequence[RecordRestore]:
        """Get pending restore operations requiring approval."""
        return self.session.exec(
            select(RecordRestore)
            .where(RecordRestore.approval_status == "pending")
            .order_by(sa_desc(col(RecordRestore.created_at)))
            .limit(limit)
        ).all()

    def get_version_summary(self, record_id: UUID) -> dict[str, Any]:
        """Get version summary for a record."""
        version_info = self.session.exec(
            select(RecordVersion).where(RecordVersion.record_id == record_id)
        ).first()

        if not version_info:
            return {
                "record_id": record_id,
                "current_version": 0,
                "total_changes": 0,
                "last_changed": None,
                "change_breakdown": {},
            }

        return {
            "record_id": record_id,
            "current_version": version_info.current_version,
            "total_changes": version_info.total_changes,
            "last_changed": version_info.last_change_at,
            "last_changed_by": version_info.last_changed_by,
            "last_major_version": version_info.last_major_version,
            "last_snapshot_at": version_info.last_snapshot_at,
            "change_breakdown": {
                "user_edit": version_info.user_edits,
                "admin": version_info.admin_edits,
                "system": version_info.system_updates,
            },
        }

    def get_history_count(self, record_id: UUID) -> int:
        """Get total history entry count for a record."""
        return (
            self.session.exec(
                select(func.count(RecordHistory.uid)).where(  # type: ignore[bad-argument-type]
                    RecordHistory.record_id == record_id
                )
            ).first()
            or 0
        )

    def get_recent_history(
        self, record_id: UUID, since: datetime, limit: int = 100
    ) -> Sequence[RecordHistory]:
        """Get recent history entries since a given datetime."""
        return self.session.exec(
            select(RecordHistory)
            .where(RecordHistory.record_id == record_id)
            .where(RecordHistory.created_at >= since)
            .order_by(desc(RecordHistory.created_at))
            .limit(limit)
        ).all()

    def get_user_history(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[RecordHistory]:
        """Get all history entries changed by a specific user."""
        return self.session.exec(
            select(RecordHistory)
            .where(RecordHistory.changed_by == user_id)
            .order_by(desc(RecordHistory.created_at))
            .offset(offset)
            .limit(limit)
        ).all()

    def get_user_edit_metrics(self, user_id: UUID) -> dict[str, Any]:
        """Get comprehensive edit metrics for a user."""
        from app.models.user import User

        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        total_edits = (
            self.session.exec(
                select(func.count(RecordHistory.uid)).where(  # type: ignore[bad-argument-type]
                    RecordHistory.changed_by == user_id
                )
            ).first()
            or 0
        )

        records_edited = (
            self.session.exec(
                select(
                    func.count(func.distinct(RecordHistory.record_id))
                ).where(RecordHistory.changed_by == user_id)
            ).first()
            or 0
        )

        average_edits_per_record = (
            total_edits / records_edited if records_edited > 0 else 0.0
        )

        return {
            "user_id": user_id,
            "user_name": user.name,
            "total_edits": total_edits,
            "records_edited": records_edited,
            "average_edits_per_record": round(average_edits_per_record, 2),
        }

    def get_user_edit_activity(self, user_id: UUID) -> dict[str, Any]:
        """Get simplified edit activity for dashboard views."""
        from app.models.user import User

        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        total_edits = (
            self.session.exec(
                select(func.count(RecordHistory.uid)).where(  # type: ignore[bad-argument-type]
                    RecordHistory.changed_by == user_id
                )
            ).first()
            or 0
        )

        recent_edits = (
            self.session.exec(
                select(func.count(RecordHistory.uid))  # type: ignore[bad-argument-type]
                .where(RecordHistory.changed_by == user_id)
                .where(RecordHistory.created_at >= thirty_days_ago)
            ).first()
            or 0
        )

        records_edited = (
            self.session.exec(
                select(
                    func.count(func.distinct(RecordHistory.record_id))
                ).where(RecordHistory.changed_by == user_id)
            ).first()
            or 0
        )

        last_edit = self.session.exec(
            select(RecordHistory.created_at)
            .where(RecordHistory.changed_by == user_id)
            .order_by(sa_desc(RecordHistory.created_at))  # type: ignore[bad-argument-type]
            .limit(1)
        ).first()

        average_edits_per_record = (
            round(total_edits / records_edited, 2) if records_edited else 0
        )

        return {
            "user_id": user_id,
            "user_name": user.name,
            "total_edits": total_edits,
            "recent_edits": recent_edits,
            "records_edited": records_edited,
            "average_edits_per_record": average_edits_per_record,
            "last_edit_date": last_edit,
        }

    def _get_or_create_version_info(self, record_id: UUID) -> RecordVersion:
        """Get or create version info for a record."""
        version_info = self.session.exec(
            select(RecordVersion)
            .where(RecordVersion.record_id == record_id)
            .with_for_update()
        ).first()

        if not version_info:
            version_info = RecordVersion(
                record_id=record_id,
                total_changes=0,
                last_change_at=datetime.now(timezone.utc),
            )

        return version_info

    def _create_record_snapshot(self, record: Record) -> dict[str, Any]:
        """Create a snapshot of current record state."""
        snapshot = record.model_dump(mode="json", exclude={"location"})

        extracted_text_entry = getattr(record, "extracted_text", None)
        if (
            extracted_text_entry is None
            and getattr(record, "uid", None) is not None
        ):
            extracted_text_entry = self.session.exec(
                select(ExtractedText).where(
                    ExtractedText.record_id == record.uid
                )
            ).first()

        if extracted_text_entry and hasattr(extracted_text_entry, "confidence"):
            snapshot["extracted_text"] = self._serialize_extracted_text(
                extracted_text_entry
            )

        if record.location:
            from app.utils.postgis_utils import (
                extract_coordinates_from_geometry,
            )

            coords = extract_coordinates_from_geometry(record.location)
            if coords:
                snapshot["location"] = {
                    "latitude": coords[1],
                    "longitude": coords[0],
                }

        snapshot["snapshot_timestamp"] = datetime.now(timezone.utc).isoformat()

        return snapshot

    def _serialize_extracted_text(
        self, extracted_text: ExtractedText
    ) -> dict[str, Any]:
        return {
            "confidence": extracted_text.confidence,
            "language": extracted_text.language,
            "extraction_type": extracted_text.extraction_type,
            "quality_score": extracted_text.quality_score,
            "notes": extracted_text.notes,
            "summary": extracted_text.summary,
            "model_name": extracted_text.model_name,
            "processing_date": extracted_text.processing_date,
            "segments": extracted_text.segments,
            "named_entities": extracted_text.named_entities,
            "dataset": extracted_text.dataset,
            "is_fully_proofread": extracted_text.is_fully_proofread,
            "is_fully_validated": extracted_text.is_fully_validated,
            "skipped": extracted_text.skipped,
            "skip_reason": extracted_text.skip_reason,
            "edit": extracted_text.edit,
            "device_uid": extracted_text.device_uid,
            "extraction_metadata": extracted_text.extraction_metadata,
            "created_at": (
                extracted_text.created_at.isoformat()
                if extracted_text.created_at
                else None
            ),
            "updated_at": (
                extracted_text.updated_at.isoformat()
                if extracted_text.updated_at
                else None
            ),
        }

    def _calculate_field_changes(
        self, old_values: dict[str, Any], new_values: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Calculate field-level changes with new JSONB format."""
        changes = {}

        for field, new_value in new_values.items():
            old_value = old_values.get(field)
            old_serialized = _serialize_value(old_value)
            new_serialized = _serialize_value(new_value)

            if old_serialized != new_serialized:
                changes[field] = {
                    "old": old_serialized,
                    "new": new_serialized,
                    "reason": None,
                }

        for field, old_value in old_values.items():
            if field not in new_values:
                changes[field] = {
                    "old": _serialize_value(old_value),
                    "new": None,
                    "reason": None,
                }

        return changes

    def _should_create_major_snapshot(
        self, version: int, change_type: ChangeType
    ) -> bool:
        """Determine if a major snapshot should be created."""
        if version == 0:
            return False
        return (
            version % self.MAJOR_VERSION_INTERVAL == 0
            or change_type == ChangeType.admin_override
            or version == 1
        )

    def _create_major_snapshot(
        self,
        record: Record,
        version: int,
        created_by: UUID,
        snapshot_type: str = "auto",
    ):
        """Create a major version snapshot."""
        snapshot = RecordMajorSnapshot(
            record_id=record.uid,
            version_number=version,
            full_data=self._create_record_snapshot(record),
            snapshot_type=snapshot_type,
        )
        self.session.add(snapshot)

    def _calculate_diff(
        self, old_snapshot: dict[str, Any], new_snapshot: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate differences between two record snapshots."""
        added = {}
        removed = {}
        changed = {}
        change_types = set()

        for field, new_value in new_snapshot.items():
            if field == "snapshot_timestamp":
                continue

            if field not in old_snapshot:
                added[field] = new_value
                change_types.add("added")
            elif old_snapshot[field] != new_value:
                changed[field] = {
                    "old": old_snapshot[field],
                    "new": new_value,
                    "change_type": "modified",
                }
                change_types.add("modified")

        for field, old_value in old_snapshot.items():
            if field == "snapshot_timestamp":
                continue

            if field not in new_snapshot:
                removed[field] = old_value
                change_types.add("removed")

        return {
            "added": added,
            "removed": removed,
            "changed": changed,
            "total_changes": len(added) + len(removed) + len(changed),
            "change_types": list(change_types),
        }

    def _get_record_snapshot(
        self, history_entry: RecordHistory
    ) -> dict[str, Any]:
        if history_entry.full_snapshot:
            return history_entry.full_snapshot

        prior = self.session.exec(
            select(RecordHistory)
            .where(
                and_(
                    RecordHistory.record_id == history_entry.record_id,
                    RecordHistory.version_number
                    <= history_entry.version_number,
                    RecordHistory.full_snapshot != None,  # noqa: E711
                )
            )
            .order_by(sa_desc(RecordHistory.version_number))  # type: ignore[bad-argument-type]
            .limit(1)
        ).first()

        if not prior or not prior.full_snapshot:
            return {}

        snapshot = dict(prior.full_snapshot)
        intermediate = self.session.exec(
            select(RecordHistory)
            .where(
                and_(
                    RecordHistory.record_id == history_entry.record_id,
                    RecordHistory.version_number > prior.version_number,
                    RecordHistory.version_number
                    <= history_entry.version_number,
                )
            )
            .order_by(sa_asc(RecordHistory.version_number))  # type: ignore[bad-argument-type]
        ).all()

        for entry in intermediate:
            if not entry.field_changes:
                continue
            for field, change in entry.field_changes.items():
                if not isinstance(change, dict):
                    continue
                new_val = change.get("new")
                if new_val is None:
                    snapshot.pop(field, None)
                else:
                    snapshot[field] = new_val

        return snapshot

    def _restore_extracted_text(
        self, record: Record, target_data: dict[str, Any]
    ) -> None:
        """Restore extracted_text from snapshot into the ExtractedText table."""
        et_data = target_data.get("extracted_text")
        if not et_data or not isinstance(et_data, dict) or record.uid is None:
            return

        existing = self.session.exec(
            select(ExtractedText).where(ExtractedText.record_id == record.uid)
        ).first()

        et_fields = (
            "confidence",
            "language",
            "extraction_type",
            "quality_score",
            "notes",
            "summary",
            "model_name",
            "processing_date",
            "segments",
            "named_entities",
            "dataset",
            "is_fully_proofread",
            "is_fully_validated",
            "skipped",
            "skip_reason",
            "edit",
            "device_uid",
            "extraction_metadata",
        )

        if existing:
            for field in et_fields:
                val = et_data.get(field)
                if val is not None:
                    setattr(existing, field, val)
            self.session.add(existing)
        else:
            from app.models.extracted_text import ExtractedText as ETModel

            kwargs = {f: et_data.get(f) for f in et_fields}
            kwargs["record_id"] = record.uid
            kwargs.setdefault("extraction_type", "manual")
            et = ETModel(**kwargs)
            self.session.add(et)

    def _apply_restoration(
        self,
        record: Record,
        target_history: RecordHistory,
        fields_to_restore: list[str] | None,
        restored_by: UUID,
    ):
        """Apply restoration to a record."""
        target_data = self._get_record_snapshot(target_history)

        old_values = self._create_record_snapshot(record)

        _skip_fields = {
            "uid",
            "created_at",
            "updated_at",
            "snapshot_timestamp",
            "extracted_text",
            "user_id",
            "user",
            "reviewed_by",
            "reviewer",
            "device_uid",
            "device",
            "history",
            "version_info",
            "location",
        }

        if fields_to_restore:
            for field in fields_to_restore:
                if field in target_data and field not in _skip_fields:
                    setattr(record, field, target_data[field])
        else:
            for field, value in target_data.items():
                if field not in _skip_fields:
                    setattr(record, field, value)

        self._restore_extracted_text(record, target_data)

        record.updated_at = datetime.now(timezone.utc)

        new_values = self._create_record_snapshot(record)
        if record.uid is None:
            raise ValueError("Record must have a uid to capture record changes")
        self.capture_record_changes(
            record.uid,
            old_values,
            new_values,
            restored_by,
            ChangeSource.admin_action,
            f"Restored to version {target_history.version_number}",
        )

        self.session.add(record)

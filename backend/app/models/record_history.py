"""V2 Record History Models - Optimized Unified History Architecture.

This module implements the optimized V2 history system that replaces
the multi-table V1 architecture with a simplified, high-performance
unified design.

ARCHITECTURE OVERVIEW:
======================

V1 (Old) Issues:
- 5 tables: RecordHistory, RecordFieldHistory, RecordVersion,
  RecordSnapshot, RecordRestore
- High storage duplication (full snapshots per change)
- Complex joins for history queries
- Slow pagination and filtering
- Difficult maintenance

V2 (New) Solutions:
- 3 main tables: RecordHistory, RecordVersion, RecordMajorSnapshot
- Single-table field changes (JSONB)
- Major snapshots only (every 10 versions)
- Optimized indexes for common query patterns
- Simplified maintenance

SCHEMA DESIGN:
==============

record_history_v2:
- uid: UUID (PK)
- record_id: UUID (FK, indexed)
- version_number: int (indexed, unique per record)
- change_type: ChangeType (indexed)
- change_source: ChangeSource (indexed)
- changed_by: UUID (FK, indexed)
- field_changes: JSONB (unified field-level changes)
- full_snapshot: JSONB (nullable, full record state)
- change_reason: VARCHAR(500)
- validation_errors: JSONB
- change_metadata: JSONB
- created_at: TIMESTAMPTZ (indexed)

Indexes:
- PRIMARY KEY (uid)
- UNIQUE (record_id, version_number)
- INDEX (record_id, created_at DESC)
- INDEX (changed_by, created_at DESC)
- INDEX (created_at) for time-range queries

field_changes JSONB format:
{
    "title": {"old": "Old Title", "new": "New Title", "reason": "Correction"},
    "status": {"old": null, "new": "published", "reason": null}
}

record_version_v2:
- Single row per record (unique on record_id)
- current_version, total_changes
- Aggregated counters: user_edits, admin_edits, system_updates
- last_major_version, last_snapshot_at for snapshot tracking

record_major_snapshot:
- Only created for major versions (every 10)
- Stores full record state for efficient diff calculation

COMPATIBILITY:
==============
- V1 tables preserved (not dropped) — safe downgrade by dropping V2 tables only
- V2 unified schema runs alongside V1 tables
- Data migration runs within the alembic upgrade transaction
- Backward compatible with existing API calls (shapes V2 data as V1)
- V1 tables can be manually dropped after stability is confirmed
"""

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import ARRAY, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from .change_enums import ChangeSource, ChangeType

if TYPE_CHECKING:
    from .record import Record
    from .user import User


class RecordHistory(SQLModel, table=True):
    """Unified history table - single source of truth for all record changes.

    Replaces: RecordHistory + RecordFieldHistory (V1)

    Key design decisions:
    - Single table stores both metadata and field-level changes
    - field_changes uses JSONB for efficient storage and querying
    - full_snapshot stored as JSONB but nullable to save space
    - All indexes optimized for common query patterns:
      * record_id + version_number (unique constraint)
      * record_id + created_at (pagination)
      * changed_by + created_at (user activity)
      * created_at index for time-range queries

    Migration from V1:
    - Old RecordHistory.field_changes mapped to new format
    - Old RecordFieldHistory entries merged into field_changes JSONB
    - All existing data preserved during migration
    """

    __tablename__ = "record_history_v2"  # type: ignore[bad-override]

    uid: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)

    record_id: UUID = Field(foreign_key="record.uid", index=True)
    version_number: int = Field(ge=0)

    change_type: ChangeType = Field(index=True)
    change_source: ChangeSource = Field(index=True)
    changed_by: UUID = Field(foreign_key="user.id", index=True)

    field_changes: dict[str, dict[str, Any]] = Field(
        default_factory=dict, sa_type=JSONB
    )
    full_snapshot: dict[str, Any] | None = Field(default=None, sa_type=JSONB)

    change_reason: str | None = Field(default=None, max_length=500)

    validation_errors: dict[str, Any] | None = Field(
        default=None, sa_type=JSONB
    )

    change_metadata: dict[str, Any] | None = Field(default=None, sa_type=JSONB)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )

    record: Optional["Record"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[RecordHistory.record_id]",
            "back_populates": "history",
        }
    )
    changed_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RecordHistory.changed_by]"}
    )

    class Config:  # type: ignore[bad-override]
        """Pydantic model configuration."""

        arbitrary_types_allowed = True


class RecordVersion(SQLModel, table=True):
    """Lightweight version tracking table - quick lookups for version metadata.

    Replaces: RecordVersion (V1)

    Design:
    - One row per record (record_id is the primary key)
    - Aggregated counters eliminate need to count history entries
    - last_major_version + last_snapshot_at track snapshot creation

    Counters (updated atomically with history entries):
    - user_edits: count of user-initiated changes
    - admin_edits: count of admin override changes
    - system_updates: count of system/process changes

    Usage:
    - Quick version info without querying history table
    - Dashboard metrics and analytics
    - Change source breakdown
    """

    __tablename__ = "record_version_v2"  # type: ignore[bad-override]

    uid: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    record_id: UUID = Field(foreign_key="record.uid", unique=True, index=True)

    current_version: int = Field(default=0, ge=0)
    total_changes: int = Field(default=0, ge=0)

    last_changed_by: UUID | None = Field(default=None, foreign_key="user.id")
    last_change_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    user_edits: int = Field(default=0, ge=0)
    admin_edits: int = Field(default=0, ge=0)
    system_updates: int = Field(default=0, ge=0)

    last_major_version: int = Field(default=0, ge=0)
    last_snapshot_at: datetime | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    record: Optional["Record"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[RecordVersion.record_id]",
            "back_populates": "version_info",
        }
    )
    last_changed_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[RecordVersion.last_changed_by]"
        }
    )

    class Config:  # type: ignore[bad-override]
        """Pydantic model configuration."""

        arbitrary_types_allowed = True


class RecordMajorSnapshot(SQLModel, table=True):
    """Major version snapshots - replaces RecordSnapshot."""

    __tablename__ = "record_major_snapshot"  # type: ignore[bad-override]

    uid: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)

    record_id: UUID = Field(foreign_key="record.uid", index=True)
    version_number: int = Field(ge=0)

    full_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSONB)

    snapshot_type: str = Field(max_length=20)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    record: Optional["Record"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[RecordMajorSnapshot.record_id]"
        }
    )

    class Config:  # type: ignore[bad-override]
        """Pydantic model configuration."""

        arbitrary_types_allowed = True


class RecordRestore(SQLModel, table=True):
    """Optimized restore tracking - replaces RecordRestore."""

    __tablename__ = "record_restore_v2"  # type: ignore[bad-override]

    uid: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)

    record_id: UUID = Field(foreign_key="record.uid", index=True)
    restored_from_version: int = Field(ge=0)
    restored_to_version: int = Field(ge=0)

    restored_by: UUID = Field(foreign_key="user.id")
    restore_reason: str = Field(max_length=500)

    restored_fields: list[str] = Field(  # type: ignore[no-matching-overload]
        default_factory=list, sa_type=ARRAY(String)
    )
    partial_restore: bool = Field(default=False)

    requires_approval: bool = Field(default=False)
    approved_by: UUID | None = Field(default=None, foreign_key="user.id")
    approval_status: str = Field(default="pending", max_length=20)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    approved_at: datetime | None = Field(default=None)

    record: Optional["Record"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RecordRestore.record_id]"}
    )
    restored_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RecordRestore.restored_by]"}
    )
    approved_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RecordRestore.approved_by]"}
    )

    class Config:  # type: ignore[bad-override]
        """Pydantic model configuration."""

        arbitrary_types_allowed = True

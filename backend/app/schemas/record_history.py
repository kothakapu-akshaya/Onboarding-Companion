"""Record history schemas."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.record_history import ChangeSource, ChangeType


# Base schemas
class RecordHistoryBase(BaseModel):
    """Record history base schema."""

    record_id: UUID
    version_number: int
    change_type: ChangeType
    change_source: ChangeSource
    changed_by: UUID
    change_reason: str | None = None


class RecordFieldHistoryBase(BaseModel):
    """Record field history base schema."""

    record_id: UUID
    field_name: str
    old_value: str | None = None
    new_value: str | None = None
    change_reason: str | None = None


# Create schemas
class RecordRestoreCreate(BaseModel):
    """Record restore creation schema."""

    target_version: int = Field(..., ge=0, description="Version to restore to")
    restore_reason: str = Field(
        ..., max_length=500, description="Reason for restoration"
    )
    fields_to_restore: list[str] | None = Field(
        None, description="Specific fields to restore (null for full restore)"
    )
    requires_approval: bool = Field(
        False, description="Whether this restore requires admin approval"
    )


# Read schemas
class RecordHistoryRead(RecordHistoryBase):
    """Record history read schema."""

    uid: UUID
    record_snapshot: dict[str, Any]
    field_changes: dict[str, dict[str, Any]]
    change_metadata: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class RecordFieldHistoryRead(RecordFieldHistoryBase):
    """Record field history read schema."""

    uid: UUID
    record_history_id: UUID
    validation_errors: dict[str, Any] | None = None
    validation_warnings: dict[str, Any] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class RecordVersionRead(BaseModel):
    """Record version read schema."""

    uid: UUID
    record_id: UUID
    current_version: int
    total_changes: int
    last_changed_by: UUID | None = None
    last_change_type: ChangeType | None = None
    last_change_source: ChangeSource | None = None
    created_at: datetime
    last_updated: datetime
    user_edit_changes: int
    admin_changes: int
    system_changes: int

    class Config:
        from_attributes = True


class RecordDiffRead(BaseModel):
    """Record diff read schema."""

    record_id: UUID
    from_version: int
    to_version: int
    added_fields: dict[str, Any]
    removed_fields: dict[str, Any]
    changed_fields: dict[str, dict[str, Any]]
    total_changes: int
    change_types: list[str]
    created_at: datetime


class RecordRestoreRead(BaseModel):
    """Record restore read schema."""

    uid: UUID
    record_id: UUID
    restored_from_version: int
    restored_to_version: int
    restored_by: UUID
    restore_reason: str
    restored_fields: list[str]
    partial_restore: bool
    requires_approval: bool
    approved_by: UUID | None = None
    approval_status: str
    created_at: datetime
    approved_at: datetime | None = None

    class Config:
        from_attributes = True


class VersionSummaryRead(BaseModel):
    """Version summary read schema."""

    record_id: UUID
    current_version: int
    total_changes: int
    last_changed: datetime | None = None
    last_changed_by: UUID | None = None
    change_breakdown: dict[str, int]


class RestoreApprovalRead(BaseModel):
    """Restore approval read schema."""

    restore_id: UUID
    approved: bool
    approval_reason: str | None = None


# Streak tracking schemas
class StreakData(BaseModel):
    """Individual streak data."""

    current_streak: int = Field(
        ..., ge=0, description="Current consecutive days"
    )
    current_streak_start: date | None = Field(
        None, description="Start date of current streak"
    )
    current_streak_end: date | None = Field(
        None, description="End date of current streak"
    )
    longest_streak: int = Field(
        ..., ge=0, description="Longest consecutive days achieved"
    )
    longest_streak_start: date | None = Field(
        None, description="Start date of longest streak"
    )
    longest_streak_end: date | None = Field(
        None, description="End date of longest streak"
    )
    total_active_days: int = Field(
        ..., ge=0, description="Total number of active days"
    )
    last_activity_date: date | None = Field(
        None, description="Date of most recent activity"
    )
    first_activity_date: date | None = Field(
        None, description="Date of first activity"
    )


class UserStreaks(BaseModel):
    """Complete streak information for a user."""

    user_id: UUID
    contributions_streak: StreakData = Field(
        ..., description="Streak based on daily contributions"
    )
    edits_streak: StreakData = Field(
        ..., description="Streak based on daily edits"
    )
    combined_streak: StreakData = Field(
        ..., description="Streak based on combined activity"
    )

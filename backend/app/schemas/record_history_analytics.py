"""Analytics schemas for record history."""

from pydantic import BaseModel


class DailyActivityRow(BaseModel):
    """One day's change activity grouped by source."""

    date: str
    source: str
    count: int


class TopChangedRecord(BaseModel):
    """Record with the most changes in the period."""

    record_id: str
    title: str
    total_changes: int


class MostActiveUser(BaseModel):
    """User with the most edits in the period."""

    user_id: str
    name: str
    changes_made: int


class ChangeActivityReport(BaseModel):
    """Full change activity report for a trailing window."""

    period_days: int
    daily_activity: list[DailyActivityRow]
    top_changed_records: list[TopChangedRecord]
    most_active_users: list[MostActiveUser]


class FieldChangeFrequency(BaseModel):
    """How often a single field changed across all records."""

    field_name: str
    change_count: int
    records_affected: int


class FieldChangeReport(BaseModel):
    """Field-level change frequency report."""

    period_days: int
    field_change_frequency: list[FieldChangeFrequency]

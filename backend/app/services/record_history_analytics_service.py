"""Analytics service for record history."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text as sa_text
from sqlmodel import Session

from app.schemas.record_history_analytics import (
    ChangeActivityReport,
    DailyActivityRow,
    FieldChangeFrequency,
    FieldChangeReport,
    MostActiveUser,
    TopChangedRecord,
)

logger = logging.getLogger(__name__)


class RecordHistoryAnalyticsService:
    """Analytics queries for record history data."""

    def __init__(self, session: Session):
        """Initialize with a SQLModel session."""
        self.session = session

    def get_change_activity(self, days: int = 30) -> ChangeActivityReport:
        """Aggregated change activity over a trailing window."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        daily_changes = self.session.execute(
            sa_text("""
                SELECT DATE(created_at) as change_date,
                       change_source,
                       COUNT(*) as change_count
                FROM record_history_v2
                WHERE created_at >= :start_date
                GROUP BY DATE(created_at), change_source
                ORDER BY change_date DESC
            """),
            {"start_date": start_date},
        ).all()

        top_changed = self.session.execute(
            sa_text("""
                SELECT rh.record_id,
                       r.title,
                       COUNT(*) as total_changes
                FROM record_history_v2 rh
                JOIN record r ON rh.record_id = r.uid
                WHERE rh.created_at >= :start_date
                GROUP BY rh.record_id, r.title
                ORDER BY total_changes DESC
                LIMIT 10
            """),
            {"start_date": start_date},
        ).all()

        active_users = self.session.execute(
            sa_text("""
                SELECT rh.changed_by,
                       u.name,
                       COUNT(*) as changes_made
                FROM record_history_v2 rh
                JOIN "user" u ON rh.changed_by = u.id
                WHERE rh.created_at >= :start_date
                GROUP BY rh.changed_by, u.name
                ORDER BY changes_made DESC
                LIMIT 10
            """),
            {"start_date": start_date},
        ).all()

        return ChangeActivityReport(
            period_days=days,
            daily_activity=[
                DailyActivityRow(
                    date=str(row.change_date),
                    source=row.change_source,
                    count=row.change_count,
                )
                for row in daily_changes
            ],
            top_changed_records=[
                TopChangedRecord(
                    record_id=str(row.record_id),
                    title=row.title,
                    total_changes=row.total_changes,
                )
                for row in top_changed
            ],
            most_active_users=[
                MostActiveUser(
                    user_id=str(row.changed_by),
                    name=row.name,
                    changes_made=row.changes_made,
                )
                for row in active_users
            ],
        )

    def get_field_change_analytics(self, days: int = 30) -> FieldChangeReport:
        """Field-level change frequency from V2 JSONB field_changes."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        field_changes = self.session.execute(
            sa_text("""
                SELECT field_name,
                       COUNT(*) as change_count,
                       COUNT(DISTINCT record_id) as records_affected
                FROM record_history_v2,
                     LATERAL jsonb_object_keys(field_changes) AS field_name
                WHERE created_at >= :start_date
                  AND field_changes != '{}'::jsonb
                GROUP BY field_name
                ORDER BY change_count DESC
            """),
            {"start_date": start_date},
        ).all()

        return FieldChangeReport(
            period_days=days,
            field_change_frequency=[
                FieldChangeFrequency(
                    field_name=row.field_name,
                    change_count=row.change_count,
                    records_affected=row.records_affected,
                )
                for row in field_changes
            ],
        )

"""Streak tracking service for calculating daily streaks from existing data."""

import logging
from datetime import date, timedelta
from typing import Any, cast
from uuid import UUID

from sqlmodel import Session, and_, func, select

from app.models.change_enums import ChangeSource
from app.models.record import Record
from app.models.record_history import RecordHistory

logger = logging.getLogger(__name__)


class StreakService:
    """Service for calculating user streaks from existing activity data."""

    def __init__(self, session: Session):
        """Initialize the StreakService."""
        self.session = session

    def get_user_streaks(self, user_id: UUID) -> dict[str, Any]:
        """Get all streak information for a user."""
        contributions_streak = self._calculate_contributions_streak(user_id)
        edits_streak = self._calculate_edits_streak(user_id)
        combined_streak = self._calculate_combined_streak(user_id)

        return {
            "user_id": user_id,
            "contributions_streak": contributions_streak,
            "edits_streak": edits_streak,
            "combined_streak": combined_streak,
        }

    def _calculate_contributions_streak(self, user_id: UUID) -> dict[str, Any]:
        """Calculate streak based on daily contributions (record uploads)."""
        # Get all contribution dates for the user
        statement = (
            select(func.date(Record.created_at))
            .where(Record.user_id == user_id)
            .distinct()
            .order_by(func.date(Record.created_at))
        )
        contribution_dates = list(self.session.exec(statement).all())

        if not contribution_dates:
            return self._empty_streak_data()

        return self._calculate_streak_from_dates(contribution_dates)

    def _calculate_edits_streak(self, user_id: UUID) -> dict[str, Any]:
        """Calculate streak based on daily edits (record history entries)."""
        # Get all edit dates for the user (user-generated changes only)
        statement = (
            select(func.date(RecordHistory.created_at))
            .where(
                and_(
                    RecordHistory.changed_by == user_id,
                    RecordHistory.change_source == ChangeSource.user_edit,
                )
            )
            .distinct()
            .order_by(func.date(RecordHistory.created_at))
        )
        edit_dates = list(self.session.exec(statement).all())

        if not edit_dates:
            return self._empty_streak_data()

        return self._calculate_streak_from_dates(edit_dates)

    def _calculate_combined_streak(self, user_id: UUID) -> dict[str, Any]:
        """Calculate streak based on combined daily contributions and edits."""
        # Get all activity dates (contributions OR edits) for the user
        contributions_subquery = select(
            func.date(Record.created_at).label("activity_date")
        ).where(Record.user_id == user_id)

        edits_subquery = select(
            func.date(RecordHistory.created_at).label("activity_date")
        ).where(
            and_(
                RecordHistory.changed_by == user_id,
                RecordHistory.change_source == ChangeSource.user_edit,
            )
        )

        # Union the two subqueries
        union_query = select(contributions_subquery.c.activity_date).union(
            select(edits_subquery.c.activity_date)
        )

        # Use a subquery to get distinct dates and order them
        subquery = union_query.subquery()
        combined_statement = (
            select(subquery.c.activity_date)
            .distinct()
            .order_by(subquery.c.activity_date)
        )

        activity_dates = list(self.session.exec(combined_statement).all())

        if not activity_dates:
            return self._empty_streak_data()

        return self._calculate_streak_from_dates(activity_dates)

    def _calculate_streak_from_dates(self, dates: list[date]) -> dict[str, Any]:
        """Calculate streak statistics from a list of dates."""
        if not dates:
            return self._empty_streak_data()

        dates = sorted(dates)
        today = date.today()

        # Calculate current streak
        current_streak, current_start, current_end = self._get_current_streak(
            dates, today
        )

        # Calculate longest streak
        longest_streak, longest_start, longest_end = self._get_longest_streak(
            dates
        )

        return {
            "current_streak": current_streak,
            "current_streak_start": current_start,
            "current_streak_end": current_end,
            "longest_streak": longest_streak,
            "longest_streak_start": longest_start,
            "longest_streak_end": longest_end,
            "total_active_days": len(dates),
            "last_activity_date": dates[-1] if dates else None,
            "first_activity_date": dates[0] if dates else None,
        }

    def _get_current_streak(
        self, dates: list[date], today: date
    ) -> tuple[int, date | None, date | None]:
        """Calculate the current active streak."""
        if not dates:
            return 0, None, None

        dates = sorted(dates)

        # Check if there was activity today or yesterday
        # (yesterday counts as current if user hasn't broken the streak yet)
        latest_date = dates[-1]
        days_since_last = (today - latest_date).days

        # If more than 1 day gap, no current streak
        if days_since_last > 1:
            return 0, None, None

        # If activity was today or yesterday, calculate streak backwards
        current_streak = 1
        current_end = latest_date
        current_start = latest_date

        # Go backwards through dates to find consecutive days
        for i in range(len(dates) - 2, -1, -1):
            prev_date = dates[i]
            expected_date = current_start - timedelta(days=1)

            if prev_date == expected_date:
                current_streak += 1
                current_start = prev_date
            else:
                break

        return current_streak, current_start, current_end

    def _get_longest_streak(
        self, dates: list[date]
    ) -> tuple[int, date | None, date | None]:
        """Calculate the longest streak from all dates."""
        if not dates:
            return 0, None, None

        dates = sorted(dates)

        max_streak = 1
        max_start = dates[0]
        max_end = dates[0]

        current_streak = 1
        current_start = dates[0]
        current_end = dates[0]

        for i in range(1, len(dates)):
            current_date = dates[i]
            prev_date = dates[i - 1]

            # Check if dates are consecutive
            if (current_date - prev_date).days == 1:
                current_streak += 1
                current_end = current_date
            else:
                # Check if this was the longest streak
                if current_streak > max_streak:
                    max_streak = current_streak
                    max_start = current_start
                    max_end = current_end

                # Start new streak
                current_streak = 1
                current_start = current_date
                current_end = current_date

        # Check final streak
        if current_streak > max_streak:
            max_streak = current_streak
            max_start = current_start
            max_end = current_end

        return max_streak, max_start, max_end

    def _empty_streak_data(self) -> dict[str, Any]:
        """Return empty streak data structure."""
        return {
            "current_streak": 0,
            "current_streak_start": None,
            "current_streak_end": None,
            "longest_streak": 0,
            "longest_streak_start": None,
            "longest_streak_end": None,
            "total_active_days": 0,
            "last_activity_date": None,
            "first_activity_date": None,
        }

    def get_daily_activity_counts(
        self, user_id: UUID, days: int = 30
    ) -> list[dict[str, Any]]:
        """Get daily activity counts for the last N days."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        # Get contributions by date
        contributions_stmt = (
            select(
                func.date(Record.created_at),
                func.count(cast(Any, Record.uid)),
            )
            .where(
                and_(
                    Record.user_id == user_id,
                    Record.uid is not None,
                    func.date(Record.created_at) >= start_date,
                    func.date(Record.created_at) <= end_date,
                )
            )
            .group_by(func.date(Record.created_at))
        )
        contributions_data = dict(self.session.exec(contributions_stmt).all())

        # Get edits by date
        edits_stmt = (
            select(
                func.date(RecordHistory.created_at),
                func.count(cast(Any, RecordHistory.uid)),
            )
            .where(
                and_(
                    RecordHistory.changed_by == user_id,
                    RecordHistory.uid is not None,
                    RecordHistory.change_source == ChangeSource.user_edit,
                    func.date(RecordHistory.created_at) >= start_date,
                    func.date(RecordHistory.created_at) <= end_date,
                )
            )
            .group_by(func.date(RecordHistory.created_at))
        )
        edits_data = dict(self.session.exec(edits_stmt).all())

        # Build daily activity list
        daily_activities = []
        current_date = start_date

        while current_date <= end_date:
            contributions_count = contributions_data.get(current_date, 0)
            edits_count = edits_data.get(current_date, 0)

            daily_activities.append(
                {
                    "date": current_date.isoformat(),
                    "contributions_count": contributions_count,
                    "edits_count": edits_count,
                    "combined_count": contributions_count + edits_count,
                    "has_activity": (contributions_count + edits_count) > 0,
                }
            )

            current_date += timedelta(days=1)

        return daily_activities

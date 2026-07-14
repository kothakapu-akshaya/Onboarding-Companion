"""Tests for StreakService."""

from datetime import date, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.services.streak_service import StreakService


@pytest.fixture
def mock_session():
    """Create a mock SQLModel session."""
    return Mock()


@pytest.fixture
def streak_service(mock_session):
    """Create a StreakService instance with a mock session."""
    return StreakService(mock_session)


@pytest.fixture
def user_id():
    """Generate a random user ID."""
    return uuid4()


class TestEmptyStreakData:
    """Tests for empty streak data structure."""

    def test_empty_streak_data_structure(self, streak_service):
        """Test empty streak data structure."""
        result = streak_service._empty_streak_data()
        assert result == {
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


class TestCalculateStreakFromDates:
    """Tests for _calculate_streak_from_dates method."""

    def test_empty_dates_returns_empty_streak(self, streak_service):
        """Test that empty dates returns empty streak."""
        result = streak_service._calculate_streak_from_dates([])
        assert result == streak_service._empty_streak_data()

    def test_single_date(self, streak_service):
        """Test single date streak calculation."""
        today = date.today()
        result = streak_service._calculate_streak_from_dates([today])

        assert result["current_streak"] == 1
        assert result["longest_streak"] == 1
        assert result["total_active_days"] == 1
        assert result["first_activity_date"] == today
        assert result["last_activity_date"] == today

    def test_consecutive_dates(self, streak_service):
        """Test consecutive dates streak calculation."""
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(5)]
        result = streak_service._calculate_streak_from_dates(dates)

        assert result["current_streak"] == 5
        assert result["longest_streak"] == 5
        assert result["total_active_days"] == 5

    def test_non_consecutive_dates(self, streak_service):
        """Test non-consecutive dates streak calculation."""
        dates = [
            date.today() - timedelta(days=10),
            date.today() - timedelta(days=5),
            date.today() - timedelta(days=1),
        ]
        result = streak_service._calculate_streak_from_dates(dates)

        assert result["current_streak"] == 1
        assert result["longest_streak"] == 1
        assert result["total_active_days"] == 3

    def test_multiple_streaks(self, streak_service):
        """Test dates with multiple separate streaks."""
        today = date.today()
        dates = [
            today - timedelta(days=10),
            today - timedelta(days=9),
            today - timedelta(days=8),
            today - timedelta(days=2),
            today - timedelta(days=1),
        ]
        result = streak_service._calculate_streak_from_dates(dates)

        # Current streak: 2 (yesterday + 2 days ago,
        # since today has no activity)
        assert result["current_streak"] == 2
        assert result["longest_streak"] == 3
        assert result["total_active_days"] == 5


class TestGetCurrentStreak:
    """Tests for _get_current_streak method."""

    def test_no_dates(self, streak_service):
        """Test get current streak with no dates."""
        result = streak_service._get_current_streak([], date.today())
        assert result == (0, None, None)

    def test_activity_today(self, streak_service):
        """Test get current streak with activity today."""
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(3)]
        length, start, end = streak_service._get_current_streak(dates, today)

        assert length == 3
        assert start == today - timedelta(days=2)
        assert end == today

    def test_activity_yesterday(self, streak_service):
        """Test get current streak with activity yesterday."""
        today = date.today()
        dates = [today - timedelta(days=i) for i in range(1, 4)]
        length, start, end = streak_service._get_current_streak(dates, today)

        assert length == 3
        assert start == today - timedelta(days=3)
        assert end == today - timedelta(days=1)

    def test_streak_broken(self, streak_service):
        """Test when last activity was more than 1 day ago."""
        today = date.today()
        dates = [today - timedelta(days=5), today - timedelta(days=4)]
        length, start, end = streak_service._get_current_streak(dates, today)

        assert length == 0
        assert start is None
        assert end is None


class TestGetLongestStreak:
    """Tests for _get_longest_streak method."""

    def test_no_dates(self, streak_service):
        """Test get longest streak with no dates."""
        result = streak_service._get_longest_streak([])
        assert result == (0, None, None)

    def test_single_date(self, streak_service):
        """Test get longest streak with single date."""
        today = date.today()
        result = streak_service._get_longest_streak([today])
        assert result == (1, today, today)

    def test_all_consecutive(self, streak_service):
        """Test get longest streak with all consecutive dates."""
        today = date.today()
        # range(7) produces 0..6, so dates are today, today-1, ..., today-6
        dates = [today - timedelta(days=i) for i in range(7)]
        length, start, end = streak_service._get_longest_streak(dates)

        assert length == 7
        assert start == today - timedelta(days=6)
        assert end == today

    def test_multiple_streaks_longest_in_middle(self, streak_service):
        """Test longest streak with multiple streaks in the middle."""
        dates = [
            date(2024, 1, 1),
            date(2024, 1, 2),
            date(2024, 1, 10),
            date(2024, 1, 11),
            date(2024, 1, 12),
            date(2024, 1, 13),
            date(2024, 1, 20),
        ]
        length, start, end = streak_service._get_longest_streak(dates)

        assert length == 4
        assert start == date(2024, 1, 10)
        assert end == date(2024, 1, 13)


class TestCalculateContributionsStreak:
    """Tests for _calculate_contributions_streak method."""

    def test_no_contributions(self, streak_service, user_id):
        """Test contributions streak with no contributions."""
        mock_result = Mock()
        mock_result.all.return_value = []
        streak_service.session.exec.return_value = mock_result

        result = streak_service._calculate_contributions_streak(user_id)
        assert result == streak_service._empty_streak_data()

    def test_with_contributions(self, streak_service, user_id):
        """Test contributions streak with contribution data."""
        today = date.today()
        contribution_dates = [today - timedelta(days=i) for i in range(3)]

        mock_result = Mock()
        mock_result.all.return_value = contribution_dates
        streak_service.session.exec.return_value = mock_result

        result = streak_service._calculate_contributions_streak(user_id)

        assert result["current_streak"] == 3
        assert result["total_active_days"] == 3


class TestCalculateEditsStreak:
    """Tests for _calculate_edits_streak method."""

    def test_no_edits(self, streak_service, user_id):
        """Test edits streak with no edits."""
        mock_result = Mock()
        mock_result.all.return_value = []
        streak_service.session.exec.return_value = mock_result

        result = streak_service._calculate_edits_streak(user_id)
        assert result == streak_service._empty_streak_data()

    def test_with_edits(self, streak_service, user_id):
        """Test edits streak with edit data."""
        today = date.today()
        edit_dates = [today - timedelta(days=i) for i in range(5)]

        mock_result = Mock()
        mock_result.all.return_value = edit_dates
        streak_service.session.exec.return_value = mock_result

        result = streak_service._calculate_edits_streak(user_id)

        assert result["current_streak"] == 5
        assert result["total_active_days"] == 5


class TestCalculateCombinedStreak:
    """Tests for _calculate_combined_streak method."""

    @pytest.mark.skip(
        reason="SQLAlchemy 2.0 incompatibility: .distinct() on CompoundSelect"
    )
    def test_no_activity(self, streak_service, user_id):
        """Test combined streak with no activity."""
        mock_empty_result = Mock()
        mock_empty_result.all.return_value = []
        streak_service.session.exec.return_value = mock_empty_result

        result = streak_service._calculate_combined_streak(user_id)
        assert result == streak_service._empty_streak_data()

    @pytest.mark.skip(
        reason="SQLAlchemy 2.0 incompatibility: .distinct() on CompoundSelect"
    )
    def test_with_combined_activity(self, streak_service, user_id):
        """Test combined streak with combined activity data."""
        today = date.today()
        activity_dates = [today - timedelta(days=i) for i in range(4)]

        mock_result = Mock()
        mock_result.all.return_value = activity_dates
        streak_service.session.exec.return_value = mock_result

        result = streak_service._calculate_combined_streak(user_id)

        assert result["current_streak"] == 4
        assert result["total_active_days"] == 4


class TestGetUserStreaks:
    """Tests for get_user_streaks method."""

    @patch.object(StreakService, "_calculate_contributions_streak")
    @patch.object(StreakService, "_calculate_edits_streak")
    @patch.object(StreakService, "_calculate_combined_streak")
    def test_get_user_streaks(
        self,
        mock_combined,
        mock_edits,
        mock_contributions,
        streak_service,
        user_id,
    ):
        """Test get user streaks returns combined data."""
        mock_contributions.return_value = {"current_streak": 3}
        mock_edits.return_value = {"current_streak": 2}
        mock_combined.return_value = {"current_streak": 5}

        result = streak_service.get_user_streaks(user_id)

        assert result["user_id"] == user_id
        assert result["contributions_streak"] == {"current_streak": 3}
        assert result["edits_streak"] == {"current_streak": 2}
        assert result["combined_streak"] == {"current_streak": 5}

        mock_contributions.assert_called_once_with(user_id)
        mock_edits.assert_called_once_with(user_id)
        mock_combined.assert_called_once_with(user_id)


class TestGetDailyActivityCounts:
    """Tests for get_daily_activity_counts method."""

    def test_empty_activity(self, streak_service, user_id):
        """Test daily activity counts with empty activity."""
        mock_result = Mock()
        mock_result.all.return_value = []
        streak_service.session.exec.return_value = mock_result

        result = streak_service.get_daily_activity_counts(user_id, days=7)

        assert len(result) == 7
        for day in result:
            assert day["contributions_count"] == 0
            assert day["edits_count"] == 0
            assert day["combined_count"] == 0
            assert day["has_activity"] is False

    def test_with_activity(self, streak_service, user_id):
        """Test daily activity counts with activity data."""
        today = date.today()
        contributions_data = [(today - timedelta(days=1), 3), (today, 5)]
        edits_data = [(today - timedelta(days=1), 2)]

        call_count = [0]

        def mock_exec(stmt):
            mock_result = Mock()
            call_count[0] += 1
            if call_count[0] == 1:
                mock_result.all.return_value = contributions_data
            else:
                mock_result.all.return_value = edits_data
            return mock_result

        streak_service.session.exec.side_effect = mock_exec

        result = streak_service.get_daily_activity_counts(user_id, days=3)

        assert len(result) == 3
        # Today should have contributions (5) and no edits
        today_activity = result[-1]
        assert today_activity["contributions_count"] == 5
        assert today_activity["has_activity"] is True

    def test_has_activity_flag(self, streak_service, user_id):
        """Test has_activity True when contributions or edits exist."""
        today = date.today()
        contributions_data = [(today, 1)]
        edits_data = []

        call_count = [0]

        def mock_exec(stmt):
            mock_result = Mock()
            call_count[0] += 1
            if call_count[0] == 1:
                mock_result.all.return_value = contributions_data
            else:
                mock_result.all.return_value = edits_data
            return mock_result

        streak_service.session.exec.side_effect = mock_exec

        result = streak_service.get_daily_activity_counts(user_id, days=1)

        assert len(result) == 1
        assert result[0]["has_activity"] is True
        assert result[0]["combined_count"] == 1

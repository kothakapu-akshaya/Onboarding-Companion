"""Tests for app/api/v1/endpoints/points.py - Coverage tests.

These tests cover the points endpoints.
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4


class TestPointsStreakStatus:
    """Tests for the get_streak_status endpoint."""

    def test_streak_active_with_multiplier(self):
        """Test streak status when streak is active and has multiplier."""
        from app.api.v1.endpoints.points import get_streak_status

        mock_user = Mock()
        mock_user.streak_multiplier = 1.5
        mock_user.streak_expires_at = datetime.now(timezone.utc) + timedelta(
            days=5
        )

        result = get_streak_status(current_user=mock_user)

        assert result.streak_multiplier == 1.5
        assert result.streak_expires_at is not None

    def test_streak_expired(self):
        """Test streak status when streak has expired."""
        from app.api.v1.endpoints.points import get_streak_status

        mock_user = Mock()
        mock_user.streak_multiplier = 1.5
        mock_user.streak_expires_at = datetime.now(timezone.utc) - timedelta(
            days=1
        )

        result = get_streak_status(current_user=mock_user)

        assert result.streak_multiplier == 1.0
        assert result.streak_expires_at is None

    def test_no_streak(self):
        """Test streak status when user has no streak."""
        from app.api.v1.endpoints.points import get_streak_status

        mock_user = Mock()
        mock_user.streak_multiplier = 1.0
        mock_user.streak_expires_at = None

        result = get_streak_status(current_user=mock_user)

        assert result.streak_multiplier == 1.0
        assert result.streak_expires_at is None


class TestPointsStatsEndpoint:
    """Simplified tests for get_points_stats endpoint."""

    pass


class TestPointsResponseSchemas:
    """Test that response schemas work correctly."""

    def test_streak_status_response_schema(self):
        """Test StreakStatusResponse can be instantiated."""
        from app.schemas.points import StreakStatusResponse

        response = StreakStatusResponse(
            streak_multiplier=1.5,
            streak_expires_at=None,
        )

        assert response.streak_multiplier == 1.5

    def test_daily_points_schema(self):
        """Test DailyPoints can be instantiated."""
        from app.schemas.points import DailyPoints

        dp = DailyPoints(date=date(2024, 1, 15), points=50.0)

        assert dp.date == date(2024, 1, 15)
        assert dp.points == 50.0

    def test_leaderboard_response_schema(self):
        """Test LeaderboardResponse can be instantiated."""
        from app.schemas.points import LeaderboardResponse

        lr = LeaderboardResponse(
            user_id=str(uuid4()),
            user_name="Test User",
            total_points=100.0,
            rank=1,
        )

        assert lr.rank == 1
        assert lr.total_points == 100.0

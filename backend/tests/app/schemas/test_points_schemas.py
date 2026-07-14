"""Tests for app/schemas/points.py Pydantic models.

Import the module directly to avoid circular imports
via app/schemas/__init__.py.
"""

import os
import sys
from datetime import date, datetime
from importlib.util import module_from_spec, spec_from_file_location

import pytest
from pydantic import ValidationError

# ── Direct module import (bypasses app/schemas/__init__.py circular import) ──
_points_path = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    ),
    "app",
    "schemas",
    "points.py",
)
_spec = spec_from_file_location("points_module", _points_path)
assert _spec is not None, f"Could not find spec for {_points_path}"
assert _spec.loader is not None, f"Loader not found for {_points_path}"
points_module = module_from_spec(_spec)
sys.modules["app.schemas.points"] = points_module
_spec.loader.exec_module(points_module)

DailyPoints = points_module.DailyPoints
PointsStatsResponse = points_module.PointsStatsResponse
StreakStatusResponse = points_module.StreakStatusResponse
LeaderboardResponse = points_module.LeaderboardResponse
CategoryLeaderboardResponse = points_module.CategoryLeaderboardResponse


# ─────────────────────────────────────────────
# DailyPoints
# ─────────────────────────────────────────────


class TestDailyPoints:
    def test_valid_instantiation(self):
        dp = DailyPoints(date=date(2026, 4, 7), points=15.5)
        assert dp.date == date(2026, 4, 7)
        assert dp.points == 15.5

    def test_valid_with_zero_points(self):
        dp = DailyPoints(date=date(2026, 1, 1), points=0)
        assert dp.points == 0.0

    def test_valid_with_negative_points(self):
        dp = DailyPoints(date=date(2026, 1, 1), points=-5.0)
        assert dp.points == -5.0

    def test_valid_with_large_points(self):
        dp = DailyPoints(date=date(2026, 1, 1), points=999999.99)
        assert dp.points == 999999.99

    def test_coerces_int_to_float(self):
        dp = DailyPoints(date=date(2026, 4, 7), points=10)
        assert dp.points == 10.0
        assert isinstance(dp.points, float)

    def test_coerces_date_string(self):
        dp = DailyPoints(date="2026-04-07", points=10.0)
        assert dp.date == date(2026, 4, 7)

    def test_missing_date_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            DailyPoints(points=10.0)
        assert "date" in str(exc_info.value).lower()

    def test_missing_points_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            DailyPoints(date=date(2026, 4, 7))
        assert "points" in str(exc_info.value).lower()

    def test_invalid_date_type_raises(self):
        with pytest.raises(ValidationError):
            DailyPoints(date="not-a-date", points=10.0)

    def test_invalid_points_type_raises(self):
        with pytest.raises(ValidationError):
            DailyPoints(date=date(2026, 4, 7), points="not-a-number")

    def test_model_dump(self):
        dp = DailyPoints(date=date(2026, 4, 7), points=25.0)
        result = dp.model_dump()
        assert result == {"date": date(2026, 4, 7), "points": 25.0}

    def test_extra_fields_ignored_by_default(self):
        dp = DailyPoints(
            date=date(2026, 4, 7), points=10.0, extra_field="value"
        )
        assert dp.date == date(2026, 4, 7)
        assert dp.points == 10.0
        assert not hasattr(dp, "extra_field")


# ─────────────────────────────────────────────
# PointsStatsResponse
# ─────────────────────────────────────────────


class TestPointsStatsResponse:
    def _sample_daily(self):
        return [
            DailyPoints(date=date(2026, 4, 6), points=10.0),
            DailyPoints(date=date(2026, 4, 7), points=20.0),
        ]

    def test_valid_instantiation(self):
        resp = PointsStatsResponse(
            total_points=100.0,
            points_today=25.0,
            daily=self._sample_daily(),
        )
        assert resp.total_points == 100.0
        assert resp.points_today == 25.0
        assert len(resp.daily) == 2

    def test_valid_with_empty_daily_list(self):
        resp = PointsStatsResponse(
            total_points=0.0,
            points_today=0.0,
            daily=[],
        )
        assert resp.daily == []

    def test_coerces_numeric_values(self):
        resp = PointsStatsResponse(
            total_points=100,
            points_today=25,
            daily=[],
        )
        assert resp.total_points == 100.0
        assert resp.points_today == 25.0

    def test_missing_total_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PointsStatsResponse(points_today=10.0, daily=[])
        assert "total_points" in str(exc_info.value).lower()

    def test_missing_points_today_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PointsStatsResponse(total_points=100.0, daily=[])
        assert "points_today" in str(exc_info.value).lower()

    def test_missing_daily_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PointsStatsResponse(total_points=100.0, points_today=10.0)
        assert "daily" in str(exc_info.value).lower()

    def test_invalid_daily_type_raises(self):
        with pytest.raises(ValidationError):
            PointsStatsResponse(
                total_points=100.0,
                points_today=10.0,
                daily=["not-a-daily-points"],
            )

    def test_model_dump(self):
        resp = PointsStatsResponse(
            total_points=100.0,
            points_today=25.0,
            daily=self._sample_daily(),
        )
        result = resp.model_dump()
        assert result["total_points"] == 100.0
        assert result["points_today"] == 25.0
        assert len(result["daily"]) == 2
        assert result["daily"][0]["date"] == date(2026, 4, 6)
        assert result["daily"][0]["points"] == 10.0


# ─────────────────────────────────────────────
# StreakStatusResponse
# ─────────────────────────────────────────────


class TestStreakStatusResponse:
    def test_valid_instantiation_with_expiry(self):
        expires = datetime(2026, 4, 8, 12, 0, 0)
        resp = StreakStatusResponse(
            streak_multiplier=1.5, streak_expires_at=expires
        )
        assert resp.streak_multiplier == 1.5
        assert resp.streak_expires_at == expires

    def test_valid_with_null_expiry(self):
        resp = StreakStatusResponse(
            streak_multiplier=1.0, streak_expires_at=None
        )
        assert resp.streak_multiplier == 1.0
        assert resp.streak_expires_at is None

    def test_valid_with_explicit_none_expiry(self):
        resp = StreakStatusResponse(
            streak_multiplier=2.0, streak_expires_at=None
        )
        assert resp.streak_multiplier == 2.0
        assert resp.streak_expires_at is None

    def test_valid_with_zero_multiplier(self):
        resp = StreakStatusResponse(
            streak_multiplier=0.0, streak_expires_at=None
        )
        assert resp.streak_multiplier == 0.0

    def test_valid_with_negative_multiplier(self):
        resp = StreakStatusResponse(
            streak_multiplier=-1.0, streak_expires_at=None
        )
        assert resp.streak_multiplier == -1.0

    def test_coerces_int_multiplier(self):
        resp = StreakStatusResponse(streak_multiplier=2, streak_expires_at=None)
        assert resp.streak_multiplier == 2.0

    def test_coerces_datetime_string(self):
        resp = StreakStatusResponse(
            streak_multiplier=1.0,
            streak_expires_at="2026-04-08T12:00:00",
        )
        assert resp.streak_expires_at == datetime(2026, 4, 8, 12, 0, 0)

    def test_missing_multiplier_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            StreakStatusResponse()
        assert "streak_multiplier" in str(exc_info.value).lower()

    def test_invalid_multiplier_type_raises(self):
        with pytest.raises(ValidationError):
            StreakStatusResponse(streak_multiplier="not-a-number")

    def test_invalid_datetime_string_raises(self):
        with pytest.raises(ValidationError):
            StreakStatusResponse(
                streak_multiplier=1.0,
                streak_expires_at="not-a-datetime",
            )

    def test_model_dump_with_expiry(self):
        expires = datetime(2026, 4, 8, 12, 0, 0)
        resp = StreakStatusResponse(
            streak_multiplier=1.5, streak_expires_at=expires
        )
        result = resp.model_dump()
        assert result == {
            "streak_multiplier": 1.5,
            "streak_expires_at": expires,
        }

    def test_model_dump_without_expiry(self):
        resp = StreakStatusResponse(
            streak_multiplier=1.0, streak_expires_at=None
        )
        result = resp.model_dump()
        assert result == {"streak_multiplier": 1.0, "streak_expires_at": None}


# ─────────────────────────────────────────────
# LeaderboardResponse
# ─────────────────────────────────────────────


class TestLeaderboardResponse:
    def test_valid_instantiation(self):
        resp = LeaderboardResponse(
            rank=1,
            user_id="user-123",
            user_name="Alice",
            total_points=500.0,
        )
        assert resp.rank == 1
        assert resp.user_id == "user-123"
        assert resp.user_name == "Alice"
        assert resp.total_points == 500.0

    def test_valid_with_zero_rank(self):
        resp = LeaderboardResponse(
            rank=0,
            user_id="user-0",
            user_name="Nobody",
            total_points=0.0,
        )
        assert resp.rank == 0

    def test_valid_with_negative_rank(self):
        resp = LeaderboardResponse(
            rank=-1,
            user_id="user-1",
            user_name="Test",
            total_points=0.0,
        )
        assert resp.rank == -1

    def test_valid_with_empty_username(self):
        resp = LeaderboardResponse(
            rank=1,
            user_id="user-123",
            user_name="",
            total_points=100.0,
        )
        assert resp.user_name == ""

    def test_valid_with_empty_user_id(self):
        resp = LeaderboardResponse(
            rank=1,
            user_id="",
            user_name="Test",
            total_points=100.0,
        )
        assert resp.user_id == ""

    def test_coerces_rank_to_int(self):
        resp = LeaderboardResponse(
            rank=1.0,
            user_id="user-1",
            user_name="Test",
            total_points=100.0,
        )
        assert resp.rank == 1
        assert isinstance(resp.rank, int)

    def test_coerces_points_to_float(self):
        resp = LeaderboardResponse(
            rank=1,
            user_id="user-1",
            user_name="Test",
            total_points=100,
        )
        assert resp.total_points == 100.0

    def test_missing_rank_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardResponse(user_id="u", user_name="n", total_points=0.0)
        assert "rank" in str(exc_info.value).lower()

    def test_missing_user_id_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardResponse(rank=1, user_name="n", total_points=0.0)
        assert "user_id" in str(exc_info.value).lower()

    def test_missing_user_name_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardResponse(rank=1, user_id="u", total_points=0.0)
        assert "user_name" in str(exc_info.value).lower()

    def test_missing_total_points_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            LeaderboardResponse(rank=1, user_id="u", user_name="n")
        assert "total_points" in str(exc_info.value).lower()

    def test_invalid_rank_type_raises(self):
        with pytest.raises(ValidationError):
            LeaderboardResponse(
                rank="not-an-int",
                user_id="u",
                user_name="n",
                total_points=0.0,
            )

    def test_invalid_user_id_type_raises(self):
        with pytest.raises(ValidationError):
            LeaderboardResponse(
                rank=1, user_id=123, user_name="n", total_points=0.0
            )

    def test_invalid_user_name_type_raises(self):
        with pytest.raises(ValidationError):
            LeaderboardResponse(
                rank=1, user_id="u", user_name=123, total_points=0.0
            )

    def test_invalid_total_points_type_raises(self):
        with pytest.raises(ValidationError):
            LeaderboardResponse(
                rank=1, user_id="u", user_name="n", total_points="abc"
            )

    def test_model_dump(self):
        resp = LeaderboardResponse(
            rank=1,
            user_id="user-123",
            user_name="Alice",
            total_points=500.0,
        )
        assert resp.model_dump() == {
            "rank": 1,
            "user_id": "user-123",
            "user_name": "Alice",
            "total_points": 500.0,
        }


# ─────────────────────────────────────────────
# CategoryLeaderboardResponse
# ─────────────────────────────────────────────


class TestCategoryLeaderboardResponse:
    def _sample_leaderboard(self):
        return [
            LeaderboardResponse(
                rank=1,
                user_id="u1",
                user_name="Alice",
                total_points=500.0,
            ),
            LeaderboardResponse(
                rank=2,
                user_id="u2",
                user_name="Bob",
                total_points=400.0,
            ),
        ]

    def test_valid_instantiation(self):
        lb = self._sample_leaderboard()
        resp = CategoryLeaderboardResponse(
            leaderboard=lb,
            current_user_rank=lb[1],
        )
        assert len(resp.leaderboard) == 2
        assert resp.current_user_rank.user_id == "u2"

    def test_valid_with_empty_leaderboard(self):
        resp = CategoryLeaderboardResponse(leaderboard=[])
        assert resp.leaderboard == []
        assert resp.current_user_rank is None

    def test_valid_omitting_current_user_rank(self):
        resp = CategoryLeaderboardResponse(
            leaderboard=self._sample_leaderboard()
        )
        assert resp.current_user_rank is None

    def test_valid_with_none_current_user_rank(self):
        resp = CategoryLeaderboardResponse(
            leaderboard=self._sample_leaderboard(),
            current_user_rank=None,
        )
        assert resp.current_user_rank is None

    def test_valid_with_single_entry(self):
        resp = CategoryLeaderboardResponse(
            leaderboard=[
                LeaderboardResponse(
                    rank=1,
                    user_id="u1",
                    user_name="Solo",
                    total_points=100.0,
                ),
            ],
        )
        assert len(resp.leaderboard) == 1

    def test_missing_leaderboard_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            CategoryLeaderboardResponse()
        assert "leaderboard" in str(exc_info.value).lower()

    def test_invalid_leaderboard_type_raises(self):
        with pytest.raises(ValidationError):
            CategoryLeaderboardResponse(leaderboard="not-a-list")

    def test_invalid_leaderboard_entry_type_raises(self):
        with pytest.raises(ValidationError):
            CategoryLeaderboardResponse(
                leaderboard=["not-a-leaderboard-response"]
            )

    def test_invalid_current_user_rank_type_raises(self):
        with pytest.raises(ValidationError):
            CategoryLeaderboardResponse(
                leaderboard=[],
                current_user_rank="not-a-leaderboard-response",
            )

    def test_model_dump_full(self):
        lb = self._sample_leaderboard()
        resp = CategoryLeaderboardResponse(
            leaderboard=lb,
            current_user_rank=lb[0],
        )
        result = resp.model_dump()
        assert len(result["leaderboard"]) == 2
        assert result["leaderboard"][0]["rank"] == 1
        assert result["leaderboard"][0]["user_name"] == "Alice"
        assert result["current_user_rank"]["rank"] == 1

    def test_model_dump_without_current_user_rank(self):
        resp = CategoryLeaderboardResponse(leaderboard=[])
        result = resp.model_dump()
        assert result["leaderboard"] == []
        assert result["current_user_rank"] is None

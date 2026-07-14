from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.points import (
    get_current_month_bounds,
    get_leaderboard,
    get_points_stats,
    get_previous_month_bounds,
    get_streak_status,
    utc_day_bounds,
)


def first_result(value):
    return SimpleNamespace(first=lambda: value)


def all_result(rows):
    return SimpleNamespace(all=lambda: rows)


def test_month_and_day_bounds_are_timezone_aware():
    prev_start, prev_end = get_previous_month_bounds()
    current_start, current_now = get_current_month_bounds()
    day_start, day_end = utc_day_bounds(
        datetime(2024, 1, 15, 12, 30, tzinfo=timezone.utc)
    )

    assert prev_start.tzinfo == timezone.utc
    assert prev_end.tzinfo == timezone.utc
    assert current_start.tzinfo == timezone.utc
    assert current_now.tzinfo == timezone.utc
    assert day_start.hour == 0
    assert day_end - day_start == timedelta(days=1)


def test_streak_status_variants():
    active_user = Mock(
        streak_multiplier=1.75,
        streak_expires_at=datetime.now() + timedelta(days=2),
    )
    expired_user = Mock(
        streak_multiplier=1.75,
        streak_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    no_streak_user = Mock(streak_multiplier=1.0, streak_expires_at=None)

    active = get_streak_status(active_user)
    expired = get_streak_status(expired_user)
    none = get_streak_status(no_streak_user)

    assert active.streak_multiplier == 1.75
    assert expired.streak_multiplier == 1.0
    assert none.streak_expires_at is None


def test_get_points_stats_by_uuid_and_username():
    target_user = Mock(id=uuid4(), username="target")
    session = Mock()
    session.get.return_value = target_user
    session.exec.side_effect = [
        first_result(105.0),
        first_result(10.0),
        all_result([(datetime(2024, 1, 1, tzinfo=timezone.utc), 5.0)]),
    ]

    stats = get_points_stats(str(target_user.id), session, target_user)
    assert stats.total_points == 105.0
    assert stats.points_today == 10.0
    assert len(stats.daily) == 366

    username_user = Mock(id=uuid4(), username="username-user")
    session = Mock()
    session.exec.side_effect = [
        first_result(username_user),
        first_result(50.0),
        first_result(3.0),
        all_result([(datetime(2024, 1, 1, tzinfo=timezone.utc), 2.0)]),
    ]
    stats = get_points_stats("username-user", session, username_user)
    assert stats.total_points == 50.0
    assert stats.points_today == 3.0


def test_get_points_stats_not_found():
    session = Mock()
    session.exec.return_value = first_result(None)

    with pytest.raises(HTTPException) as exc_info:
        get_points_stats(
            "missing-user", session, Mock(id=uuid4(), username="x")
        )

    assert exc_info.value.status_code == 404


def test_category_and_global_leaderboards():
    current_user = Mock(id=uuid4(), name="Current User")
    other_user = Mock(id=uuid4(), name="Other User")
    session = Mock()
    session.exec.side_effect = [
        all_result(
            [
                SimpleNamespace(
                    user_id=other_user.id,
                    user_name="Other User",
                    total_points=25,
                    rank=1,
                )
            ]
        ),
        first_result(
            SimpleNamespace(
                user_id=current_user.id,
                user_name="Current User",
                total_points=15,
                rank=2,
            )
        ),
        all_result(
            [
                SimpleNamespace(
                    user_id=current_user.id,
                    user_name="Current User",
                    total_points=30,
                    rank=1,
                )
            ]
        ),
    ]

    category = get_leaderboard(session, current_user, category_id="cat-1")
    assert category.leaderboard[0].user_name == "Other User"
    assert category.current_user_rank.user_name == "Current User"

    global_board = get_leaderboard(session, current_user)
    assert global_board.leaderboard[0].rank == 1

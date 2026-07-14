import json
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlmodel import col, select

from app.core.rbac_fastapi import require_any_role
from app.db.session import SessionDep
from app.models.points import PointsEvent
from app.models.record import Record
from app.models.user import User
from app.schemas.points import (
    CategoryLeaderboardResponse,
    DailyPoints,
    LeaderboardResponse,
    PointsStatsResponse,
    StreakStatusResponse,
)

router = APIRouter()


def get_previous_month_bounds():
    """Returns the start and end datetimes for the previous full month."""
    today = date.today()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    first_day_of_previous_month = last_day_of_previous_month.replace(day=1)

    start_utc = datetime(
        first_day_of_previous_month.year,
        first_day_of_previous_month.month,
        first_day_of_previous_month.day,
        0,
        0,
        0,
        tzinfo=timezone.utc,
    )
    end_utc = datetime(
        last_day_of_previous_month.year,
        last_day_of_previous_month.month,
        last_day_of_previous_month.day,
        23,
        59,
        59,
        999999,
        tzinfo=timezone.utc,
    )
    return start_utc, end_utc


def get_current_month_bounds():
    """Return start of current month and current UTC datetime."""
    now_utc = datetime.now(timezone.utc)
    first_day_of_current_month = now_utc.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return first_day_of_current_month, now_utc


def utc_day_bounds(dt: datetime | None = None):
    """Return UTC start and end datetimes for a given day."""
    now = dt or datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


@router.get("/streak", response_model=StreakStatusResponse)
def get_streak_status(current_user: User = Depends(require_any_role())):
    """Get the current user's streak status."""
    now = datetime.now(timezone.utc)
    multiplier = 1.0
    expires_at = current_user.streak_expires_at

    # Check if there is an active streak
    if expires_at:
        # Ensure the datetime from the DB is timezone-aware before comparing
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at > now:
            multiplier = current_user.streak_multiplier
        else:
            # If the streak is expired, the effective multiplier is 1.0
            # and there is no expiration date to show.
            expires_at = None
            multiplier = 1.0

    return StreakStatusResponse(
        streak_multiplier=multiplier,
        streak_expires_at=expires_at,
    )


@router.get("/leaderboard", response_model=CategoryLeaderboardResponse)
def get_leaderboard(
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
    category_id: Annotated[
        str | None,
        Query(
            description=(
                "Filter by category ID for category-specific leaderboard"
            )
        ),
    ] = None,
):
    """Get the top 10 contributors for the current month.

    Use `category_id` for a category leaderboard.
    Leave it empty for the global leaderboard.
    Also returns the current user's rank when they are outside the top 10.
    """
    start_date, end_date = get_current_month_bounds()

    # Base subquery to rank all users by points in the current month
    query = select(
        col(User.id).label("user_id"),
        col(User.name).label("user_name"),
        func.sum(col(PointsEvent.points)).label("total_points"),
        func.rank()
        .over(order_by=func.sum(col(PointsEvent.points)).desc())
        .label("rank"),
    ).join(PointsEvent, col(User.id) == col(PointsEvent.user_id))

    # Add category filter if specified
    if category_id:
        query = query.join(
            Record, col(PointsEvent.record_uid) == col(Record.uid)
        )
        query = query.where(text("category_ids @> :category_id::jsonb")).params(
            category_id=json.dumps([category_id])
        )

    query = query.where(
        col(PointsEvent.created_at) >= start_date,
        col(PointsEvent.created_at) <= end_date,
    )
    query = query.group_by(col(User.id), col(User.name)).subquery("all_ranks")

    # Query for the top 10
    top_10_stmt = (
        select(
            query.c.user_id,
            query.c.user_name,
            query.c.total_points,
            query.c.rank,
        )
        .where(query.c.rank <= 10)
        .order_by(query.c.rank)
    )
    top_10_results = session.exec(top_10_stmt).all()

    top_10_leaderboard = [
        LeaderboardResponse(
            user_id=str(res.user_id),  # type: ignore[missing-attribute]
            user_name=res.user_name,  # type: ignore[missing-attribute]
            total_points=float(res.total_points),  # type: ignore[missing-attribute]
            rank=res.rank,  # type: ignore[missing-attribute]
        )
        for res in top_10_results
    ]

    current_user_rank_entry = None
    user_in_top_10 = any(
        str(entry.user_id) == str(current_user.id)
        for entry in top_10_leaderboard
    )

    if not user_in_top_10:
        user_rank_stmt = select(
            query.c.user_id,
            query.c.user_name,
            query.c.total_points,
            query.c.rank,
        ).where(query.c.user_id == current_user.id)
        user_rank_result = session.exec(user_rank_stmt).first()
        if user_rank_result:
            current_user_rank_entry = LeaderboardResponse(
                user_id=str(user_rank_result.user_id),  # type: ignore[missing-attribute]
                user_name=user_rank_result.user_name,  # type: ignore[missing-attribute]
                total_points=float(user_rank_result.total_points),  # type: ignore[missing-attribute]
                rank=user_rank_result.rank,  # type: ignore[missing-attribute]
            )

    return CategoryLeaderboardResponse(
        leaderboard=top_10_leaderboard,
        current_user_rank=current_user_rank_entry,
    )


@router.get("/stats/{user_identifier}", response_model=PointsStatsResponse)
def get_points_stats(
    user_identifier: str,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
):
    """Get a user's points stats (heatmap data).

    Args:
        user_identifier: Either a UUID (user_id) or a username string.
        session: Database session.
        current_user: The authenticated user.
    """
    from uuid import UUID

    from fastapi import HTTPException

    target_user = None

    # Try to parse as UUID first
    try:
        user_uuid = UUID(user_identifier)
        target_user = session.get(User, user_uuid)
    except ValueError:
        # Not a valid UUID, try to find by username
        stmt = select(User).where(User.username == user_identifier)
        target_user = session.exec(stmt).first()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now(timezone.utc)
    # Fetch data for the last 365 days for a full year view
    start_365 = (now - timedelta(days=365)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_stmt = select(func.coalesce(func.sum(PointsEvent.points), 0)).where(
        PointsEvent.user_id == target_user.id
    )
    total_points_result = session.exec(total_stmt).first()
    total_points = float(total_points_result or 0)

    start_today, end_today = utc_day_bounds()
    today_stmt = select(func.coalesce(func.sum(PointsEvent.points), 0)).where(
        PointsEvent.user_id == target_user.id,
        PointsEvent.created_at >= start_today,
        PointsEvent.created_at < end_today,
    )
    points_today_result = session.exec(today_stmt).first()
    points_today = float(points_today_result or 0)

    daily_stmt = (
        select(
            func.date_trunc("day", PointsEvent.created_at).label("day"),
            func.coalesce(func.sum(PointsEvent.points), 0).label("points"),
        )
        .where(
            PointsEvent.user_id == target_user.id,
            PointsEvent.created_at >= start_365,  # Use the new start date
            PointsEvent.created_at <= now,
        )
        .group_by("day")
        .order_by("day")
    )
    rows = session.exec(daily_stmt).all()
    by_day: dict[date, float] = {row[0].date(): float(row[1]) for row in rows}

    daily: list[DailyPoints] = []
    # Loop for a full year (366 days to be safe for leap years)
    for i in range(366):
        d = (start_365 + timedelta(days=i)).date()
        daily.append(DailyPoints(date=d, points=by_day.get(d, 0)))

    return PointsStatsResponse(
        total_points=total_points, points_today=points_today, daily=daily
    )

"""Points system schemas."""

from datetime import date, datetime

from pydantic import BaseModel


class DailyPoints(BaseModel):
    """Daily points response schema."""

    date: date
    points: float


class PointsStatsResponse(BaseModel):
    """Points statistics response schema."""

    total_points: float
    points_today: float
    daily: list[DailyPoints]


class StreakStatusResponse(BaseModel):
    """Streak status response schema."""

    streak_multiplier: float
    streak_expires_at: datetime | None


class LeaderboardResponse(BaseModel):
    """Leaderboard response schema."""

    rank: int
    user_id: str
    user_name: str
    total_points: float


class CategoryLeaderboardResponse(BaseModel):
    """Category leaderboard response schema."""

    leaderboard: list[LeaderboardResponse]
    current_user_rank: LeaderboardResponse | None = None

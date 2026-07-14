"""Versioned API router registration."""

# app/api/v1/api.py
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    categories,
    devices,
    events,
    institutions,
    languages,
    location,
    points,
    record_history,
    records,
    roles,
    tasks,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(
    categories.router, prefix="/categories", tags=["categories"]
)
api_router.include_router(
    languages.router, prefix="/languages", tags=["languages"]
)
api_router.include_router(records.router, prefix="/records", tags=["records"])
api_router.include_router(
    record_history.router, prefix="/history", tags=["record-history"]
)
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(points.router, prefix="/points", tags=["points"])
api_router.include_router(
    location.router, prefix="/location", tags=["location"]
)
api_router.include_router(
    institutions.router, prefix="/institutions", tags=["institutions"]
)
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])

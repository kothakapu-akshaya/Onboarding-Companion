"""Schemas for admin-managed events."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import RecordReviewFilters


class EventCreate(BaseModel):
    """Payload for creating a new Event."""

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    page_context: str = Field(..., min_length=1, max_length=100)
    filters: RecordReviewFilters | None = None
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of records to return when the event is used",
    )
    is_active: bool = True
    start_date: datetime | None = None
    end_date: datetime | None = None


class EventUpdate(BaseModel):
    """Payload for partially updating an Event."""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    page_context: str | None = Field(None, min_length=1, max_length=100)
    filters: RecordReviewFilters | None = None
    limit: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Number of records to return when the event is used",
    )
    is_active: bool | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class EventRead(BaseModel):
    """Full representation of an Event returned to callers."""

    uid: UUID
    name: str
    description: str | None = None
    page_context: str
    filters: dict[str, Any] | None = None
    limit: int
    is_active: bool
    start_date: datetime | None = None
    end_date: datetime | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

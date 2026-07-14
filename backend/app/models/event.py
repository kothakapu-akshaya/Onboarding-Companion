import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class Event(SQLModel, table=True):
    """An admin-defined event that carries filter presets for a page."""

    uid: UUID | None = Field(
        default_factory=uuid_pkg.uuid4,
        primary_key=True,
    )

    name: str = Field(max_length=200, index=True)
    description: str | None = Field(default=None, max_length=1000)

    # Identifies which client page this event applies to.
    page_context: str = Field(max_length=100, index=True)

    # JSONB filter bag mirroring RecordReviewFilters.
    filters: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB),
    )
    limit: int = Field(default=20)

    is_active: bool = Field(default=True, index=True)

    start_date: datetime | None = Field(default=None)
    end_date: datetime | None = Field(default=None)

    created_by: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    creator: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Event.created_by]"}
    )

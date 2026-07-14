"""Persistent language registry model."""

import uuid as uuid_pkg
from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Field, SQLModel


class LanguageEntry(SQLModel, table=True):
    """Language registry entry used for service-level validation."""

    __tablename__ = "language"  # type: ignore[bad-override]

    id: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    code: str | None = Field(
        default=None,
        max_length=10,
        unique=True,
        index=True,
        description="BCP47/ISO 639 language code, e.g. 'te', 'hi', 'en'",
    )
    spoken_population: int | None = Field(default=None)
    geo_area: str | None = Field(default=None, max_length=500)
    created_by: UUID | None = Field(default=None, foreign_key="user.id")
    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

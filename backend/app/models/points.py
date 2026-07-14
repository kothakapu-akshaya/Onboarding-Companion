from __future__ import annotations

import uuid as uuid_pkg
from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Field, SQLModel


class PointsEvent(SQLModel, table=True):
    """Points event model."""

    id: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True, nullable=False)
    record_uid: UUID | None = Field(
        default=None, foreign_key="record.uid", unique=True
    )
    points: float = Field(default=1, ge=0)
    reason: str = Field(default="record_created", max_length=50)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )

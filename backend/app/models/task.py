import uuid as uuid_pkg
from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Field, SQLModel


class Task(SQLModel, table=True):
    """
    Employee onboarding task model.
    """

    id: UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)

    title: str = Field(max_length=200)

    description: str | None = Field(default=None, max_length=500)

    status: str = Field(default="Pending", max_length=50)

    assigned_to: UUID = Field(foreign_key="user.id")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

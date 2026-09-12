"""Database models for the onboarding service.

These tables store per-user onboarding task progress and the metadata of
evidence images uploaded as proof of completion. They deliberately do not
carry foreign keys to the corpus ``user`` table: the onboarding service is
expected to run against its own isolated database and identifies users by
the UUID embedded in their corpus JWT.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc)


class OnboardingProgress(SQLModel, table=True):
    """Per-user completion state for a single onboarding task."""

    __tablename__ = "onboarding_progress"  # type: ignore[bad-override]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True, nullable=False)
    task_key: str = Field(max_length=16, nullable=False)
    status: str = Field(default="pending", max_length=16, nullable=False)
    notes: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "task_key",
            name="uq_onboarding_progress_user_id_task_key",
        ),
    )


class OnboardingEvidence(SQLModel, table=True):
    """Metadata for one evidence image uploaded for an onboarding task."""

    __tablename__ = "onboarding_evidence"  # type: ignore[bad-override]

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(index=True, nullable=False)
    task_key: str = Field(index=True, max_length=16, nullable=False)
    object_key: str = Field(unique=True, max_length=512, nullable=False)
    file_name: str = Field(max_length=255, nullable=False)
    mime_type: str = Field(max_length=100, nullable=False)
    file_size: int = Field(nullable=False)
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)

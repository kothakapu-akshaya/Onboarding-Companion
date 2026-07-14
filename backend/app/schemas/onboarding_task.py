from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel


class OnboardingTaskCreate(SQLModel):
    title: str
    description: str | None = None
    assigned_to: UUID


class OnboardingTaskUpdate(SQLModel):
    status: str | None = None


class OnboardingTaskRead(SQLModel):
    id: UUID
    title: str
    description: str | None
    status: str
    assigned_to: UUID
    created_at: datetime
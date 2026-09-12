"""Request and response schemas for the onboarding API."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ProgressStatus = Literal["pending", "in_progress", "completed"]


class OnboardingProgressUpdate(BaseModel):
    """Request body for creating or updating onboarding progress."""

    status: ProgressStatus
    notes: str | None = None


class OnboardingProgressRead(BaseModel):
    """Progress row for one onboarding task."""

    id: UUID
    user_id: UUID
    task_key: str
    status: ProgressStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class OnboardingEvidenceRead(BaseModel):
    """Evidence metadata row for an onboarding task."""

    id: UUID
    user_id: UUID
    task_key: str
    object_key: str
    file_name: str
    mime_type: str
    file_size: int
    created_at: datetime


class OnboardingEvidenceUrl(BaseModel):
    """Temporary access URL for one onboarding evidence image."""

    evidence_url: str
    expires_minutes: int

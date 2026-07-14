import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .device import Device
    from .record import Record


class ExtractedText(SQLModel, table=True):
    """Extracted text model."""

    uid: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)

    record_id: UUID = Field(foreign_key="record.uid", unique=True, index=True)

    # Device whose volunteer-compute work produced this extraction
    device_uid: UUID | None = Field(
        default=None, foreign_key="device.uid", index=True
    )

    confidence: float | None = Field(default=None)
    language: str | None = Field(default=None, max_length=50)
    extraction_type: str = Field(max_length=20, index=True)

    is_fully_proofread: bool | None = Field(default=False, index=True)
    is_fully_validated: bool | None = Field(default=False, index=True)

    quality_score: float | None = Field(default=None)
    notes: str | None = Field(default=None, sa_column=Column(Text))
    summary: str | None = Field(default=None, sa_column=Column(Text))
    model_name: str | None = Field(default=None, max_length=100)
    processing_date: str | None = Field(default=None, max_length=100)

    segments: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Segmented text with timing/position information",
    )

    named_entities: list[dict[str, str]] | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Named entities in the document",
    )

    dataset: str | None = Field(default=None, max_length=50)

    # Text metrics computed from segments (set server-side on POST/PATCH)
    word_count: int | None = Field(default=None, ge=0)
    sentence_count: int | None = Field(default=None, ge=0)
    character_count: int | None = Field(default=None, ge=0)

    skipped: bool | None = Field(default=False)
    skip_reason: str | None = Field(default=None, max_length=50)
    edit: list[str] | None = Field(
        default=None,
        sa_column=Column(JSONB),
    )

    extraction_metadata: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Additional extraction-specific metadata",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    record: Optional["Record"] = Relationship(back_populates="extracted_text")
    device: Optional["Device"] = Relationship(back_populates="extracted_texts")

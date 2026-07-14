import enum
import uuid as uuid_pkg
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .device import Device
    from .extracted_text import ExtractedText
    from .record_history import RecordHistory, RecordVersion
    from .user import User


class MediaType(str, enum.Enum):
    """Media type enum."""

    text = "text"
    audio = "audio"
    video = "video"
    image = "image"
    document = "document"


class ReleaseRights(str, enum.Enum):
    """Release rights enum."""

    creator = "creator"
    others = "others"
    downloaded = "downloaded"
    NA = "NA"


class Record(SQLModel, table=True):
    """Record model."""

    uid: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)

    # Main content fields
    title: str = Field(max_length=200)
    description: str = Field(min_length=32, max_length=1000)

    # Media and file info
    media_type: MediaType = Field(index=True)
    file_url: str | None = Field(default=None, max_length=500)
    file_name: str | None = Field(default=None, max_length=255)
    file_size: int | None = Field(default=None)
    file_hash: str | None = Field(default=None, max_length=255)
    snr_frequency: float | None = Field(default=None)
    speech_not_detected: bool = Field(
        default=False,
        description="Flag indicating audio/video file is corrupt, has no "
        "audio track, or otherwise cannot be transcribed",
    )

    status: str = Field(
        default="pending", max_length=20
    )  # pending/uploaded/failed

    release_rights: ReleaseRights = Field(default=ReleaseRights.NA)
    creator: str | None = Field(default=None, max_length=200)
    published_date: date | None = Field(
        default=None, description="Published/event date of the record content"
    )

    language: str = Field(default="und", max_length=100)

    # Location data using PostGIS Point geometry
    # SRID 4326 is WGS84 (latitude/longitude coordinates)
    # Using Any type to handle WKBElement from PostGIS
    location: Any | None = Field(
        default=None, sa_column=Column(Geometry("POINT", srid=4326))
    )

    # Foreign keys
    user_id: UUID = Field(foreign_key="user.id")
    reviewed: bool = Field(default=False)
    reviewed_by: UUID | None = Field(default=None, foreign_key="user.id")

    # Device this record was contributed from, if known
    device_uid: UUID | None = Field(
        default=None, foreign_key="device.uid", index=True
    )

    # Store multiple category IDs as JSON array - enables many-to-many
    # relationship without junction table
    category_ids: list[UUID] | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Array of category IDs associated with this record",
    )

    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: datetime | None = Field(default=None)

    # Relationships - explicitly specify foreign keys to avoid ambiguity
    user: Optional["User"] = Relationship(
        back_populates="records",
        sa_relationship_kwargs={"foreign_keys": "[Record.user_id]"},
    )
    reviewer: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Record.reviewed_by]"}
    )

    # Device this record was contributed from
    device: Optional["Device"] = Relationship(back_populates="records")

    # History and versioning relationships (V2)
    history: list["RecordHistory"] = Relationship(back_populates="record")
    version_info: Optional["RecordVersion"] = Relationship(
        back_populates="record"
    )

    # Duration in seconds (auto-calculated, read-only)
    duration_seconds: int | None = Field(default=None, ge=0)

    # Page count for document records (backfilled asynchronously)
    page_count: int | None = Field(default=None, ge=1)

    # Text metrics (word_count, sentence_count, character_count) are stored
    # on the ExtractedText model, not on Record.

    # Tag fields
    tagged_usernames: list[str] | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Array of usernames tagged in this record",
    )
    hashtags: list[str] | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Array of hashtags (clean, without # prefix)",
    )
    record_tags: list[str] | None = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Array of admin-managed record tags",
    )

    # Source information fields
    source_label: str | None = Field(
        default=None,
        max_length=200,
        description="Label for the source of the record",
    )
    source_url: str | None = Field(
        default=None,
        max_length=500,
        description="URL for the source of the record",
    )

    # Extracted text relationship - linked to dedicated table
    extracted_text: Optional["ExtractedText"] = Relationship(
        back_populates="record", sa_relationship_kwargs={"uselist": False}
    )

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Handle PostGIS geometry serialization in model dump."""
        # Get the base model dump
        data = super().model_dump(**kwargs)

        # Remove the location field to avoid WKBElement serialization issues
        # The location field will be handled separately in the API endpoints
        data.pop("location", None)

        return data

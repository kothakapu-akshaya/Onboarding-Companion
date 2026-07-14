# app/models/user.py
import uuid as uuid_pkg
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.schemas import (
    FieldPrivacy,
    Gender,
)

if TYPE_CHECKING:
    from .institution import Institution
    from .record import Record
    from .user_device import UserDevice
    from .user_follow import UserFollow


class User(SQLModel, table=True):
    """User model."""

    id: UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    phone: str = Field(max_length=20, unique=True, index=True)
    username: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=100)
    email: str | None = Field(
        default=None, max_length=100, unique=True, index=True
    )
    gender: Gender | None = Field(default=None)
    date_of_birth: date | None = Field(default=None)
    current_place: str | None = Field(default=None, max_length=100)
    profile_picture_path: str | None = Field(default=None, max_length=255)
    short_bio: str | None = Field(default=None, max_length=500)
    profession: str | None = Field(default=None, max_length=200)
    organisation: str | None = Field(default=None, max_length=200)

    # JSONB fields for storing complex data structures
    places_lived: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    from_place: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )

    # Social media profiles (JSON array of {platform, url} objects)
    social_media_profiles: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )

    # Language proficiency (JSON object mapping language to proficiency level)
    language_proficiencies: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )  # JSON object

    # Internship-specific profile fields
    rural_area_access: str | None = Field(default=None, max_length=500)
    permanent_postal_address: str | None = Field(default=None, max_length=500)
    institution_id: UUID | None = Field(
        default=None, foreign_key="institution.id"
    )
    current_year_of_study: str | None = Field(default=None, max_length=50)
    college_roll_number: str | None = Field(default=None, max_length=100)
    task_registered_id: str | None = Field(default=None, max_length=100)
    resume_record_id: UUID | None = Field(
        default=None, foreign_key="record.uid"
    )
    hardware_details: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    has_completed_ai_courses: str | None = Field(default=None, max_length=50)
    ai_courses_list: str | None = Field(default=None, max_length=1000)

    # Privacy settings for profile fields
    phone_privacy: FieldPrivacy = Field(default=FieldPrivacy.private)
    email_privacy: FieldPrivacy = Field(default=FieldPrivacy.private)

    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    last_login_at: datetime | None = Field(default=None)

    # Consent tracking
    has_given_consent: bool = Field(default=False)
    is_intern: bool = Field(default=False)

    streak_multiplier: float = Field(default=1.0)
    streak_expires_at: datetime | None = Field(default=None)
    credits: float = Field(default=0.0)

    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    # Many-to-many relationship with roles
    # (will be defined after UserRoleLink import)

    # One-to-many relationship with records (as creator)
    records: list["Record"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[Record.user_id]"},
    )

    # One-to-many relationship with records (as reviewer)
    reviewed_records: list["Record"] = Relationship(
        back_populates="reviewer",
        sa_relationship_kwargs={"foreign_keys": "[Record.reviewed_by]"},
    )

    # Following relationships (users this user is following)
    following_relationships: list["UserFollow"] = Relationship(
        back_populates="follower",
        sa_relationship_kwargs={"foreign_keys": "[UserFollow.follower_id]"},
    )

    # Follower relationships (users following this user)
    follower_relationships: list["UserFollow"] = Relationship(
        back_populates="following",
        sa_relationship_kwargs={"foreign_keys": "[UserFollow.following_id]"},
    )

    # Institution relationship
    institution: Optional["Institution"] = Relationship(back_populates="users")

    # Devices the user has contributed compute/uploads from
    device_links: list["UserDevice"] = Relationship(back_populates="user")

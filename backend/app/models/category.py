# app/models/category.py
import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class Category(SQLModel, table=True):
    """Category model."""

    id: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    title: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=500)
    published: bool = Field(default=False)
    rank: int = Field(default=0)

    # Fields for category suggestion and approval workflow
    approved: bool = Field(
        default=False
    )  # Whether the category has been approved by an admin
    suggested_by: UUID | None = Field(
        default=None, foreign_key="user.id"
    )  # User who suggested the category
    approved_by: UUID | None = Field(
        default=None, foreign_key="user.id"
    )  # Admin who approved the category

    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationships for user references
    suggester: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Category.suggested_by]"}
    )
    approver: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Category.approved_by]"}
    )

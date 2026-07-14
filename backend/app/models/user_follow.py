"""User follow relationship model."""

import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .user import User


class UserFollow(SQLModel, table=True):
    """Many-to-many relationship table for user following."""

    __tablename__ = "user_follows"  # type: ignore[bad-override]

    id: UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    follower_id: UUID = Field(foreign_key="user.id", index=True)
    following_id: UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    follower: "User" = Relationship(
        back_populates="following_relationships",
        sa_relationship_kwargs={"foreign_keys": "[UserFollow.follower_id]"},
    )
    following: "User" = Relationship(
        back_populates="follower_relationships",
        sa_relationship_kwargs={"foreign_keys": "[UserFollow.following_id]"},
    )

    # Ensure unique constraint (user can only follow another user once)
    __table_args__ = ({"sqlite_autoincrement": True},)

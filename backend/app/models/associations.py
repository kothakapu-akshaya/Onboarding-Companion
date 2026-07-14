# app/models/associations.py
from uuid import UUID

from sqlmodel import Field, SQLModel


# Association table for many-to-many relationship between User and Role
class UserRoleLink(SQLModel, table=True):
    """User-role association model."""

    __tablename__ = "user_roles"  # type: ignore[bad-override]

    user_id: UUID | None = Field(
        default=None, foreign_key="user.id", primary_key=True
    )
    role_id: int | None = Field(
        default=None, foreign_key="role.id", primary_key=True
    )

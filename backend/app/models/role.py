# app/models/role.py
import enum
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


class RoleEnum(str, enum.Enum):
    """Role enum."""

    admin = "admin"
    user = "user"
    reviewer = "reviewer"
    system = "system"


class Role(SQLModel, table=True):
    """Role model."""

    id: int | None = Field(default=None, primary_key=True)
    name: RoleEnum = Field(unique=True, index=True)
    description: str | None = Field(default=None, max_length=255)

    # Many-to-many relationship with users
    # (will be defined after UserRoleLink import)

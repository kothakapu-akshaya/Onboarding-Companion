"""Database models package."""

# app/models/__init__.py

# Now define the many-to-many relationships after all models are imported
from sqlmodel import Relationship

from .associations import UserRoleLink
from .category import Category
from .course import Course
from .device import Device
from .event import Event
from .extracted_text import ExtractedText
from .institution import (
    CollegeType,
    District,
    Institution,
    ManagementType,
    Medium,
    Mode,
)
from .language import LanguageEntry
from .points import PointsEvent
from .record import MediaType, Record
from .record_history import (
    ChangeSource,
    ChangeType,
    RecordHistory,
    RecordMajorSnapshot,
    RecordRestore,
    RecordVersion,
)
from .role import Role, RoleEnum
from .user import User
from .user_device import UserDevice
from .user_follow import UserFollow

# Add the relationship fields to the models
Role.users = Relationship(back_populates="roles", link_model=UserRoleLink)  # type: ignore
User.roles = Relationship(back_populates="users", link_model=UserRoleLink)  # type: ignore

# Import all models to ensure they're registered with SQLModel
__all__ = [
    "Role",
    "RoleEnum",
    "User",
    "UserRoleLink",
    "Category",
    "LanguageEntry",
    "Record",
    "ExtractedText",
    "MediaType",
    "PointsEvent",
    "RecordHistory",
    "RecordVersion",
    "RecordMajorSnapshot",
    "RecordRestore",
    "ChangeType",
    "ChangeSource",
    "UserFollow",
    "Event",
    "Institution",
    "Course",
    "Device",
    "UserDevice",
    "District",
    "CollegeType",
    "ManagementType",
    "Medium",
    "Mode",
]

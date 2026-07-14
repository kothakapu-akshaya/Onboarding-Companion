import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from .device import Device
    from .user import User


class UserDevice(SQLModel, table=True):
    """Link between a user and a device they have contributed from.

    A device can be shared by multiple users (e.g. a community computer),
    and a user can have multiple devices.
    """

    __table_args__ = (
        UniqueConstraint(
            "user_id", "device_uid", name="uq_user_device_user_id_device_uid"
        ),
    )

    uid: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)

    user_id: UUID = Field(foreign_key="user.id", index=True)
    device_uid: UUID = Field(foreign_key="device.uid", index=True)

    # When this user first/last used this device
    first_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    user: Optional["User"] = Relationship(back_populates="device_links")
    device: Optional["Device"] = Relationship(back_populates="user_links")

import enum
import uuid as uuid_pkg
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .extracted_text import ExtractedText
    from .record import Record
    from .user_device import UserDevice


class OSType(str, enum.Enum):
    """Broad operating system platform of a device."""

    android = "android"
    ios = "ios"
    linux = "linux"
    windows = "windows"
    macos = "macos"
    other = "other"


class ComputeTier(str, enum.Enum):
    """Coarse volunteer-compute capability tier of a device."""

    low = "low"
    medium = "medium"
    high = "high"


def calculate_compute_tier(
    cpu_cores: int | None,
    ram_gb: float | None,
    gpu_model: str | None,
    gpu_vram_gb: float | None = None,
) -> ComputeTier | None:
    """Derive a coarse compute capability tier from hardware specs.

    Returns None if no hardware specs are available to base a tier on.
    """
    if cpu_cores is None and ram_gb is None and gpu_model is None:
        return None

    cores = cpu_cores or 0
    ram = ram_gb or 0
    has_gpu = bool(gpu_model)
    vram = gpu_vram_gb or 0

    if has_gpu and cores >= 8 and ram >= 16 and vram >= 8:
        return ComputeTier.high
    if has_gpu and vram >= 4:
        return ComputeTier.medium
    if cores >= 4 and ram >= 8:
        return ComputeTier.medium
    return ComputeTier.low


class Device(SQLModel, table=True):
    """Hardware profile of a device, shared across the users who use it.

    e.g. a shared lab or community computer.
    """

    uid: UUID | None = Field(default_factory=uuid_pkg.uuid4, primary_key=True)

    # Stable client-generated identifier (or hardware fingerprint hash),
    # globally unique across all users.
    device_id: str = Field(max_length=255, unique=True, index=True)

    # Hardware fingerprint hash, used as a fallback identifier when a
    # client's device_id changes (e.g. reinstall, cleared storage) but the
    # underlying hardware is the same.
    fingerprint_hash: str | None = Field(
        default=None, max_length=255, index=True
    )

    device_name: str | None = Field(default=None, max_length=200)
    os_type: OSType | None = Field(default=None, index=True)
    os_name: str | None = Field(default=None, max_length=100)
    os_version: str | None = Field(default=None, max_length=100)
    cpu_model: str | None = Field(default=None, max_length=200)
    cpu_architecture: str | None = Field(default=None, max_length=50)
    cpu_cores: int | None = Field(default=None, ge=0)
    ram_gb: float | None = Field(default=None, ge=0)
    gpu_model: str | None = Field(default=None, max_length=200)
    gpu_cores: int | None = Field(default=None, ge=0)
    gpu_vram_gb: float | None = Field(default=None, ge=0)
    download_speed_mbps: float | None = Field(default=None, ge=0)
    upload_speed_mbps: float | None = Field(default=None, ge=0)

    # Derived volunteer-compute capability tier, recalculated from hardware
    # specs on each upsert.
    compute_tier: ComputeTier | None = Field(default=None, index=True)

    # Earliest/latest time this device was seen, across all users
    first_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )

    user_links: list["UserDevice"] = Relationship(back_populates="device")
    records: list["Record"] = Relationship(back_populates="device")
    extracted_texts: list["ExtractedText"] = Relationship(
        back_populates="device"
    )

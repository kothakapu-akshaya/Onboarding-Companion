"""Schemas for device hardware profiles."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.device import ComputeTier, OSType


class DeviceUpsert(BaseModel):
    """Payload for registering or updating a device's hardware profile."""

    device_id: str = Field(..., min_length=1, max_length=255)
    fingerprint_hash: str | None = Field(
        None,
        max_length=255,
        description=(
            "Hardware fingerprint hash, used as a fallback identifier if "
            "device_id changes (e.g. reinstall) but the hardware is the same"
        ),
    )
    device_name: str | None = Field(None, max_length=200)
    os_type: OSType | None = Field(
        None, description="Broad operating system platform"
    )
    os_name: str | None = Field(None, max_length=100)
    os_version: str | None = Field(None, max_length=100)
    cpu_model: str | None = Field(None, max_length=200)
    cpu_architecture: str | None = Field(
        None,
        max_length=50,
        description="CPU instruction set architecture, e.g. x86_64, arm64",
    )
    cpu_cores: int | None = Field(None, ge=0)
    ram_gb: float | None = Field(None, ge=0)
    gpu_model: str | None = Field(None, max_length=200)
    gpu_cores: int | None = Field(None, ge=0)
    gpu_vram_gb: float | None = Field(None, ge=0)
    download_speed_mbps: float | None = Field(None, ge=0)
    upload_speed_mbps: float | None = Field(None, ge=0)


class DeviceRead(BaseModel):
    """Representation of a device returned to callers."""

    uid: UUID
    device_id: str
    fingerprint_hash: str | None = None
    device_name: str | None = None
    os_type: OSType | None = None
    os_name: str | None = None
    os_version: str | None = None
    cpu_model: str | None = None
    cpu_architecture: str | None = None
    cpu_cores: int | None = None
    ram_gb: float | None = None
    gpu_model: str | None = None
    gpu_cores: int | None = None
    gpu_vram_gb: float | None = None
    download_speed_mbps: float | None = None
    upload_speed_mbps: float | None = None
    compute_tier: ComputeTier | None = Field(
        None,
        description=(
            "Coarse volunteer-compute capability tier, derived from "
            "hardware specs"
        ),
    )
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    user_first_seen_at: datetime | None = Field(
        None, description="When the current user first used this device"
    )
    user_last_seen_at: datetime | None = Field(
        None, description="When the current user last used this device"
    )

    model_config = ConfigDict(from_attributes=True)


class DeviceUserLink(BaseModel):
    """A user linked to a shared device. Admin only."""

    user_id: UUID
    username: str
    name: str
    first_seen_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceStatsResponse(BaseModel):
    """Federation-wide device hardware composition. Admin only."""

    total_devices: int
    total_user_links: int
    by_os_type: dict[str, int] = Field(default_factory=dict)
    by_os_name: dict[str, int] = Field(default_factory=dict)
    by_cpu_model: dict[str, int] = Field(default_factory=dict)
    by_cpu_architecture: dict[str, int] = Field(default_factory=dict)
    by_gpu_model: dict[str, int] = Field(default_factory=dict)
    by_compute_tier: dict[str, int] = Field(default_factory=dict)
    avg_ram_gb: float | None = None
    avg_gpu_vram_gb: float | None = None
    avg_download_speed_mbps: float | None = None
    avg_upload_speed_mbps: float | None = None

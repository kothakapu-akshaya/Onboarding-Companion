"""Device hardware profile endpoints."""

import enum
import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlmodel import col, select

from app.core.rbac_fastapi import require_admin, require_any_role
from app.db.session import SessionDep
from app.models.device import Device, calculate_compute_tier
from app.models.user import User
from app.models.user_device import UserDevice
from app.schemas.device import (
    DeviceRead,
    DeviceStatsResponse,
    DeviceUpsert,
    DeviceUserLink,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _str_count_dict(
    rows: Sequence[tuple[enum.Enum | str | None, int]],
) -> dict[str, int]:
    """Convert (key, count) rows into a dict[str, int], dropping null keys."""
    result: dict[str, int] = {}
    for key, count in rows:
        if key is None:
            continue
        result[key.value if isinstance(key, enum.Enum) else key] = count
    return result


def _to_device_read(
    device: Device, link: UserDevice | None = None
) -> DeviceRead:
    data = DeviceRead.model_validate(device).model_dump()
    if link is not None:
        data["user_first_seen_at"] = link.first_seen_at
        data["user_last_seen_at"] = link.last_seen_at
    return DeviceRead.model_validate(data)


@router.put("/", response_model=DeviceRead)
def upsert_device(
    device_data: DeviceUpsert,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> DeviceRead:
    """Create or update a device's hardware profile and link it to the user.

    Devices are identified globally by a stable `device_id` (client-generated
    ID or hardware fingerprint hash), so the same device can be shared and
    reported by multiple users. Calling this repeatedly for the same device
    updates its hardware profile and `last_seen_at` timestamps.

    If `device_id` is unrecognized but `fingerprint_hash` matches a
    previously registered device, the existing device record is reused and
    its `device_id` is updated — this handles cases where a client's stable
    ID is lost (e.g. reinstall) but the underlying hardware is unchanged.
    """
    now = datetime.now(timezone.utc)

    device = session.exec(
        select(Device).where(Device.device_id == device_data.device_id)
    ).first()

    matched_via_fingerprint = False
    if device is None and device_data.fingerprint_hash:
        device = session.exec(
            select(Device).where(
                Device.fingerprint_hash == device_data.fingerprint_hash
            )
        ).first()
        matched_via_fingerprint = device is not None

    if device is None:
        device = Device(device_id=device_data.device_id, first_seen_at=now)
    elif matched_via_fingerprint:
        device.device_id = device_data.device_id

    for field, value in device_data.model_dump(
        exclude_unset=True, exclude={"device_id"}
    ).items():
        setattr(device, field, value)

    device.compute_tier = calculate_compute_tier(
        device.cpu_cores, device.ram_gb, device.gpu_model, device.gpu_vram_gb
    )

    device.last_seen_at = now
    device.updated_at = now

    session.add(device)
    session.flush()

    link = session.exec(
        select(UserDevice).where(
            UserDevice.user_id == current_user.id,
            UserDevice.device_uid == device.uid,
        )
    ).first()

    if link is None:
        link = UserDevice(
            user_id=current_user.id,
            device_uid=device.uid,
            first_seen_at=now,
        )

    link.last_seen_at = now

    session.add(link)
    session.commit()
    session.refresh(device)
    session.refresh(link)

    return jsonable_encoder(_to_device_read(device, link))


@router.get("/", response_model=list[DeviceRead])
def list_devices(
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> list[DeviceRead]:
    """List the devices the current user has contributed from."""
    rows = session.exec(
        select(Device, UserDevice)
        .join(UserDevice, col(UserDevice.device_uid) == col(Device.uid))
        .where(UserDevice.user_id == current_user.id)
        .order_by(UserDevice.last_seen_at.desc())  # type: ignore[attr-defined]
    ).all()
    return jsonable_encoder(
        [_to_device_read(device, link) for device, link in rows]
    )


@router.get("/stats", response_model=DeviceStatsResponse)
def get_device_stats(
    session: SessionDep,
    current_user: User = Depends(require_admin()),
    active_since: datetime | None = Query(
        None,
        description=(
            "Only include devices last seen at or after this time, to "
            "exclude stale/abandoned devices from the hardware composition"
        ),
    ),
) -> DeviceStatsResponse:
    """Federation-wide device hardware composition. Admin only."""
    device_filter = (
        [Device.last_seen_at >= active_since] if active_since else []
    )

    total_devices = session.exec(
        select(func.count()).select_from(Device).where(*device_filter)
    ).one()
    total_user_links = session.exec(
        select(func.count()).select_from(UserDevice)
    ).one()

    by_os_type = _str_count_dict(
        session.exec(
            select(Device.os_type, func.count())
            .where(Device.os_type.is_not(None), *device_filter)  # type: ignore[union-attr]
            .group_by(Device.os_type)
        ).all()
    )
    by_os_name = _str_count_dict(
        session.exec(
            select(Device.os_name, func.count())
            .where(Device.os_name.is_not(None), *device_filter)  # type: ignore[union-attr]
            .group_by(Device.os_name)
        ).all()
    )
    by_cpu_model = _str_count_dict(
        session.exec(
            select(Device.cpu_model, func.count())
            .where(Device.cpu_model.is_not(None), *device_filter)  # type: ignore[union-attr]
            .group_by(Device.cpu_model)
        ).all()
    )
    by_gpu_model = _str_count_dict(
        session.exec(
            select(Device.gpu_model, func.count())
            .where(Device.gpu_model.is_not(None), *device_filter)  # type: ignore[union-attr]
            .group_by(Device.gpu_model)
        ).all()
    )
    by_cpu_architecture = _str_count_dict(
        session.exec(
            select(Device.cpu_architecture, func.count())
            .where(Device.cpu_architecture.is_not(None), *device_filter)  # type: ignore[union-attr]
            .group_by(Device.cpu_architecture)
        ).all()
    )
    by_compute_tier = _str_count_dict(
        session.exec(
            select(Device.compute_tier, func.count())
            .where(Device.compute_tier.is_not(None), *device_filter)  # type: ignore[union-attr]
            .group_by(Device.compute_tier)
        ).all()
    )

    avg_ram_gb = session.exec(
        select(func.avg(Device.ram_gb)).where(*device_filter)
    ).one()
    avg_gpu_vram_gb = session.exec(
        select(func.avg(Device.gpu_vram_gb)).where(*device_filter)
    ).one()
    avg_download_speed_mbps = session.exec(
        select(func.avg(Device.download_speed_mbps)).where(*device_filter)
    ).one()
    avg_upload_speed_mbps = session.exec(
        select(func.avg(Device.upload_speed_mbps)).where(*device_filter)
    ).one()

    return DeviceStatsResponse(
        total_devices=total_devices,
        total_user_links=total_user_links,
        by_os_type=by_os_type,
        by_os_name=by_os_name,
        by_cpu_model=by_cpu_model,
        by_cpu_architecture=by_cpu_architecture,
        by_gpu_model=by_gpu_model,
        by_compute_tier=by_compute_tier,
        avg_ram_gb=avg_ram_gb,
        avg_gpu_vram_gb=avg_gpu_vram_gb,
        avg_download_speed_mbps=avg_download_speed_mbps,
        avg_upload_speed_mbps=avg_upload_speed_mbps,
    )


@router.get("/{device_uid}/users", response_model=list[DeviceUserLink])
def get_device_users(
    device_uid: UUID,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
) -> list[DeviceUserLink]:
    """List the users linked to a shared device. Admin only."""
    device = session.get(Device, device_uid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    rows = session.exec(
        select(User, UserDevice)
        .join(UserDevice, col(UserDevice.user_id) == col(User.id))
        .where(UserDevice.device_uid == device_uid)
        .order_by(UserDevice.last_seen_at.desc())  # type: ignore[attr-defined]
    ).all()

    return jsonable_encoder(
        [
            DeviceUserLink(
                user_id=user.id,
                username=user.username,
                name=user.name,
                first_seen_at=link.first_seen_at,
                last_seen_at=link.last_seen_at,
            )
            for user, link in rows
        ]
    )


@router.get("/{device_uid}", response_model=DeviceRead)
def get_device(
    device_uid: UUID,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> DeviceRead:
    """Get a device the current user has contributed from."""
    link = session.exec(
        select(UserDevice).where(
            UserDevice.user_id == current_user.id,
            UserDevice.device_uid == device_uid,
        )
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Device not found")

    device = session.get(Device, device_uid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return jsonable_encoder(_to_device_read(device, link))

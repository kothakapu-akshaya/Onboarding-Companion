"""Tests for device endpoint behavior."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.devices import (
    get_device,
    get_device_stats,
    get_device_users,
    list_devices,
    upsert_device,
)
from app.models.device import ComputeTier, OSType
from app.schemas.device import DeviceUpsert
from tests.unit.api.v1.endpoints.conftest import DummyModel, result_rows


def make_device(**overrides):
    now = datetime.now(timezone.utc)
    device = DummyModel(
        uid=uuid4(),
        device_id="device-123",
        device_name="My Laptop",
        os_type=OSType.linux,
        os_name="Linux",
        os_version="6.0",
        cpu_model="Ryzen 7",
        cpu_architecture="x86_64",
        cpu_cores=8,
        ram_gb=16.0,
        gpu_model="RTX 3060",
        gpu_cores=3584,
        gpu_vram_gb=12.0,
        download_speed_mbps=100.0,
        upload_speed_mbps=20.0,
        first_seen_at=now,
        last_seen_at=now,
        created_at=now,
        updated_at=now,
    )
    for key, value in overrides.items():
        setattr(device, key, value)
    return device


def make_link(**overrides):
    now = datetime.now(timezone.utc)
    link = DummyModel(
        uid=uuid4(),
        user_id=overrides.get("user_id", uuid4()),
        device_uid=overrides.get("device_uid", uuid4()),
        first_seen_at=now,
        last_seen_at=now,
    )
    for key, value in overrides.items():
        setattr(link, key, value)
    return link


def test_upsert_device_creates_new_device_and_link(mock_session, endpoint_user):
    # No existing device, no existing user-device link.
    mock_session.exec.side_effect = [result_rows(), result_rows()]

    payload = DeviceUpsert(
        device_id="device-123",
        device_name="My Laptop",
        os_name="Linux",
        cpu_cores=8,
        ram_gb=16.0,
    )

    result = upsert_device(payload, mock_session, endpoint_user)

    assert mock_session.add.call_count == 2
    added_device = mock_session.add.call_args_list[0][0][0]
    added_link = mock_session.add.call_args_list[1][0][0]
    assert added_device.device_id == "device-123"
    assert added_device.device_name == "My Laptop"
    assert added_link.user_id == endpoint_user.id
    assert result["device_id"] == "device-123"


def test_upsert_device_updates_existing_device_and_links_new_user(
    mock_session, endpoint_user
):
    existing = make_device()
    # Existing device found, but no link for this user yet (device shared).
    mock_session.exec.side_effect = [result_rows(existing), result_rows()]

    payload = DeviceUpsert(device_id="device-123", ram_gb=32.0)

    result = upsert_device(payload, mock_session, endpoint_user)

    assert existing.ram_gb == 32.0
    assert result["ram_gb"] == 32.0
    added_link = mock_session.add.call_args_list[-1][0][0]
    assert added_link.user_id == endpoint_user.id
    assert added_link.device_uid == existing.uid


def test_upsert_device_updates_existing_link(mock_session, endpoint_user):
    existing = make_device()
    existing_link = make_link(user_id=endpoint_user.id, device_uid=existing.uid)
    mock_session.exec.side_effect = [
        result_rows(existing),
        result_rows(existing_link),
    ]

    payload = DeviceUpsert(device_id="device-123")

    upsert_device(payload, mock_session, endpoint_user)

    assert mock_session.add.call_args_list[-1][0][0] is existing_link


def test_list_devices_returns_user_devices(mock_session, endpoint_user):
    device = make_device()
    link = make_link(user_id=endpoint_user.id, device_uid=device.uid)
    mock_session.exec.return_value = result_rows((device, link))

    result = list_devices(mock_session, endpoint_user)

    assert len(result) == 1
    assert result[0]["device_id"] == device.device_id
    assert result[0]["user_first_seen_at"] is not None


def test_get_device_not_found_without_link(mock_session, endpoint_user):
    mock_session.exec.return_value = result_rows()

    with pytest.raises(HTTPException) as exc_info:
        get_device(uuid4(), mock_session, endpoint_user)

    assert exc_info.value.status_code == 404


def test_get_device_returns_own_device(mock_session, endpoint_user):
    device = make_device()
    link = make_link(user_id=endpoint_user.id, device_uid=device.uid)
    mock_session.exec.return_value = result_rows(link)
    mock_session.get.return_value = device

    result = get_device(device.uid, mock_session, endpoint_user)

    assert result["device_id"] == device.device_id


def test_upsert_device_matches_via_fingerprint_fallback(
    mock_session, endpoint_user
):
    existing = make_device(device_id="old-device-id", fingerprint_hash="abc123")
    # device_id lookup misses, fingerprint lookup hits, no existing link.
    mock_session.exec.side_effect = [
        result_rows(),
        result_rows(existing),
        result_rows(),
    ]

    payload = DeviceUpsert(device_id="new-device-id", fingerprint_hash="abc123")

    result = upsert_device(payload, mock_session, endpoint_user)

    assert existing.device_id == "new-device-id"
    assert result["device_id"] == "new-device-id"
    added_link = mock_session.add.call_args_list[-1][0][0]
    assert added_link.device_uid == existing.uid


def test_get_device_users_not_found(mock_session, endpoint_user):
    mock_session.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        get_device_users(uuid4(), mock_session, endpoint_user)

    assert exc_info.value.status_code == 404


def test_get_device_users_returns_linked_users(mock_session, endpoint_user):
    device = make_device()
    mock_session.get.return_value = device

    user = DummyModel(uid=uuid4())
    user.id = uuid4()
    user.username = "alice"
    user.name = "Alice"
    link = make_link(user_id=user.id, device_uid=device.uid)
    mock_session.exec.return_value = result_rows((user, link))

    result = get_device_users(device.uid, mock_session, endpoint_user)

    assert len(result) == 1
    assert result[0]["username"] == "alice"
    assert result[0]["user_id"] == str(user.id)


def test_get_device_stats_returns_aggregates(mock_session, endpoint_user):
    mock_session.exec.side_effect = [
        result_rows(5),  # total_devices
        result_rows(7),  # total_user_links
        result_rows((OSType.linux, 3), (OSType.android, 2)),  # by_os_type
        result_rows(("Linux", 3), ("Windows", 2)),  # by_os_name
        result_rows(("Ryzen 7", 4)),  # by_cpu_model
        result_rows(("RTX 3060", 1)),  # by_gpu_model
        result_rows(("x86_64", 4), ("arm64", 1)),  # by_cpu_architecture
        result_rows(
            (ComputeTier.high, 2), (ComputeTier.low, 3)
        ),  # by_compute_tier
        result_rows(16.0),  # avg_ram_gb
        result_rows(12.0),  # avg_gpu_vram_gb
        result_rows(100.0),  # avg_download_speed_mbps
        result_rows(20.0),  # avg_upload_speed_mbps
    ]

    result = get_device_stats(mock_session, endpoint_user)

    assert result.total_devices == 5
    assert result.total_user_links == 7
    assert result.by_os_type == {"linux": 3, "android": 2}
    assert result.by_os_name == {"Linux": 3, "Windows": 2}
    assert result.by_cpu_model == {"Ryzen 7": 4}
    assert result.by_gpu_model == {"RTX 3060": 1}
    assert result.by_cpu_architecture == {"x86_64": 4, "arm64": 1}
    assert result.by_compute_tier == {"high": 2, "low": 3}
    assert result.avg_ram_gb == 16.0
    assert result.avg_download_speed_mbps == 100.0
    assert result.avg_upload_speed_mbps == 20.0

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.endpoints.users import get_user


class DummyUser:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.username = kwargs.get("username", "testuser")
        self.phone = kwargs.get("phone", "+919876543210")
        self.is_active = kwargs.get("is_active", True)
        self.has_given_consent = kwargs.get("has_given_consent", True)
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
        for k, v in kwargs.items():
            setattr(self, k, v)

    def model_dump(self):
        return {
            "id": self.id,
            "username": self.username,
            "phone": self.phone,
            "name": getattr(self, "name", "Test User"),
            "email": getattr(self, "email", "test@example.com"),
            "is_active": self.is_active,
            "has_given_consent": self.has_given_consent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "phone_privacy": "public",
            "email_privacy": "public",
        }


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.mark.asyncio
async def test_get_user_by_phone_direct(mock_session):
    user = DummyUser(phone="+919876543210")
    mock_session.exec.return_value.first.return_value = user

    current_user = DummyUser(id=uuid4())

    with (
        patch("app.api.v1.endpoints.users.get_user_roles", return_value=[]),
        patch(
            "app.api.v1.endpoints.users.filter_user_privacy",
            side_effect=lambda d, *args: d,
        ),
    ):
        result = await get_user(mock_session, "9876543210", current_user)

    assert result.phone == "+919876543210"
    # Verify phone lookup was attempted
    args, _ = mock_session.exec.call_args
    assert "phone = :phone_1" in str(args[0]).lower()


@pytest.mark.asyncio
async def test_get_user_by_username_fallback(mock_session):
    # If phone lookup fails to find user, it should fallback to identifier
    mock_session.exec.return_value.first.return_value = None

    user = DummyUser(username="testuser")
    current_user = DummyUser(id=uuid4())

    with (
        patch(
            "app.api.v1.endpoints.users.get_user_by_identifier",
            return_value=user,
        ),
        patch("app.api.v1.endpoints.users.get_user_roles", return_value=[]),
        patch(
            "app.api.v1.endpoints.users.filter_user_privacy",
            side_effect=lambda d, *args: d,
        ),
    ):
        result = await get_user(mock_session, "testuser", current_user)

    assert result.username == "testuser"

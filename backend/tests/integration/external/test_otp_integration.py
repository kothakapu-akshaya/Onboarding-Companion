import os
import uuid
from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app

# Skip integration tests if database is not available
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests skipped (set RUN_INTEGRATION_TESTS=1 to run)",
)


@pytest.fixture
def mock_session():
    """Mock DB session for FastAPI dependency injection."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.flush = Mock()
    session.exec = Mock()
    return session


class _ExecResult:
    """Small helper to mimic SQLModel exec() results (first/all)."""

    def __init__(self, *, first=None, all=None):
        self._first = first
        self._all = all

    def first(self):
        return self._first

    def all(self):
        return [] if self._all is None else self._all


@pytest.fixture
def client(mock_session):
    app.dependency_overrides[get_session] = lambda: mock_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_test_user():
    """Create a mock test user for unit tests."""
    user = Mock()
    user.id = uuid.uuid4()
    user.phone = "+919876543210"
    user.username = "test_user"
    user.name = "Test User"
    user.email = "test@example.com"
    user.gender = "male"
    user.date_of_birth = date(1990, 1, 1)
    user.place = "Test City, India"
    user.has_given_consent = True
    user.is_active = True
    user.hashed_password = "hashed_password"
    return user


class TestOTPAuth:
    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_login_otp_success(
        self, mock_otp_service, client, mock_session, mock_test_user
    ):
        mock_session.exec.return_value.first.return_value = mock_test_user
        mock_otp_service.return_value.send_otp = AsyncMock(
            return_value={"status": "success", "reference_id": "1234"}
        )
        mock_otp_service.return_value.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = client.post(
            "/api/v1/auth/login/send-otp", json={"phone": mock_test_user.phone}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_login_otp_rate_limit(
        self, mock_otp_service, client, mock_session, mock_test_user
    ):
        mock_session.exec.return_value.first.return_value = mock_test_user
        mock_otp_service.return_value.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": False, "wait_minutes": 5}
        )

        response = client.post(
            "/api/v1/auth/login/send-otp", json={"phone": mock_test_user.phone}
        )

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_login_otp_success(
        self, mock_otp_service, client, mock_session, mock_test_user
    ):
        mock_session.exec.side_effect = [
            _ExecResult(first=mock_test_user),  # user lookup
            _ExecResult(all=[]),  # roles lookup
        ]
        mock_otp_service.return_value.verify_otp_detailed = AsyncMock(
            return_value={"valid": True}
        )

        with patch(
            "app.api.v1.endpoints.auth.create_access_token",
            return_value="test_token",
        ):
            response = client.post(
                "/api/v1/auth/login/verify-otp",
                json={"phone": mock_test_user.phone, "otp_code": "123456"},
            )

        assert response.status_code == 200
        assert response.json()["access_token"] == "test_token"

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_login_otp_failure(
        self, mock_otp_service, client, mock_session, mock_test_user
    ):
        mock_session.exec.return_value.first.return_value = mock_test_user
        mock_otp_service.return_value.verify_otp_detailed = AsyncMock(
            return_value={"valid": False, "message": "Invalid OTP"}
        )

        response = client.post(
            "/api/v1/auth/login/verify-otp",
            json={"phone": mock_test_user.phone, "otp_code": "wrong_otp"},
        )

        assert response.status_code == 400
        assert "Invalid OTP" in response.json()["detail"]

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_forgot_password_init_success(
        self, mock_otp_service, client, mock_session, mock_test_user
    ):
        mock_session.exec.return_value.first.return_value = mock_test_user
        mock_otp_service.return_value.send_otp = AsyncMock(
            return_value={"status": "success", "reference_id": "1234"}
        )
        mock_otp_service.return_value.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = client.post(
            "/api/v1/auth/forgot-password/init",
            json={"phone": mock_test_user.phone},
        )

        assert response.status_code == 200
        assert "you will receive an OTP shortly" in response.json()["message"]

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_forgot_password_confirm_success(
        self, mock_otp_service, client, mock_session, mock_test_user
    ):
        mock_session.exec.return_value.first.return_value = mock_test_user
        mock_otp_service.return_value.verify_otp_detailed = AsyncMock(
            return_value={"valid": True}
        )

        with (
            patch(
                "app.api.v1.endpoints.auth.verify_password", return_value=False
            ),
            patch(
                "app.api.v1.endpoints.auth.get_password_hash",
                return_value="new_hashed_password",
            ),
        ):
            response = client.post(
                "/api/v1/auth/forgot-password/confirm",
                json={
                    "phone": mock_test_user.phone,
                    "otp_code": "123456",
                    "new_password": "new_password",
                    "confirm_password": "new_password",
                },
            )

        assert response.status_code == 200
        assert "Password reset successfully" in response.json()["message"]

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_signup_send_otp_success(
        self, mock_otp_service, client, mock_session
    ):
        mock_session.exec.return_value.first.return_value = (
            None  # No existing user for signup
        )
        mock_otp_service.return_value.send_signup_otp = AsyncMock(
            return_value={"status": "success", "reference_id": "1234"}
        )
        mock_otp_service.return_value.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = client.post(
            "/api/v1/auth/signup/send-otp", json={"phone": "+919876543210"}
        )

        assert response.status_code == 200
        assert "OTP sent successfully for signup" in response.json()["message"]

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_signup_verify_otp_success(
        self, mock_otp_service, client, mock_session
    ):
        mock_session.exec.side_effect = [
            _ExecResult(first=None),  # existing user by phone
            _ExecResult(first=None),  # existing email
            _ExecResult(first=None),  # existing username
            _ExecResult(all=[]),  # roles lookup
        ]
        mock_otp_service.return_value.verify_otp_detailed = AsyncMock(
            return_value={"valid": True}
        )

        with (
            patch(
                "app.api.v1.endpoints.auth.create_access_token",
                return_value="test_token",
            ),
            patch(
                "app.api.v1.endpoints.auth.get_password_hash",
                return_value="new_hashed_password",
            ),
        ):
            response = client.post(
                "/api/v1/auth/signup/verify-otp",
                json={
                    "phone": "+919876543211",
                    "otp_code": "123456",
                    "username": "new_user",
                    "name": "New User",
                    "email": "newuser@example.com",
                    "password": "new_password",
                    "confirm_password": "new_password",
                    "has_given_consent": True,
                    "gender": "male",
                    "date_of_birth": "1990-01-01",
                    "current_place": "New York",
                },
            )

        assert response.status_code == 200
        assert response.json()["access_token"] == "test_token"

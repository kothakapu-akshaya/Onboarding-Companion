"""Authentication-related fixtures for testing.

Provides OTP, token, and auth-specific test data.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from app.services.otp_service import OTPService
from tests.data.test_data import TestData


@pytest.fixture
def mock_otp_service():
    """Create a mock OTP service for testing."""
    service = Mock(spec=OTPService)
    service.send_otp = AsyncMock(
        return_value={"status": "success", "reference_id": "test_ref_id"}
    )
    service.verify_otp_detailed = AsyncMock(
        return_value={"valid": True, "message": "OTP verified successfully"}
    )
    service.check_rate_limit_detailed = AsyncMock(
        return_value={"allowed": True}
    )
    return service


@pytest.fixture
def otp_data():
    """Provide standard OTP data for testing."""
    return TestData.otp_data()


@pytest.fixture
def valid_otp_data():
    """Provide valid OTP test cases."""
    return [
        {"phone": "+919876543210", "otp_code": "123456"},
        {"phone": "+918765432109", "otp_code": "654321"},
        {"phone": "+917654321098", "otp_code": "111111"},
    ]


@pytest.fixture
def invalid_otp_data():
    """Provide invalid OTP test cases."""
    return [
        {"phone": "+919876543210", "otp_code": "000000"},  # Invalid OTP
        {"phone": "+919876543210", "otp_code": "12345"},  # Too short
        {"phone": "+919876543210", "otp_code": "1234567"},  # Too long
        {"phone": "invalid_phone", "otp_code": "123456"},  # Invalid phone
    ]


@pytest.fixture
def mock_jwt_token():
    """Create a mock JWT token for testing."""
    return "mock.jwt.token"


@pytest.fixture
def auth_headers(mock_jwt_token):
    """Create authentication headers for API testing."""
    return {"Authorization": f"Bearer {mock_jwt_token}"}


@pytest.fixture
def password_reset_data():
    """Provide password reset test data."""
    return {
        "phone": "+919876543210",
        "new_password": "NewSecurePass123!",
        "otp_code": "123456",
        "reference_id": "test_ref_id",
    }


@pytest.fixture
def password_change_data():
    """Provide password change test data."""
    return {
        "current_password": "SecurePass123!",
        "new_password": "NewSecurePass123!",
        "confirm_password": "NewSecurePass123!",
    }

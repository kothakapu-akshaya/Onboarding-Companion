"""Unit tests for auth endpoints - using mocks instead of DB fixtures."""

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import create_access_token, get_password_hash


@pytest.fixture
def mock_app():
    """Create a mock FastAPI app with auth router."""
    from app.api.v1.endpoints import auth

    app = FastAPI()
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    return app


@pytest.fixture
def client_with_mocked_db(mock_app):
    """Create test client with mocked database session."""
    with patch("app.db.session.get_session") as mock_get_session:
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        with TestClient(mock_app) as client:
            yield client, mock_session


class TestAuthUtilities:
    """Test auth utility functions."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        token = create_access_token(
            subject=str(uuid4()), expires_delta=timedelta(minutes=30)
        )
        assert token is not None
        assert isinstance(token, str)

    def test_get_password_hash(self):
        """Test password hashing."""
        password = "TestPass123!"
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password(self):
        """Test password verification."""
        from app.core.auth import verify_password

        password = "TestPass123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False


class TestAuthSchemas:
    """Test auth-related Pydantic schemas."""

    def test_login_request_schema(self):
        """Test LoginRequest schema."""
        from app.schemas import LoginRequest

        login = LoginRequest(phone="+919999999999", password="testpassword")
        assert login.phone == "+919999999999"
        assert login.password == "testpassword"

    def test_token_schema(self):
        """Test Token schema."""
        from app.schemas import Token

        token = Token(access_token="test_token", token_type="bearer")
        assert token.access_token == "test_token"
        assert token.token_type == "bearer"

    def test_password_change_request(self):
        """Test PasswordChangeRequest schema."""
        from app.schemas import PasswordChangeRequest

        req = PasswordChangeRequest(
            current_password="oldpass",
            new_password="NewPass123!",
            confirm_password="NewPass123!",
        )
        assert req.current_password == "oldpass"

    def test_otp_request_schemas(self):
        """Test OTP request schemas."""
        from app.schemas.otp import OTPLoginSendRequest, OTPLoginVerifyRequest

        send_req = OTPLoginSendRequest(phone="+919999999999")
        assert send_req.phone == "+919999999999"

        verify_req = OTPLoginVerifyRequest(
            phone="+919999999999", otp_code="123456"
        )
        assert verify_req.otp_code == "123456"


class TestAuthEdgeCases:
    """Test edge cases in auth functionality."""

    def test_login_request_invalid_phone(self):
        """Test login with invalid phone format.

        - expect no validation error for phone.
        """
        from app.schemas import LoginRequest

        login = LoginRequest(phone="invalid", password="password")
        assert login.phone == "invalid"

    def test_password_change_passwords_not_matching(self):
        """Test password change with non-matching passwords."""
        from pydantic import ValidationError

        from app.schemas import PasswordChangeRequest

        with pytest.raises(ValidationError):
            PasswordChangeRequest(
                current_password="oldpass",
                new_password="newpass1",
                confirm_password="newpass2",
            )

    def test_otp_request_invalid_phone(self):
        """Test OTP request with invalid phone."""
        from pydantic import ValidationError

        from app.schemas.otp import OTPLoginSendRequest

        with pytest.raises(ValidationError):
            OTPLoginSendRequest(phone="123")


class TestPasswordResetSchemas:
    """Test password reset schemas."""

    def test_password_reset_init_request(self):
        """Test PasswordResetInitRequest schema."""
        from app.schemas.password_reset import PasswordResetInitRequest

        req = PasswordResetInitRequest(phone="+919999999999")
        assert req.phone == "+919999999999"

    def test_password_reset_confirm_request(self):
        """Test PasswordResetConfirmRequest schema with matching passwords."""
        from app.schemas.password_reset import PasswordResetConfirmRequest

        req = PasswordResetConfirmRequest(
            phone="+919999999999",
            otp_code="123456",
            new_password="NewPass123!",
            confirm_password="NewPass123!",
        )
        assert req.otp_code == "123456"

    def test_password_reset_confirm_request_with_valid_data(self):
        """Test PasswordResetConfirmRequest schema with valid data."""
        from app.schemas.password_reset import PasswordResetConfirmRequest

        req = PasswordResetConfirmRequest(
            phone="+919999999999",
            otp_code="123456",
            new_password="NewPass123!",
            confirm_password="NewPass123!",
        )
        assert req.otp_code == "123456"
        assert req.new_password == req.confirm_password
        assert req.otp_code == "123456"

    def test_password_reset_confirm_passwords_not_matching(self):
        """Test password reset with different passwords."""
        from pydantic import ValidationError

        from app.schemas.password_reset import PasswordResetConfirmRequest

        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(
                phone="+919999999999",
                otp_code="123456",
                new_password="newpass1",
                confirm_password="newpass2",
            )


class TestSignupSchemas:
    """Test signup-related schemas."""

    def test_otp_signup_send_request(self):
        """Test OTPSignupSendRequest schema."""
        from app.schemas.otp import OTPSignupSendRequest

        req = OTPSignupSendRequest(
            phone="+919999999999", email="test@example.com"
        )
        assert req.phone == "+919999999999"
        assert req.email == "test@example.com"

    def test_otp_signup_verify_request(self):
        """Test OTPSignupVerifyRequest schema."""
        from app.schemas.otp import OTPSignupVerifyRequest

        req = OTPSignupVerifyRequest(
            phone="+919999999999",
            otp_code="123456",
            password="TestPass123!",
            confirm_password="TestPass123!",
            name="Test User",
            email="test@example.com",
            gender="male",
            date_of_birth="2000-01-01",
            current_place="Test City",
            has_given_consent=True,
        )
        assert req.has_given_consent is True

    def test_signup_without_consent(self):
        """Test signup request without consent."""
        from pydantic import ValidationError

        from app.schemas.otp import OTPSignupVerifyRequest

        with pytest.raises(ValidationError):
            OTPSignupVerifyRequest(
                phone="+919999999999",
                otp_code="123456",
                password="TestPass123!",
                confirm_password="TestPass123!",
                name="Test User",
                email="test@example.com",
                gender="male",
                date_of_birth="2000-01-01",
                current_place="Test City",
                has_given_consent=False,
            )


class TestTokenResponseSchema:
    """Test TokenResponse schema."""

    def test_token_response(self):
        """Test TokenResponse with all fields."""
        from app.schemas import RoleRead
        from app.schemas.otp import TokenResponse

        role = RoleRead(id=3, name="user", description="Regular user")

        response = TokenResponse(
            access_token="test_token",
            token_type="bearer",
            user_id=str(uuid4()),
            username="testuser",
            phone="+919999999999",
            roles=[role],
        )

        assert response.access_token == "test_token"
        assert len(response.roles) == 1
        assert response.roles[0].name == "user"


class TestOTPResponseSchema:
    """Test OTPResponse schema."""

    def test_otp_response_success(self):
        """Test successful OTP response."""
        from app.schemas.otp import OTPResponse

        response = OTPResponse(
            status="success",
            message="OTP sent successfully",
            reference_id="ref123",
        )

        assert response.status == "success"
        assert response.reference_id == "ref123"

    def test_otp_response_signup_required(self):
        """Test OTP response for signup required."""
        from app.schemas.otp import OTPResponse

        response = OTPResponse(
            status="signup_required",
            message="Phone number not found",
            reference_id=None,
        )

        assert response.status == "signup_required"
        assert response.reference_id is None


class TestPasswordResetResponseSchema:
    """Test PasswordResetResponse schema."""

    def test_password_reset_response(self):
        """Test password reset response."""
        from app.schemas.password_reset import PasswordResetResponse

        response = PasswordResetResponse(
            status="success", message="Password reset successful"
        )

        assert response.status == "success"
        assert "successful" in response.message

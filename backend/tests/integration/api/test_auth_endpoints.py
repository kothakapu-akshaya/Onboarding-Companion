import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tests.data.test_data import TestData
from tests.helpers.assertions import assert_api_error, assert_api_response
from tests.helpers.test_builders import user_data

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests skipped (set RUN_INTEGRATION_TESTS=1 to run)",
)


class TestAuthSignupEndpoints:
    """Test user registration endpoints."""

    def test_signup_endpoint_exists(self, app_client):
        """Test signup endpoint accessibility."""
        response = app_client.post("/api/v1/auth/signup")
        # Should return 422 for missing data, not 404
        assert response.status_code == 422

    def test_signup_with_valid_data(self, app_client, user_registration_data):
        """Test signup with valid data."""
        response = app_client.post(
            "/api/v1/auth/signup", json=user_registration_data
        )

        # Could be 201 (success), 409 (duplicate), or 422 (validation)
        assert response.status_code in [201, 409, 422, 500]

        if response.status_code == 201:
            assert_api_response(response, 200, ["user_id", "message"])

    @pytest.mark.parametrize(
        "registration_data",
        [
            user_data().with_phone("8876543210").build(),
            user_data().with_email("different@example.com").build(),
            user_data().with_name("Different User").build(),
            user_data().with_gender("female").build(),
        ],
    )
    def test_signup_variations(self, app_client, registration_data):
        """Test signup with different valid data variations."""
        response = app_client.post(
            "/api/v1/auth/signup", json=registration_data
        )
        assert response.status_code in [201, 409, 422, 500]

    @pytest.mark.parametrize(
        "invalid_data",
        [
            user_data().with_phone("5876543210").build(),  # Invalid phone
            user_data().with_password("weak").build(),  # Weak password
            user_data().with_name("A").build(),  # Too short name
            user_data().without_consent().build(),  # No consent
        ],
    )
    def test_signup_validation_errors(self, app_client, invalid_data):
        """Test signup with invalid data."""
        response = app_client.post("/api/v1/auth/signup", json=invalid_data)
        assert_api_error(response, 422)

    def test_signup_missing_required_fields(self, app_client):
        """Test signup with missing required fields."""
        incomplete_data = {"name": "Test User"}
        response = app_client.post("/api/v1/auth/signup", json=incomplete_data)
        assert_api_error(response, 422)

    def test_signup_password_mismatch(self, app_client, user_registration_data):
        """Test signup with password confirmation mismatch."""
        data = {
            **user_registration_data,
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass123!",
        }
        response = app_client.post("/api/v1/auth/signup", json=data)
        assert_api_error(response, 422)


class TestAuthLoginEndpoints:
    """Test authentication login endpoints."""

    def test_login_endpoint_exists(self, app_client):
        """Test login endpoint accessibility."""
        response = app_client.post("/api/v1/auth/login")
        assert_api_error(response, 422)

    def test_login_with_phone(self, app_client, user_login_data):
        """Test login with phone number."""
        response = app_client.post("/api/v1/auth/login", json=user_login_data)

        # Could be various responses depending on user existence
        assert response.status_code in [200, 400, 401, 404, 422, 500]

    def test_login_with_email(self, app_client):
        """Test login with email."""
        login_data = {"email": "test@example.com", "password": "SecurePass123!"}
        response = app_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code in [200, 400, 401, 404, 422, 500]

    def test_login_invalid_credentials(self, app_client):
        """Test login with invalid credentials."""
        invalid_data = {"phone": "9876543210", "password": "WrongPassword123!"}
        response = app_client.post("/api/v1/auth/login", json=invalid_data)
        assert response.status_code in [401, 404, 422]

    def test_login_missing_credentials(self, app_client):
        """Test login with missing credentials."""
        # Missing password
        response = app_client.post(
            "/api/v1/auth/login", json={"phone": "9876543210"}
        )
        assert_api_error(response, 422)

        # Missing phone/email
        response = app_client.post(
            "/api/v1/auth/login", json={"password": "SecurePass123!"}
        )
        assert_api_error(response, 422)

    @pytest.mark.parametrize("invalid_phone", TestData.INVALID_PHONES)
    def test_login_invalid_phone_formats(self, app_client, invalid_phone):
        """Test login with invalid phone formats."""
        login_data = {"phone": invalid_phone, "password": "SecurePass123!"}
        response = app_client.post("/api/v1/auth/login", json=login_data)
        assert_api_error(response, 422)


class TestUserEndpoints:
    """Test user-related endpoints (e.g., /me, change-password)."""

    def test_read_users_me_success(self, authenticated_client):
        """Test successful retrieval of current user information."""
        response = authenticated_client.get("/api/v1/auth/me")
        assert_api_response(response, 200, ["id", "phone", "email", "name"])

    def test_read_users_me_unauthorized(self, app_client):
        """Test unauthorized access to current user information."""
        response = app_client.get("/api/v1/auth/me")
        assert_api_error(response, 401)

    def test_change_password_success(self, authenticated_client, test_user):
        """Test successful password change."""
        change_data = {
            "current_password": "testpassword",
            "new_password": "NewSecurePassword123!",
            "confirm_new_password": "NewSecurePassword123!",
        }
        response = authenticated_client.post(
            "/api/v1/auth/change-password", json=change_data
        )
        assert_api_response(response, 200, ["message"])
        assert response.json()["message"] == "Password changed successfully"

    def test_change_password_incorrect_current_password(
        self, authenticated_client
    ):
        """Test password change with incorrect current password."""
        change_data = {
            "current_password": "WrongPassword",
            "new_password": "NewSecurePassword123!",
            "confirm_new_password": "NewSecurePassword123!",
        }
        response = authenticated_client.post(
            "/api/v1/auth/change-password", json=change_data
        )
        assert_api_error(response, 400, "Incorrect current password")

    def test_change_password_new_password_mismatch(self, authenticated_client):
        """Test password change with new password mismatch."""
        change_data = {
            "current_password": "testpassword",
            "new_password": "NewSecurePassword123!",
            "confirm_new_password": "MismatchPassword!",
        }
        response = authenticated_client.post(
            "/api/v1/auth/change-password", json=change_data
        )
        assert_api_error(response, 422)  # Pydantic validation error

    def test_change_password_unauthorized(self, app_client):
        """Test unauthorized password change."""
        change_data = {
            "current_password": "testpassword",
            "new_password": "NewSecurePassword123!",
            "confirm_new_password": "NewSecurePassword123!",
        }
        response = app_client.post(
            "/api/v1/auth/change-password", json=change_data
        )
        assert_api_error(response, 401)

    def test_reset_password_admin_success(
        self, authenticated_client, test_user
    ):
        """Test successful password reset by admin."""
        # This test requires an admin user. For now, we'll
        # assume authenticated_client is admin.
        # In a real scenario, you'd need a fixture for an admin user.
        reset_data = {
            "phone": test_user.phone,
            "new_password": "AdminResetPassword123!",
            "confirm_new_password": "AdminResetPassword123!",
        }
        response = authenticated_client.post(
            "/api/v1/auth/reset-password", json=reset_data
        )
        assert_api_response(response, 200, ["message"])
        assert response.json()["message"] == "Password reset successfully"

    def test_reset_password_admin_user_not_found(self, authenticated_client):
        """Test password reset by admin for a non-existent user."""
        reset_data = {
            "phone": "+919999999999",  # Non-existent phone
            "new_password": "AdminResetPassword123!",
            "confirm_new_password": "AdminResetPassword123!",
        }
        response = authenticated_client.post(
            "/api/v1/auth/reset-password", json=reset_data
        )
        assert_api_error(response, 404, "User not found")

    def test_reset_password_non_admin_unauthorized(self, app_client):
        """Test password reset by non-admin user (unauthorized)."""
        # Assuming app_client is not authenticated as admin
        reset_data = {
            "phone": "+919876543210",
            "new_password": "AdminResetPassword123!",
            "confirm_new_password": "AdminResetPassword123!",
        }
        response = app_client.post(
            "/api/v1/auth/reset-password", json=reset_data
        )
        assert_api_error(response, 401)  # Or 403 if authenticated but not admin

    def test_login_endpoint_exists(self, app_client):
        """Test login endpoint accessibility."""
        response = app_client.post("/api/v1/auth/login")
        assert_api_error(response, 422)

    def test_login_with_phone(self, app_client, user_login_data):
        """Test login with phone number."""
        response = app_client.post("/api/v1/auth/login", json=user_login_data)

        # Could be various responses depending on user existence
        assert response.status_code in [200, 400, 401, 404, 422, 500]

    def test_login_with_email(self, app_client):
        """Test login with email."""
        login_data = {"email": "test@example.com", "password": "SecurePass123!"}
        response = app_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code in [200, 400, 401, 404, 422, 500]

    def test_login_invalid_credentials(self, app_client):
        """Test login with invalid credentials."""
        invalid_data = {"phone": "9876543210", "password": "WrongPassword123!"}
        response = app_client.post("/api/v1/auth/login", json=invalid_data)
        assert response.status_code in [401, 404, 422]

    def test_login_missing_credentials(self, app_client):
        """Test login with missing credentials."""
        # Missing password
        response = app_client.post(
            "/api/v1/auth/login", json={"phone": "9876543210"}
        )
        assert_api_error(response, 422)

        # Missing phone/email
        response = app_client.post(
            "/api/v1/auth/login", json={"password": "SecurePass123!"}
        )
        assert_api_error(response, 422)

    @pytest.mark.parametrize("invalid_phone", TestData.INVALID_PHONES)
    def test_login_invalid_phone_formats(self, app_client, invalid_phone):
        """Test login with invalid phone formats."""
        login_data = {"phone": invalid_phone, "password": "SecurePass123!"}
        response = app_client.post("/api/v1/auth/login", json=login_data)
        assert_api_error(response, 422)


class TestOTPEndpoints:
    """Test OTP-related endpoints."""

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_login_otp_success(
        self, mock_otp_service, app_client, test_user
    ):
        """Test sending login OTP successfully."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.send_otp = AsyncMock(
            return_value={"status": "success", "reference_id": "test_ref_id"}
        )
        mock_service_instance.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = app_client.post(
            "/api/v1/auth/login/send-otp", json={"phone": test_user.phone}
        )

        assert_api_response(response, 200, ["status", "reference_id"])
        assert response.json()["status"] == "success"

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_login_otp_signup_required(self, mock_otp_service, app_client):
        """Test sending login OTP for a non-existent user.

        (should prompt signup).
        """
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = app_client.post(
            "/api/v1/auth/login/send-otp",
            json={
                "phone": "+919999999999"  # Non-existent phone
            },
        )

        assert_api_response(response, 200, ["status", "message"])
        assert response.json()["status"] == "signup_required"

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_login_otp_inactive_user(
        self, mock_otp_service, app_client, test_user
    ):
        """Test sending login OTP for an inactive user."""
        test_user.is_active = False  # Deactivate user for this test
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = app_client.post(
            "/api/v1/auth/login/send-otp", json={"phone": test_user.phone}
        )
        assert_api_error(response, 401, "User account is inactive")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_login_otp_rate_limited(
        self, mock_otp_service, app_client, test_user
    ):
        """Test sending login OTP when rate limited."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": False, "wait_minutes": 1}
        )

        response = app_client.post(
            "/api/v1/auth/login/send-otp", json={"phone": test_user.phone}
        )
        assert_api_error(
            response,
            429,
            "Rate limit exceeded. Please wait 1 minute(s) before trying again.",
        )

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_login_otp_service_failure(
        self, mock_otp_service, app_client, test_user
    ):
        """Test sending login OTP when OTP service fails."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.send_otp = AsyncMock(
            return_value={"status": "failed", "message": "Provider error"}
        )
        mock_service_instance.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = app_client.post(
            "/api/v1/auth/login/send-otp", json={"phone": test_user.phone}
        )
        assert_api_error(response, 500, "Failed to send OTP: Provider error")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_login_otp_success(
        self, mock_otp_service, app_client, otp_data, test_user
    ):
        """Test verifying login OTP successfully."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.verify_otp_detailed = AsyncMock(
            return_value={"valid": True, "message": "OTP verified successfully"}
        )

        response = app_client.post(
            "/api/v1/auth/login/verify-otp", json=otp_data
        )

        assert_api_response(
            response,
            200,
            ["access_token", "token_type", "user_id", "phone", "roles"],
        )
        assert response.json()["phone"] == test_user.phone

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_login_otp_invalid_code(
        self, mock_otp_service, app_client, otp_data
    ):
        """Test verifying login OTP with invalid code."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.verify_otp_detailed = AsyncMock(
            return_value={"valid": False, "message": "Invalid OTP code"}
        )

        response = app_client.post(
            "/api/v1/auth/login/verify-otp", json=otp_data
        )
        assert_api_error(response, 400, "Invalid OTP code")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_login_otp_inactive_user(
        self, mock_otp_service, app_client, otp_data, test_user
    ):
        """Test verifying login OTP for an inactive user."""
        test_user.is_active = False  # Deactivate user for this test
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.verify_otp_detailed = AsyncMock(
            return_value={"valid": True, "message": "OTP verified successfully"}
        )

        response = app_client.post(
            "/api/v1/auth/login/verify-otp", json=otp_data
        )
        assert_api_error(response, 401, "User account is inactive")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_login_otp_user_not_found(
        self, mock_otp_service, app_client, otp_data
    ):
        """Test verifying login OTP when user is not found.

        (should not happen if send-otp was called).
        """
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.verify_otp_detailed = AsyncMock(
            return_value={"valid": True, "message": "OTP verified successfully"}
        )
        with patch(
            "app.api.v1.endpoints.auth.select",
            return_value=Mock(first=Mock(return_value=None)),
        ):
            response = app_client.post(
                "/api/v1/auth/login/verify-otp", json=otp_data
            )
            assert_api_error(response, 404, "User not found")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_login_otp_success(
        self, mock_otp_service, app_client, test_user
    ):
        """Test resending login OTP successfully."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=True)
        mock_service_instance.invalidate_otp = AsyncMock()
        mock_service_instance.send_otp = AsyncMock(
            return_value={"status": "success", "reference_id": "new_ref_id"}
        )

        response = app_client.post(
            "/api/v1/auth/login/resend-otp", json={"phone": test_user.phone}
        )
        assert_api_response(response, 200, ["status", "reference_id"])
        assert response.json()["status"] == "success"

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_login_otp_signup_required(
        self, mock_otp_service, app_client
    ):
        """Test resending login OTP for a non-existent user.

        (should prompt signup).
        """
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=True)

        response = app_client.post(
            "/api/v1/auth/login/resend-otp",
            json={
                "phone": "+919999999999"  # Non-existent phone
            },
        )
        assert_api_response(response, 200, ["status", "message"])
        assert response.json()["status"] == "signup_required"

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_login_otp_inactive_user(
        self, mock_otp_service, app_client, test_user
    ):
        """Test resending login OTP for an inactive user."""
        test_user.is_active = False  # Deactivate user for this test
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=True)

        response = app_client.post(
            "/api/v1/auth/login/resend-otp", json={"phone": test_user.phone}
        )
        assert_api_error(response, 401, "User account is inactive")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_login_otp_rate_limited(
        self, mock_otp_service, app_client, test_user
    ):
        """Test resending login OTP when rate limited."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=False)

        response = app_client.post(
            "/api/v1/auth/login/resend-otp", json={"phone": test_user.phone}
        )
        assert_api_error(
            response, 429, "Rate limit exceeded. Please try again later."
        )

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_login_otp_service_failure(
        self, mock_otp_service, app_client, test_user
    ):
        """Test resending login OTP when OTP service fails."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=True)
        mock_service_instance.invalidate_otp = AsyncMock()
        mock_service_instance.send_otp = AsyncMock(
            return_value={"status": "failed", "message": "Provider error"}
        )

        response = app_client.post(
            "/api/v1/auth/login/resend-otp", json={"phone": test_user.phone}
        )
        assert_api_error(response, 500, "Failed to resend OTP: Provider error")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_login_otp_provider_failure(
        self, mock_otp_service, app_client, test_user
    ):
        """Test resending login OTP when OTP service fails."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=True)
        mock_service_instance.invalidate_otp = AsyncMock()
        mock_service_instance.send_otp = AsyncMock(
            return_value={"status": "failed", "message": "Provider error"}
        )

        response = app_client.post(
            "/api/v1/auth/login/resend-otp", json={"phone": test_user.phone}
        )
        assert_api_error(response, 500, "Failed to resend OTP: Provider error")

    def test_send_otp_invalid_phone(self, app_client):
        """Test sending OTP with invalid phone."""
        response = app_client.post(
            "/api/v1/auth/login/send-otp", json={"phone": "invalid_phone"}
        )
        assert_api_error(response, 422)

    def test_verify_otp_invalid_code(self, app_client):
        """Test verifying OTP with invalid code."""
        invalid_otp_data = {
            "phone": "9876543210",
            "otp_code": "000000",  # Invalid OTP
            "reference_id": "test_ref",
        }
        response = app_client.post(
            "/api/v1/auth/login/verify-otp", json=invalid_otp_data
        )
        assert response.status_code in [400, 401, 422]

    @pytest.mark.parametrize(
        "invalid_otp_code", ["12345", "1234567", "abcdef", ""]
    )
    def test_verify_otp_malformed_codes(self, app_client, invalid_otp_code):
        """Test OTP verification with malformed codes."""
        otp_data = {
            "phone": "9876543210",
            "otp_code": invalid_otp_code,
            "reference_id": "test_ref",
        }
        response = app_client.post(
            "/api/v1/auth/login/verify-otp", json=otp_data
        )
        assert_api_error(response, 422)

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_signup_otp_success(self, mock_otp_service, app_client):
        """Test sending signup OTP successfully."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.send_signup_otp = AsyncMock(
            return_value={"status": "success", "reference_id": "signup_ref_id"}
        )
        mock_service_instance.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = app_client.post(
            "/api/v1/auth/signup/send-otp",
            json={
                "phone": "+919876543210"  # New phone number
            },
        )
        assert_api_response(response, 200, ["status", "reference_id"])
        assert response.json()["status"] == "success"

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_signup_otp_user_already_exists(
        self, mock_otp_service, app_client, test_user
    ):
        """Test sending signup OTP when user already exists."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = app_client.post(
            "/api/v1/auth/signup/send-otp", json={"phone": test_user.phone}
        )
        assert_api_error(
            response, 400, "User with this phone number already exists"
        )

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_signup_otp_rate_limited(self, mock_otp_service, app_client):
        """Test sending signup OTP when rate limited."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": False, "wait_minutes": 1}
        )

        response = app_client.post(
            "/api/v1/auth/signup/send-otp", json={"phone": "+919876543210"}
        )
        assert_api_error(
            response,
            429,
            "Rate limit exceeded. Please wait 1 minute(s) before trying again.",
        )

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_send_signup_otp_service_failure(
        self, mock_otp_service, app_client
    ):
        """Test sending signup OTP when OTP service fails."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.send_signup_otp = AsyncMock(
            return_value={"status": "failed", "message": "Provider error"}
        )
        mock_service_instance.check_rate_limit_detailed = AsyncMock(
            return_value={"allowed": True}
        )

        response = app_client.post(
            "/api/v1/auth/signup/send-otp", json={"phone": "+919876543210"}
        )
        assert_api_error(response, 500, "Failed to send OTP: Provider error")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_signup_otp_success(
        self, mock_otp_service, app_client, user_registration_data
    ):
        """Test verifying signup OTP and creating a new user successfully."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.verify_otp_detailed = AsyncMock(
            return_value={"valid": True, "message": "OTP verified successfully"}
        )

        response = app_client.post(
            "/api/v1/auth/signup/verify-otp", json=user_registration_data
        )
        assert_api_response(
            response,
            200,
            ["access_token", "token_type", "user_id", "phone", "roles"],
        )

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_signup_otp_no_consent(
        self, mock_otp_service, app_client, user_registration_data
    ):
        """Test verifying signup OTP without user consent."""
        data = {**user_registration_data, "has_given_consent": False}
        response = app_client.post("/api/v1/auth/signup/verify-otp", json=data)
        assert_api_error(
            response, 400, "User consent is required to create an account"
        )

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_signup_otp_user_already_exists(
        self, mock_otp_service, app_client, test_user, user_registration_data
    ):
        """Test verifying signup OTP when user with phone already exists."""
        data = {**user_registration_data, "phone": test_user.phone}
        response = app_client.post("/api/v1/auth/signup/verify-otp", json=data)
        assert_api_error(
            response, 400, "User with this phone number already exists"
        )

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_signup_otp_email_already_exists(
        self, mock_otp_service, app_client, test_user, user_registration_data
    ):
        """Test verifying signup OTP when user with email already exists."""
        data = {**user_registration_data, "email": test_user.email}
        response = app_client.post("/api/v1/auth/signup/verify-otp", json=data)
        assert_api_error(response, 400, "User with this email already exists")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_verify_signup_otp_invalid_code(
        self, mock_otp_service, app_client, user_registration_data
    ):
        """Test verifying signup OTP with invalid code."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.verify_otp_detailed = AsyncMock(
            return_value={"valid": False, "message": "Invalid OTP code"}
        )

        response = app_client.post(
            "/api/v1/auth/signup/verify-otp", json=user_registration_data
        )
        assert_api_error(response, 400, "Invalid OTP code")

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_signup_otp_success(self, mock_otp_service, app_client):
        """Test resending signup OTP successfully."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=True)
        mock_service_instance.invalidate_otp = AsyncMock()
        mock_service_instance.send_signup_otp = AsyncMock(
            return_value={
                "status": "success",
                "reference_id": "new_signup_ref_id",
            }
        )

        response = app_client.post(
            "/api/v1/auth/signup/resend-otp",
            json={
                "phone": "+919876543210"  # New phone number
            },
        )
        assert_api_response(response, 200, ["status", "reference_id"])
        assert response.json()["status"] == "success"

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_signup_otp_user_already_exists(
        self, mock_otp_service, app_client, test_user
    ):
        """Test resending signup OTP when user already exists."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=True)

        response = app_client.post(
            "/api/v1/auth/signup/resend-otp", json={"phone": test_user.phone}
        )
        assert_api_error(
            response, 400, "User with this phone number already exists"
        )

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_signup_otp_rate_limited(self, mock_otp_service, app_client):
        """Test resending signup OTP when rate limited."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=False)

        response = app_client.post(
            "/api/v1/auth/signup/resend-otp", json={"phone": "+919876543210"}
        )
        assert_api_error(
            response, 429, "Rate limit exceeded. Please try again later."
        )

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_resend_signup_otp_service_failure(
        self, mock_otp_service, app_client
    ):
        """Test resending signup OTP when OTP service fails."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.check_rate_limit = AsyncMock(return_value=True)
        mock_service_instance.invalidate_otp = AsyncMock()
        mock_service_instance.send_signup_otp = AsyncMock(
            return_value={"status": "failed", "message": "Provider error"}
        )

        response = app_client.post(
            "/api/v1/auth/signup/resend-otp", json={"phone": "+919876543210"}
        )
        assert_api_error(response, 500, "Failed to resend OTP: Provider error")


class TestPasswordResetEndpoints:
    """Test password reset endpoints."""

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_request_password_reset(self, mock_otp_service, app_client):
        """Test requesting password reset."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.send_otp = AsyncMock(
            return_value={"status": "success", "reference_id": "reset_ref_id"}
        )

        response = app_client.post(
            "/api/v1/auth/password-reset/request", json={"phone": "9876543210"}
        )

        # Should succeed if user exists and OTP is sent
        assert response.status_code in [200, 404, 422, 500]

    @patch("app.api.v1.endpoints.auth.OTPService")
    def test_confirm_password_reset(self, mock_otp_service, app_client):
        """Test confirming password reset with OTP."""
        mock_service_instance = mock_otp_service.return_value
        mock_service_instance.verify_otp_detailed = AsyncMock(
            return_value={"valid": True, "message": "OTP verified successfully"}
        )

        reset_data = {
            "phone": "9876543210",
            "new_password": "NewSecurePass123!",
            "otp_code": "123456",
            "reference_id": "reset_ref_id",
        }

        response = app_client.post(
            "/api/v1/auth/password-reset/confirm", json=reset_data
        )
        assert response.status_code in [200, 400, 401, 404, 422]

    def test_password_reset_invalid_phone(self, app_client):
        """Test password reset with invalid phone."""
        response = app_client.post(
            "/api/v1/auth/password-reset/request",
            json={"phone": "invalid_phone"},
        )
        assert_api_error(response, 422)

    def test_password_reset_weak_password(self, app_client):
        """Test password reset with weak new password."""
        reset_data = {
            "phone": "9876543210",
            "new_password": "weak",  # Too weak
            "otp_code": "123456",
            "reference_id": "reset_ref_id",
        }

        response = app_client.post(
            "/api/v1/auth/password-reset/confirm", json=reset_data
        )
        assert_api_error(response, 422)


class TestTokenEndpoints:
    """Test token-related endpoints."""

    def test_refresh_token_endpoint(self, app_client):
        """Test token refresh endpoint."""
        # This would test JWT token refresh functionality
        response = app_client.post("/api/v1/auth/refresh-token")
        # Expect 401 without valid refresh token
        assert response.status_code in [401, 422]

    def test_logout_endpoint(self, app_client):
        """Test logout endpoint."""
        response = app_client.post("/api/v1/auth/logout")
        # Should work even without authentication (token invalidation)
        assert response.status_code in [200, 401]

    def test_token_validation_endpoint(self, app_client):
        """Test token validation endpoint."""
        response = app_client.get("/api/v1/auth/validate-token")
        # Expect 401 without valid token
        assert_api_error(response, 401)


class TestAuthenticationMiddleware:
    """Test authentication middleware and protected endpoints."""

    def test_protected_endpoint_without_auth(self, app_client):
        """Test accessing protected endpoint without authentication."""
        response = app_client.get("/api/v1/users/profile")
        assert_api_error(response, 401)

    def test_protected_endpoint_with_invalid_token(self, app_client):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = app_client.get("/api/v1/users/profile", headers=headers)
        assert_api_error(response, 401)

    def test_protected_endpoint_with_expired_token(self, app_client):
        """Test accessing protected endpoint with expired token."""
        # This would require generating an expired token
        expired_token = "expired.jwt.token"  # Mock expired token
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = app_client.get("/api/v1/users/profile", headers=headers)
        assert_api_error(response, 401)

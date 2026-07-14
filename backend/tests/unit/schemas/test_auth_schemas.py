"""Consolidated authentication schema validation tests.

Tests Pydantic schema validation with parameterized test cases.
"""

import pytest
from pydantic import ValidationError

from app.schemas.auth_validation import (
    OTPSendValidation,
    OTPValidation,
    PasswordChangeValidation,
    TokenValidation,
    UserLoginValidation,
    UserProfileUpdateValidation,
    UserRegistrationValidation,
)
from tests.data.test_data import TestData


class TestUserRegistrationValidation:
    """Test user registration schema validation."""

    def test_valid_registration_data(self, user_registration_data):
        """Test valid user registration."""
        user = UserRegistrationValidation(**user_registration_data)
        assert user.phone == "+919876543210"
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.has_given_consent is True

    @pytest.mark.parametrize(
        "phone,expected_formatted",
        [
            ("9876543210", "+919876543210"),
            ("+919876543210", "+919876543210"),
            ("91 9876543210", "+919876543210"),
            ("919876543210", "+919876543210"),
        ],
    )
    def test_phone_formatting(
        self, user_registration_data, phone, expected_formatted
    ):
        """Test phone number formatting in registration."""
        data = {**user_registration_data, "phone": phone}
        user = UserRegistrationValidation(**data)
        assert user.phone == expected_formatted

    @pytest.mark.parametrize(
        "invalid_phone",
        [
            "5876543210",  # Starts with 5
            "4123456789",  # Starts with 4
            "987654321",  # Too short
            "98765432100",  # Too long
            "abcd123456",  # Contains letters
        ],
    )
    def test_invalid_phones(self, user_registration_data, invalid_phone):
        """Test rejection of invalid phone numbers."""
        data = {**user_registration_data, "phone": invalid_phone}
        with pytest.raises(ValidationError):
            UserRegistrationValidation(**data)

    @pytest.mark.parametrize("invalid_name", TestData.INVALID_NAMES)
    def test_invalid_names(self, user_registration_data, invalid_name):
        """Test rejection of invalid names."""
        data = {**user_registration_data, "name": invalid_name}
        with pytest.raises(ValidationError):
            UserRegistrationValidation(**data)

    @pytest.mark.parametrize("invalid_email", TestData.INVALID_EMAILS)
    def test_invalid_emails(self, user_registration_data, invalid_email):
        """Test rejection of invalid emails."""
        data = {**user_registration_data, "email": invalid_email}
        with pytest.raises(ValidationError):
            UserRegistrationValidation(**data)

    @pytest.mark.parametrize("invalid_password", TestData.INVALID_PASSWORDS)
    def test_invalid_passwords(self, user_registration_data, invalid_password):
        """Test rejection of invalid passwords."""
        data = {
            **user_registration_data,
            "password": invalid_password,
            "confirm_password": invalid_password,
        }
        with pytest.raises(ValidationError):
            UserRegistrationValidation(**data)

    def test_password_confirmation_mismatch(self, user_registration_data):
        """Test password confirmation validation."""
        data = {
            **user_registration_data,
            "password": "SecurePass123!",
            "confirm_password": "DifferentPass123!",
        }
        with pytest.raises(ValidationError):
            UserRegistrationValidation(**data)

    @pytest.mark.parametrize("consent_value", [False, None])
    def test_consent_requirement(self, user_registration_data, consent_value):
        """Test that consent is required."""
        data = {**user_registration_data, "has_given_consent": consent_value}
        with pytest.raises(ValidationError):
            UserRegistrationValidation(**data)

    @pytest.mark.parametrize("gender", ["male", "female", "other"])
    def test_valid_genders(self, user_registration_data, gender):
        """Test valid gender values."""
        data = {**user_registration_data, "gender": gender}
        user = UserRegistrationValidation(**data)
        assert user.gender == gender

    def test_invalid_gender(self, user_registration_data):
        """Test invalid gender values."""
        data = {**user_registration_data, "gender": "invalid"}
        with pytest.raises(ValidationError):
            UserRegistrationValidation(**data)


class TestUserLoginValidation:
    """Test user login schema validation."""

    def test_valid_login_data(self, user_login_data):
        """Test valid login data."""
        login = UserLoginValidation(**user_login_data)
        assert login.phone == "+919876543210"
        assert login.password == "SecurePass123!"

    def test_login_with_email(self):
        """Test login with email instead of phone."""
        data = {"email": "test@example.com", "password": "SecurePass123!"}
        login = UserLoginValidation(**data)
        assert login.email == "test@example.com"
        assert login.password == "SecurePass123!"

    @pytest.mark.parametrize("invalid_phone", TestData.INVALID_PHONES)
    def test_invalid_login_phones(self, invalid_phone):
        """Test rejection of invalid phones in login."""
        data = {"phone": invalid_phone, "password": "SecurePass123!"}
        with pytest.raises(ValidationError):
            UserLoginValidation(**data)

    def test_missing_credentials(self):
        """Test validation with missing phone/email and password."""
        with pytest.raises(ValidationError):
            UserLoginValidation()

        with pytest.raises(ValidationError):
            UserLoginValidation(phone="9876543210")

        with pytest.raises(ValidationError):
            UserLoginValidation(password="SecurePass123!")


class TestOTPValidation:
    """Test OTP schema validation."""

    def test_valid_otp_data(self, otp_data):
        """Test valid OTP data."""
        otp = OTPValidation(**otp_data)
        assert otp.phone == "+919876543210"
        assert otp.otp_code == "123456"

    @pytest.mark.parametrize(
        "invalid_otp",
        [
            "123",  # Too short
            "123456789",  # Too long
            "abcdef",  # Non-numeric
            "",  # Empty
        ],
    )
    def test_invalid_otp_codes(self, otp_data, invalid_otp):
        """Test rejection of invalid OTP codes."""
        data = {**otp_data, "otp_code": invalid_otp}
        with pytest.raises(ValidationError):
            OTPValidation(**data)

    def test_otp_send_validation(self):
        """Test OTP send request validation."""
        data = {"phone": "9876543210", "request_type": "login"}
        otp_send = OTPSendValidation(**data)
        assert otp_send.phone == "+919876543210"


class TestPasswordChangeValidation:
    """Test password change schema validation."""

    def test_valid_password_change(self):
        """Test valid password change data."""
        data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        }
        change = PasswordChangeValidation(**data)
        assert change.current_password == "OldPass123!"
        assert change.new_password == "NewPass123!"

    def test_password_change_mismatch(self):
        """Test password change with mismatched confirmation."""
        data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass123!",
            "confirm_password": "DifferentPass123!",
        }
        with pytest.raises(ValidationError):
            PasswordChangeValidation(**data)

    def test_weak_new_password(self):
        """Test password change with weak new password."""
        data = {
            "current_password": "OldPass123!",
            "new_password": "weak",
            "confirm_password": "weak",
        }
        with pytest.raises(ValidationError):
            PasswordChangeValidation(**data)


class TestUserProfileUpdateValidation:
    """Test user profile update schema validation."""

    def test_partial_profile_update(self):
        """Test partial profile updates."""
        # Should allow updating just name
        data = {"name": "Updated Name"}
        update = UserProfileUpdateValidation(**data)
        assert update.name == "Updated Name"

        # Should allow updating just current_place
        data = {"current_place": "New City, India"}
        update = UserProfileUpdateValidation(**data)
        assert update.current_place == "New City, India"

    def test_email_update_validation(self):
        """Test email update validation."""
        data = {"email": "newemail@example.com"}
        update = UserProfileUpdateValidation(**data)
        assert update.email == "newemail@example.com"

        # Invalid email should be rejected
        with pytest.raises(ValidationError):
            UserProfileUpdateValidation(email="invalid.email")

    def test_profile_update_restrictions(self):
        """Test that certain fields cannot be updated."""
        # Phone number updates might be restricted
        # This depends on your business logic
        pass


class TestTokenValidation:
    """Test token validation schemas."""

    def test_valid_token(self):
        """Test valid token validation."""
        data = {"access_token": "valid.jwt.token"}
        token = TokenValidation(**data)
        assert token.access_token == "valid.jwt.token"

    def test_empty_token(self):
        """Test empty token rejection."""
        with pytest.raises(ValidationError):
            TokenValidation(access_token="")

        with pytest.raises(ValidationError):
            TokenValidation(access_token=None)

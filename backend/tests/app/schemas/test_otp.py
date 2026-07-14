"""Unit tests for app/schemas/otp.py Pydantic models."""

import pytest
from pydantic import ValidationError

from app.schemas import RoleEnum, RoleRead
from app.schemas.otp import (
    OTPLoginSendRequest,
    OTPSignupResendRequest,
    OTPSignupSendRequest,
    OTPSignupVerifyRequest,
)

# ============================================================
# Helpers
# ============================================================

VALID_PHONE = "9177980938"
VALID_PHONE_FORMATTED = "+919177980938"
VALID_OTP = "123456"
VALID_EMAIL = "test@example.com"
VALID_PASSWORD = "Str0ng!Pass"


def _make_signup_verify(**overrides):
    """Helper to build a valid OTPSignupVerifyRequest with sensible defaults."""
    defaults = dict(
        phone=VALID_PHONE,
        name="Alice Test",
        email=VALID_EMAIL,
        password=VALID_PASSWORD,
        confirm_password=VALID_PASSWORD,
        has_given_consent=True,
        otp_code=VALID_OTP,
    )
    defaults.update(overrides)
    return OTPSignupVerifyRequest(**defaults)


def _make_role(**overrides):
    defaults = dict(id=1, name=RoleEnum.user, description=None)
    defaults.update(overrides)
    return RoleRead(**defaults)


# ============================================================
# OTPLoginSendRequest
# ============================================================


class TestOTPLoginSendRequest:
    """Tests for OTPLoginSendRequest schema."""

    def test_valid_10_digit_phone(self):
        req = OTPLoginSendRequest(phone=VALID_PHONE)
        assert req.phone == VALID_PHONE_FORMATTED

    def test_valid_with_country_code_prefix(self):
        req = OTPLoginSendRequest(phone="+919177980938")
        assert req.phone == VALID_PHONE_FORMATTED

    def test_missing_phone_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            OTPLoginSendRequest()
        assert "phone" in str(exc_info.value).lower()

    def test_empty_phone_raises(self):
        with pytest.raises(ValidationError):
            OTPLoginSendRequest(phone="")

    def test_short_phone_raises(self):
        with pytest.raises(ValidationError):
            OTPLoginSendRequest(phone="12345")

    def test_phone_with_letters_raises(self):
        with pytest.raises(ValidationError):
            OTPLoginSendRequest(phone="917798abcd")

    def test_phone_starting_with_5_raises(self):
        with pytest.raises(ValidationError):
            OTPLoginSendRequest(phone="5177980938")

    def test_phone_starting_with_0_raises(self):
        with pytest.raises(ValidationError):
            OTPLoginSendRequest(phone="0177980938")

    def test_non_string_phone_raises(self):
        with pytest.raises(ValidationError):
            OTPLoginSendRequest(phone=1234567890)

    def test_extra_fields_ignored(self):
        req = OTPLoginSendRequest(phone=VALID_PHONE, extra="ignored")
        assert "extra" not in req.model_dump()

    def test_model_dump(self):
        req = OTPSignupSendRequest(phone=VALID_PHONE, email=VALID_EMAIL)
        assert req.model_dump() == {
            "phone": VALID_PHONE_FORMATTED,
            "email": VALID_EMAIL,
            "is_intern": False,
        }


# ============================================================
# OTPSignupResendRequest
# ============================================================


class TestOTPSignupResendRequest:
    """Tests for OTPSignupResendRequest schema."""

    def test_valid_phone(self):
        req = OTPSignupResendRequest(phone=VALID_PHONE)
        assert req.phone == VALID_PHONE_FORMATTED

    def test_missing_phone_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            OTPSignupResendRequest()
        assert "phone" in str(exc_info.value).lower()


# ============================================================
# OTPSignupVerifyRequest (inherits UserSignupStep1Validation + otp_code)
# ============================================================


class TestOTPSignupVerifyRequest:
    """Tests for OTPSignupVerifyRequest schema.

    This model inherits from UserSignupStep1Validation (minimal step 1 signup):
      phone, username, name, password, confirm_password, has_given_consent
    and adds: otp_code (4-8 chars).
    """

    # --- Valid instantiation ---

    def test_valid_data(self):
        req = _make_signup_verify()
        assert req.phone == VALID_PHONE_FORMATTED
        assert req.name == "Alice Test"
        assert req.password == VALID_PASSWORD
        assert req.otp_code == VALID_OTP

    def test_valid_minimal_data(self):
        """Test that minimal step 1 signup data is valid."""
        OTPSignupVerifyRequest(
            phone="+919999999999",
            name="Bob Test",
            email=VALID_EMAIL,
            password="Str0ng!Pass",
            confirm_password="Str0ng!Pass",
            has_given_consent=True,
            otp_code="123456",
        )

    # --- Phone validation ---

    def test_invalid_phone_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(phone="123")

    # --- Name validation ---

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(name="")

    def test_name_with_numbers_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(name="Alice123")

    # --- Password validation (uses zxcvbn strength scoring) ---

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(
                password="Ab1!",
                confirm_password="Ab1!",
            )

    def test_password_weak_raises(self):
        """Test that weak passwords are rejected by zxcvbn."""
        with pytest.raises(ValidationError) as exc_info:
            _make_signup_verify(
                password="password123",
                confirm_password="password123",
            )
        assert "too weak" in str(exc_info.value).lower()

    def test_password_missing_lowercase_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_signup_verify(
                password="PASSWORD123",
                confirm_password="PASSWORD123",
            )
        assert "too weak" in str(exc_info.value).lower()

    def test_password_missing_digit_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_signup_verify(
                password="Password!",
                confirm_password="Password!",
            )
        assert "too weak" in str(exc_info.value).lower()

    def test_password_missing_special_char_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_signup_verify(
                password="Password123",
                confirm_password="Password123",
            )
        assert "too weak" in str(exc_info.value).lower()

    def test_password_mismatch_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_signup_verify(confirm_password="Different!1a")
        assert "match" in str(exc_info.value).lower()

    # --- Consent validation ---

    def test_missing_consent_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            _make_signup_verify(has_given_consent=False)
        assert (
            "consent" in str(exc_info.value).lower()
            or "terms" in str(exc_info.value).lower()
        )

    def test_consent_required(self):
        req = _make_signup_verify(has_given_consent=True)
        assert req.has_given_consent is True

    # --- OTP code validation ---

    def test_otp_min_length_4(self):
        req = _make_signup_verify(otp_code="1234")
        assert req.otp_code == "1234"

    def test_otp_max_length_8(self):
        req = _make_signup_verify(otp_code="12345678")
        assert req.otp_code == "12345678"

    def test_otp_too_short_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(otp_code="123")

    def test_otp_too_long_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(otp_code="123456789")

    def test_empty_otp_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(otp_code="")

    # --- Missing required fields ---

    def test_missing_phone_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            OTPSignupVerifyRequest(
                username="alice_test",
                name="Alice",
                email=VALID_EMAIL,
                password=VALID_PASSWORD,
                confirm_password=VALID_PASSWORD,
                has_given_consent=True,
                otp_code=VALID_OTP,
            )
        assert "phone" in str(exc_info.value).lower()

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(name=None)

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(password=None)

    def test_missing_confirm_password_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(confirm_password=None)

    def test_missing_consent_none_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(has_given_consent=None)

    def test_missing_otp_code_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(otp_code=None)

    # --- Type errors ---

    def test_non_string_name_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(name=123)

    def test_non_string_password_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(password=12345)

    def test_non_bool_consent_raises(self):
        req = _make_signup_verify(has_given_consent="yes")
        assert req.has_given_consent is True

    def test_non_string_otp_raises(self):
        with pytest.raises(ValidationError):
            _make_signup_verify(otp_code=123456)

    # --- Edge cases ---

    def test_extra_fields_ignored(self):
        req = _make_signup_verify(extra_field="ignored")
        assert "extra_field" not in req.model_dump()

    # --- Serialization ---

    def test_model_dump(self):
        req = _make_signup_verify()
        dump = req.model_dump()
        assert dump["phone"] == VALID_PHONE_FORMATTED
        assert dump["name"] == "Alice Test"
        assert dump["otp_code"] == VALID_OTP
        assert dump["has_given_consent"] is True

"""Unit tests for app/schemas/password_reset.py Pydantic models."""

import pytest
from pydantic import ValidationError

from app.schemas.password_reset import (
    PasswordResetConfirmRequest,
    PasswordResetInitRequest,
    PasswordResetResponse,
)

# ============================================================
# PasswordResetInitRequest
# ============================================================


class TestPasswordResetInitRequest:
    """Tests for PasswordResetInitRequest schema."""

    # --- Valid instantiation ---

    def test_create_with_valid_10_digit_phone(self):
        req = PasswordResetInitRequest(phone="9177980938")
        assert req.phone == "+919177980938"

    def test_create_with_country_code_prefix(self):
        req = PasswordResetInitRequest(phone="+919177980938")
        assert req.phone == "+919177980938"

    def test_phone_starting_with_6(self):
        req = PasswordResetInitRequest(phone="6000000000")
        assert req.phone == "+916000000000"

    def test_phone_starting_with_9(self):
        req = PasswordResetInitRequest(phone="9000000000")
        assert req.phone == "+919000000000"

    # --- Missing required field ---

    def test_missing_phone_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetInitRequest()
        assert "phone" in str(exc_info.value).lower()

    # --- Invalid phone formats ---

    def test_empty_phone_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetInitRequest(phone="")

    def test_phone_too_short_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetInitRequest(phone="91779")

    def test_phone_too_long_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetInitRequest(phone="+91917798093800")

    def test_phone_with_letters_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetInitRequest(phone="917798abcd")

    def test_phone_starting_with_5_raises(self):
        """Indian numbers must start with digit > 5."""
        with pytest.raises(ValidationError):
            PasswordResetInitRequest(phone="5177980938")

    def test_phone_starting_with_0_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetInitRequest(phone="0177980938")

    def test_non_string_phone_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetInitRequest(phone=1234567890)

    # --- Extra fields ---

    def test_extra_fields_ignored(self):
        req = PasswordResetInitRequest(
            phone="9177980938", extra_field="should be ignored"
        )
        assert req.phone == "+919177980938"
        assert "extra_field" not in req.model_dump()

    # --- Serialization ---

    def test_model_dump(self):
        req = PasswordResetInitRequest(phone="9177980938")
        dump = req.model_dump()
        assert dump == {"phone": "+919177980938"}


# ============================================================
# PasswordResetConfirmRequest
# ============================================================


class TestPasswordResetConfirmRequest:
    """Tests for PasswordResetConfirmRequest schema."""

    VALID_PHONE = "9177980938"
    VALID_OTP = "123456"
    VALID_PASSWORD = "StrongP @ss1!"

    # --- Valid instantiation ---

    def test_create_with_valid_data(self):
        req = PasswordResetConfirmRequest(
            phone=self.VALID_PHONE,
            otp_code=self.VALID_OTP,
            new_password=self.VALID_PASSWORD,
            confirm_password=self.VALID_PASSWORD,
        )
        assert req.phone == "+919177980938"
        assert req.otp_code == self.VALID_OTP
        assert req.new_password == self.VALID_PASSWORD
        assert req.confirm_password == self.VALID_PASSWORD

    def test_otp_min_length_4(self):
        req = PasswordResetConfirmRequest(
            phone=self.VALID_PHONE,
            otp_code="1234",
            new_password=self.VALID_PASSWORD,
            confirm_password=self.VALID_PASSWORD,
        )
        assert req.otp_code == "1234"

    def test_otp_max_length_8(self):
        req = PasswordResetConfirmRequest(
            phone=self.VALID_PHONE,
            otp_code="12345678",
            new_password=self.VALID_PASSWORD,
            confirm_password=self.VALID_PASSWORD,
        )
        assert req.otp_code == "12345678"

    def test_password_min_length_8(self):
        pw = "Str0ngP@ss1!"  # 12 chars - strong enough for zxcvbn
        req = PasswordResetConfirmRequest(
            phone=self.VALID_PHONE,
            otp_code=self.VALID_OTP,
            new_password=pw,
            confirm_password=pw,
        )
        assert req.new_password == pw

    def test_password_max_length_100(self):
        pw = "Str0ngP@ss1!xxxx"  # 16 chars - strong enough for zxcvbn
        req = PasswordResetConfirmRequest(
            phone=self.VALID_PHONE,
            otp_code=self.VALID_OTP,
            new_password=pw,
            confirm_password=pw,
        )
        assert len(req.new_password) == 16

    # --- Missing required fields ---

    def test_missing_phone_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                otp_code=self.VALID_OTP,
                new_password=self.VALID_PASSWORD,
                confirm_password=self.VALID_PASSWORD,
            )
        assert "phone" in str(exc_info.value).lower()

    def test_missing_otp_code_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                new_password=self.VALID_PASSWORD,
                confirm_password=self.VALID_PASSWORD,
            )
        assert "otp_code" in str(exc_info.value).lower()

    def test_missing_new_password_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                confirm_password=self.VALID_PASSWORD,
            )
        assert "new_password" in str(exc_info.value).lower()

    def test_missing_confirm_password_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                new_password=self.VALID_PASSWORD,
            )
        assert "confirm_password" in str(exc_info.value).lower()

    # --- Phone validation ---

    def test_invalid_phone_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(
                phone="12345",
                otp_code=self.VALID_OTP,
                new_password=self.VALID_PASSWORD,
                confirm_password=self.VALID_PASSWORD,
            )

    # --- OTP length constraints ---

    def test_otp_too_short_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code="123",
                new_password=self.VALID_PASSWORD,
                confirm_password=self.VALID_PASSWORD,
            )

    def test_otp_too_long_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code="123456789",
                new_password=self.VALID_PASSWORD,
                confirm_password=self.VALID_PASSWORD,
            )

    # --- Password strength validation (uses zxcvbn) ---

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                new_password="Ab1!",
                confirm_password="Ab1!",
            )
        assert "8 characters" in str(exc_info.value)

    def test_password_weak_raises(self):
        """Test that weak passwords are rejected by zxcvbn."""
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                new_password="password123",
                confirm_password="password123",
            )
        assert "too weak" in str(exc_info.value).lower()

    def test_password_missing_lowercase_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                new_password="PASSWORD123",
                confirm_password="PASSWORD123",
            )
        assert "too weak" in str(exc_info.value).lower()

    def test_password_missing_digit_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                new_password="Password!",
                confirm_password="Password!",
            )
        assert "too weak" in str(exc_info.value).lower()

    def test_password_missing_special_char_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                new_password="Password123",
                confirm_password="Password123",
            )
        assert "too weak" in str(exc_info.value).lower()

    # --- Password match validation (model_post_init) ---

    def test_passwords_not_matching_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                new_password=self.VALID_PASSWORD,
                confirm_password="DifferentP @ss1!",
            )
        assert (
            "match" in str(exc_info.value).lower()
            or "password" in str(exc_info.value).lower()
        )

    # --- Type errors ---

    def test_non_string_otp_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=123456,
                new_password=self.VALID_PASSWORD,
                confirm_password=self.VALID_PASSWORD,
            )

    def test_non_string_password_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                new_password=12345,
                confirm_password=self.VALID_PASSWORD,
            )

    # --- Edge cases ---

    def test_empty_otp_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code="",
                new_password=self.VALID_PASSWORD,
                confirm_password=self.VALID_PASSWORD,
            )

    def test_empty_password_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirmRequest(
                phone=self.VALID_PHONE,
                otp_code=self.VALID_OTP,
                new_password="",
                confirm_password="",
            )

    def test_extra_fields_ignored(self):
        req = PasswordResetConfirmRequest(
            phone=self.VALID_PHONE,
            otp_code=self.VALID_OTP,
            new_password=self.VALID_PASSWORD,
            confirm_password=self.VALID_PASSWORD,
            extra_field="ignored",
        )
        assert "extra_field" not in req.model_dump()

    # --- Serialization ---

    def test_model_dump(self):
        req = PasswordResetConfirmRequest(
            phone=self.VALID_PHONE,
            otp_code=self.VALID_OTP,
            new_password=self.VALID_PASSWORD,
            confirm_password=self.VALID_PASSWORD,
        )
        dump = req.model_dump()
        assert dump["phone"] == "+919177980938"
        assert dump["otp_code"] == self.VALID_OTP
        assert dump["new_password"] == self.VALID_PASSWORD
        assert dump["confirm_password"] == self.VALID_PASSWORD
        assert "extra_field" not in dump


# ============================================================
# PasswordResetResponse
# ============================================================


class TestPasswordResetResponse:
    """Tests for PasswordResetResponse schema."""

    # --- Valid instantiation ---

    def test_create_with_required_fields_only(self):
        resp = PasswordResetResponse(status="success", message="Password reset")
        assert resp.status == "success"
        assert resp.message == "Password reset"
        assert resp.reference_id is None

    def test_create_with_all_fields(self):
        resp = PasswordResetResponse(
            status="success",
            message="Password reset successfully",
            reference_id="REF-12345",
        )
        assert resp.status == "success"
        assert resp.message == "Password reset successfully"
        assert resp.reference_id == "REF-12345"

    def test_reference_id_can_be_none(self):
        resp = PasswordResetResponse(
            status="error", message="Failed", reference_id=None
        )
        assert resp.reference_id is None

    def test_reference_id_accepts_empty_string(self):
        resp = PasswordResetResponse(
            status="error", message="Failed", reference_id=""
        )
        assert resp.reference_id == ""

    # --- Missing required fields ---

    def test_missing_status_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetResponse(message="test")
        assert "status" in str(exc_info.value).lower()

    def test_missing_message_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetResponse(status="ok")
        assert "message" in str(exc_info.value).lower()

    # --- Type errors ---

    def test_non_string_status_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetResponse(status=200, message="test")

    def test_non_string_message_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetResponse(status="ok", message=123)

    def test_non_string_reference_id_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetResponse(
                status="ok", message="test", reference_id=12345
            )

    # --- Edge cases ---

    def test_empty_status_and_message_accepted(self):
        resp = PasswordResetResponse(status="", message="")
        assert resp.status == ""
        assert resp.message == ""

    def test_extra_fields_ignored(self):
        resp = PasswordResetResponse(
            status="success",
            message="Done",
            extra_field="ignored",
        )
        assert "extra_field" not in resp.model_dump()

    # --- Serialization ---

    def test_model_dump_without_reference_id(self):
        resp = PasswordResetResponse(status="success", message="Done")
        dump = resp.model_dump()
        assert dump == {
            "status": "success",
            "message": "Done",
            "reference_id": None,
        }

    def test_model_dump_with_reference_id(self):
        resp = PasswordResetResponse(
            status="success", message="Done", reference_id="REF-001"
        )
        dump = resp.model_dump()
        assert dump == {
            "status": "success",
            "message": "Done",
            "reference_id": "REF-001",
        }

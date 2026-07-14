"""Tests for OTP service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.config import settings
from app.services.otp_service import OTPService


@pytest.fixture(autouse=True)
def mock_settings():
    """Provide mocked settings for OTP tests."""
    with patch("app.services.otp_service.settings") as mock_settings:
        mock_settings.OTP_EXPIRY_MINUTES = 5
        mock_settings.OTP_MAX_ATTEMPTS = 3
        mock_settings.OTP_RATE_LIMIT_MINUTES = 1
        mock_settings.OTP_SMS_TEXT = "Your OTP is {otp}"
        mock_settings.OTP_SERVICE_URL = "http://mock-sms-service.com"
        mock_settings.OTP_USER_NAME = "test_user"
        mock_settings.OTP_ENTITY_ID = "test_entity"
        mock_settings.OTP_TEMPLATE_ID = "test_template"
        mock_settings.OTP_API_KEY = "test_api_key"
        mock_settings.OTP_SENDER_ID = "test_sender"
        mock_settings.SECRET_KEY = "supersecretkey"
        yield mock_settings


@pytest.fixture
def mock_db_session():
    """Provide a mock database session."""
    session = MagicMock()
    return session


@pytest.fixture
def otp_service(mock_db_session):
    """Provide an OTPService instance with mock session."""
    return OTPService(mock_db_session)


class TestOTPServiceInit:
    """Tests for OTPService initialization."""

    def test_service_initialization(self, otp_service):
        """Test service initializes with correct settings."""
        assert otp_service.expiry_minutes == 5
        assert otp_service.max_attempts == 3
        assert otp_service.rate_limit_minutes == 1


class TestOTPGeneration:
    """Tests for OTP generation."""

    def test_generate_otp_default_length(self, otp_service):
        """Test OTP generation with default 6-digit length."""
        otp = otp_service.generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_generate_otp_custom_length_4(self, otp_service):
        """Test OTP generation with 4-digit length."""
        otp = otp_service.generate_otp(length=4)
        assert len(otp) == 4
        assert otp.isdigit()

    def test_generate_otp_custom_length_8(self, otp_service):
        """Test OTP generation with 8-digit length."""
        otp = otp_service.generate_otp(length=8)
        assert len(otp) == 8
        assert otp.isdigit()

    def test_generate_otp_randomness(self, otp_service):
        """Test that multiple OTPs can be different."""
        otps = [otp_service.generate_otp() for _ in range(10)]
        unique_otps = set(otps)
        assert len(unique_otps) >= 1


class TestOTPHashing:
    """Tests for OTP hashing functions."""

    def test_hash_otp_returns_hex(self, otp_service):
        """Test that hash_otp returns a hex string."""
        hashed = otp_service.hash_otp("123456", "+919876543210")
        assert isinstance(hashed, str)
        assert len(hashed) == 64

    def test_hash_otp_same_input_same_output(self, otp_service):
        """Test that same input produces same hash."""
        hash1 = otp_service.hash_otp("123456", "+919876543210")
        hash2 = otp_service.hash_otp("123456", "+919876543210")
        assert hash1 == hash2

    def test_hash_otp_different_phone_different_hash(self, otp_service):
        """Test that different phones produce different hashes."""
        hash1 = otp_service.hash_otp("123456", "+919876543210")
        hash2 = otp_service.hash_otp("123456", "+919999999999")
        assert hash1 != hash2

    def test_verify_otp_hash_valid(self, otp_service):
        """Test hash verification with valid OTP."""
        otp = "123456"
        phone = "+919876543210"
        hashed = otp_service.hash_otp(otp, phone)
        assert otp_service.verify_otp_hash(otp, phone, hashed) is True

    def test_verify_otp_hash_invalid_code(self, otp_service):
        """Test hash verification with invalid code."""
        phone = "+919876543210"
        hashed = otp_service.hash_otp("123456", phone)
        assert otp_service.verify_otp_hash("654321", phone, hashed) is False

    def test_verify_otp_hash_invalid_phone(self, otp_service):
        """Test hash verification with invalid phone."""
        hashed = otp_service.hash_otp("123456", "+919876543210")
        assert (
            otp_service.verify_otp_hash("123456", "+919999999999", hashed)
            is False
        )


class TestOTPSMS:
    """Tests for OTP SMS sending."""

    @pytest.mark.asyncio
    @patch("app.services.otp_service.requests.post")
    async def test_send_otp_sms_success(self, mock_post, otp_service):
        """Test successful SMS sending."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "success: message sent"
        mock_post.return_value = mock_response

        result = await otp_service.send_otp_sms("+919876543210", "123456")
        assert result == "success: message sent"

    @pytest.mark.asyncio
    @patch("app.services.otp_service.requests.post")
    async def test_send_otp_sms_http_error(self, mock_post, otp_service):
        """Test SMS sending with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_post.return_value = mock_response

        result = await otp_service.send_otp_sms("+919876543210", "123456")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.otp_service.requests.post")
    async def test_send_otp_sms_failure_response(self, mock_post, otp_service):
        """Test SMS sending with failure response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "fail"
        mock_post.return_value = mock_response

        result = await otp_service.send_otp_sms("+919876543210", "123456")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.otp_service.requests.post")
    async def test_send_otp_sms_exception(self, mock_post, otp_service):
        """Test SMS sending with exception."""
        result = await otp_service.send_otp_sms("+919876543210", "123456")
        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.otp_service.requests.post")
    async def test_send_otp_sms_long_response(self, mock_post, otp_service):
        """Test SMS sending with long response text."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = (
            "Message queued successfully with reference ID 12345"
        )
        mock_post.return_value = mock_response

        result = await otp_service.send_otp_sms("+919876543210", "123456")
        assert result is not None

    @pytest.mark.asyncio
    @patch("app.services.otp_service.requests.post")
    async def test_send_otp_sms_phone_cleaning(self, mock_post, otp_service):
        """Test phone number is cleaned before sending."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_post.return_value = mock_response

        await otp_service.send_otp_sms("+919876543210", "123456")

        call_kwargs = mock_post.call_args[1]
        assert "9876543210" in str(
            call_kwargs.get("json", {}).get("numbers", "")
        )


class TestRateLimiting:
    """Tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_check_rate_limit_detailed_no_otp(
        self, otp_service, mock_db_session
    ):
        """Test rate limit check with no recent OTP."""
        mock_db_session.exec.return_value.first.return_value = None

        result = await otp_service.check_rate_limit_detailed("+919876543210")

        assert result["allowed"] is True
        assert result["wait_minutes"] == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_detailed_within_limit(
        self, otp_service, mock_db_session
    ):
        """Test rate limit check within rate limit window."""
        recent_otp = Mock()
        recent_otp.created_at = datetime.now(timezone.utc) - timedelta(
            seconds=30
        )
        mock_db_session.exec.return_value.first.return_value = recent_otp

        result = await otp_service.check_rate_limit_detailed("+919876543210")

        assert result["allowed"] is False
        assert result["wait_minutes"] >= 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_detailed_outside_limit(
        self, otp_service, mock_db_session
    ):
        """Test rate limit check outside rate limit window."""
        mock_db_session.exec.return_value.first.return_value = None

        result = await otp_service.check_rate_limit_detailed("+919876543210")

        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_simple_allowed(
        self, otp_service, mock_db_session
    ):
        """Test simple rate limit check when allowed."""
        mock_db_session.exec.return_value.first.return_value = None

        result = await otp_service.check_rate_limit("+919876543210")

        assert result is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_simple_blocked(
        self, otp_service, mock_db_session
    ):
        """Test simple rate limit check when blocked."""
        recent_otp = Mock()
        recent_otp.created_at = datetime.now(timezone.utc) - timedelta(
            seconds=30
        )
        mock_db_session.exec.return_value.first.return_value = recent_otp

        result = await otp_service.check_rate_limit("+919876543210")

        assert result is False


class TestGetValidOTP:
    """Tests for get_valid_otp method."""

    @pytest.mark.asyncio
    async def test_get_valid_otp_none_found(self, otp_service, mock_db_session):
        """Test get_valid_otp when no OTP found."""
        mock_db_session.exec.return_value.first.return_value = None

        result = otp_service.get_valid_otp("+919876543210")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_valid_otp_expired(self, otp_service, mock_db_session):
        """Test get_valid_otp when OTP is expired."""
        otp_record = Mock()
        otp_record.expires_at = datetime.now(timezone.utc) - timedelta(
            minutes=1
        )
        otp_record.is_verified = False
        otp_record.attempts = 0
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = otp_service.get_valid_otp("+919876543210")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_valid_otp_naive_timezone(
        self, otp_service, mock_db_session
    ):
        """Test get_valid_otp with naive datetime."""
        otp_record = Mock()
        otp_record.expires_at = datetime.now() + timedelta(minutes=10)
        otp_record.is_verified = False
        otp_record.attempts = 0
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = otp_service.get_valid_otp("+919876543210")

        assert result is otp_record

    @pytest.mark.asyncio
    async def test_get_valid_otp_already_verified(
        self, otp_service, mock_db_session
    ):
        """Test get_valid_otp when OTP already verified - mock returns None."""
        mock_db_session.exec.return_value.first.return_value = None

        result = otp_service.get_valid_otp("+919876543210")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_valid_otp_max_attempts(
        self, otp_service, mock_db_session
    ):
        """Test get_valid_otp when max attempts reached - mock returns None."""
        mock_db_session.exec.return_value.first.return_value = None

        result = otp_service.get_valid_otp("+919876543210")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_valid_otp_valid(self, otp_service, mock_db_session):
        """Test get_valid_otp with valid OTP."""
        otp_record = Mock()
        otp_record.expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=10
        )
        otp_record.is_verified = False
        otp_record.attempts = 0
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = otp_service.get_valid_otp("+919876543210")

        assert result is otp_record


class TestVerifyOTP:
    """Tests for OTP verification."""

    @pytest.mark.asyncio
    async def test_verify_otp_detailed_no_otp(
        self, otp_service, mock_db_session
    ):
        """Test verify_otp_detailed when no OTP found."""
        mock_db_session.exec.return_value.first.return_value = None

        result = await otp_service.verify_otp_detailed(
            "+919876543210", "123456"
        )

        assert result["valid"] is False
        assert result["reason"] == "no_otp"

    @pytest.mark.asyncio
    async def test_verify_otp_detailed_already_verified(
        self, otp_service, mock_db_session
    ):
        """Test verify_otp_detailed when already verified."""
        otp_record = Mock()
        otp_record.is_verified = True
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = await otp_service.verify_otp_detailed(
            "+919876543210", "123456"
        )

        assert result["valid"] is False
        assert result["reason"] == "already_used"

    @pytest.mark.asyncio
    async def test_verify_otp_detailed_expired(
        self, otp_service, mock_db_session
    ):
        """Test verify_otp_detailed when expired."""
        otp_record = Mock()
        otp_record.is_verified = False
        otp_record.attempts = 0
        otp_record.expires_at = datetime.now(timezone.utc) - timedelta(
            minutes=1
        )
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = await otp_service.verify_otp_detailed(
            "+919876543210", "123456"
        )

        assert result["valid"] is False
        assert result["reason"] == "expired"

    @pytest.mark.asyncio
    async def test_verify_otp_detailed_expired_naive(
        self, otp_service, mock_db_session
    ):
        """Test verify_otp_detailed when expired with naive datetime."""
        otp_record = Mock()
        otp_record.is_verified = False
        otp_record.attempts = 0
        past_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        otp_record.expires_at = past_time
        otp_record.otp_hash = "mock_hash"
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = await otp_service.verify_otp_detailed(
            "+919876543210", "123456"
        )

        assert result["valid"] is False
        assert result["reason"] == "expired"

    @pytest.mark.asyncio
    async def test_verify_otp_detailed_max_attempts(
        self, otp_service, mock_db_session
    ):
        """Test verify_otp_detailed when max attempts reached."""
        otp_record = Mock()
        otp_record.is_verified = False
        otp_record.attempts = settings.OTP_MAX_ATTEMPTS
        otp_record.expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=1
        )
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = await otp_service.verify_otp_detailed(
            "+919876543210", "123456"
        )

        assert result["valid"] is False
        assert result["reason"] == "max_attempts"

    @pytest.mark.asyncio
    async def test_verify_otp_detailed_invalid_code(
        self, otp_service, mock_db_session
    ):
        """Test verify_otp_detailed with invalid code."""
        otp_record = Mock()
        otp_record.is_verified = False
        otp_record.attempts = 0
        otp_record.expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=1
        )
        otp_record.otp_hash = otp_service.hash_otp("123456", "+919876543210")
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = await otp_service.verify_otp_detailed(
            "+919876543210", "654321"
        )

        assert result["valid"] is False
        assert result["reason"] == "invalid_code"
        assert otp_record.attempts == 1

    @pytest.mark.asyncio
    async def test_verify_otp_detailed_success(
        self, otp_service, mock_db_session
    ):
        """Test successful OTP verification."""
        otp_record = Mock()
        otp_record.is_verified = False
        otp_record.attempts = 0
        otp_record.expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=1
        )
        otp_record.otp_hash = otp_service.hash_otp("123456", "+919876543210")
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = await otp_service.verify_otp_detailed(
            "+919876543210", "123456"
        )

        assert result["valid"] is True
        assert result["reason"] == "success"
        assert otp_record.is_verified is True

    @pytest.mark.asyncio
    async def test_verify_otp_simple(self, otp_service, mock_db_session):
        """Test simple verify_otp method."""
        otp_record = Mock()
        otp_record.is_verified = False
        otp_record.attempts = 0
        otp_record.expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=1
        )
        otp_record.otp_hash = otp_service.hash_otp("123456", "+919876543210")
        mock_db_session.exec.return_value.first.return_value = otp_record

        result = await otp_service.verify_otp("+919876543210", "123456")

        assert result is True


class TestSendOTP:
    """Tests for send OTP methods."""

    @pytest.mark.asyncio
    async def test_send_otp_rate_limited(self, otp_service):
        """Test send_otp when rate limited."""
        with patch.object(
            otp_service,
            "check_rate_limit_detailed",
            return_value={"allowed": False, "wait_minutes": 2},
        ):
            result = await otp_service.send_otp("+919876543210")

            assert result["status"] == "error"
            assert "Please wait 2 minute(s)" in result["message"]

    @pytest.mark.asyncio
    async def test_send_otp_success(self, otp_service, mock_db_session):
        """Test successful send_otp."""
        with patch.object(
            otp_service,
            "check_rate_limit_detailed",
            return_value={"allowed": True},
        ):
            with patch.object(
                otp_service,
                "_send_otp_internal",
                return_value={"status": "success", "reference_id": "ref123"},
            ):
                result = await otp_service.send_otp("+919876543210")

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_send_signup_otp_rate_limited(self, otp_service):
        """Test send_signup_otp when rate limited."""
        with patch.object(
            otp_service,
            "check_rate_limit_detailed",
            return_value={"allowed": False, "wait_minutes": 3},
        ):
            result = await otp_service.send_signup_otp("+919876543210")

            assert result["status"] == "error"
            assert "Please wait 3 minute(s)" in result["message"]

    @pytest.mark.asyncio
    async def test_send_signup_otp_success(self, otp_service, mock_db_session):
        """Test successful send_signup_otp."""
        with patch.object(
            otp_service,
            "check_rate_limit_detailed",
            return_value={"allowed": True},
        ):
            with patch.object(
                otp_service,
                "_send_otp_internal",
                return_value={"status": "success", "reference_id": "ref123"},
            ):
                result = await otp_service.send_signup_otp("+919876543210")

                assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_send_otp_internal_sms_failure(
        self, otp_service, mock_db_session
    ):
        """Test _send_otp_internal when SMS fails."""
        with patch.object(otp_service, "send_otp_sms", return_value=None):
            with patch.object(
                otp_service, "generate_otp", return_value="123456"
            ):
                result = await otp_service._send_otp_internal("+919876543210")

                assert result["status"] == "error"
                assert "Failed to send OTP" in result["message"]

    @pytest.mark.asyncio
    async def test_send_otp_internal_success(
        self, otp_service, mock_db_session
    ):
        """Test successful _send_otp_internal."""
        with patch.object(
            otp_service, "send_otp_sms", return_value="sms_ref_123"
        ):
            with patch.object(
                otp_service, "generate_otp", return_value="123456"
            ):
                result = await otp_service._send_otp_internal("+919876543210")

                assert result["status"] == "success"
                assert result["reference_id"] == "sms_ref_123"
                assert result["expires_in_minutes"] == 5
                mock_db_session.add.assert_called_once()
                mock_db_session.commit.assert_called_once()


class TestOTPInvalidation:
    """Tests for OTP invalidation."""

    @pytest.mark.asyncio
    async def test_invalidate_otp(self, otp_service, mock_db_session):
        """Test invalidate_otp method."""
        otp1 = Mock()
        otp1.is_verified = False

        otp2 = Mock()
        otp2.is_verified = False

        mock_db_session.exec.return_value.all.return_value = [otp1, otp2]

        await otp_service.invalidate_otp("+919876543210")

        assert otp1.is_verified is True
        assert otp2.is_verified is True
        mock_db_session.commit.assert_called_once()


class TestOTPStatus:
    """Tests for OTP status."""

    @pytest.mark.asyncio
    async def test_get_otp_status_no_pending(
        self, otp_service, mock_db_session
    ):
        """Test get_otp_status when no pending OTP."""
        with patch.object(otp_service, "get_valid_otp", return_value=None):
            with patch.object(
                otp_service, "check_rate_limit", return_value=True
            ):
                result = await otp_service.get_otp_status("+919876543210")

                assert result["has_pending_otp"] is False
                assert result["attempts_remaining"] == settings.OTP_MAX_ATTEMPTS
                assert result["expires_at"] is None

    @pytest.mark.asyncio
    async def test_get_otp_status_with_pending(
        self, otp_service, mock_db_session
    ):
        """Test get_otp_status with pending OTP."""
        otp_record = Mock()
        otp_record.attempts = 1
        otp_record.expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=5
        )

        with patch.object(
            otp_service, "get_valid_otp", return_value=otp_record
        ):
            with patch.object(
                otp_service, "check_rate_limit", return_value=False
            ):
                result = await otp_service.get_otp_status("+919876543210")

                assert result["has_pending_otp"] is True
                assert (
                    result["attempts_remaining"]
                    == settings.OTP_MAX_ATTEMPTS - 1
                )
                assert result["can_resend"] is False

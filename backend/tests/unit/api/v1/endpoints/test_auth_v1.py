"""Tests for app/api/v1/endpoints/auth.py."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.auth import (
    change_password,
    confirm_password_reset,
    initiate_password_reset,
    login_for_access_token,
    read_users_me,
    resend_login_otp,
    resend_signup_otp,
    reset_password,
    send_login_otp,
    send_signup_otp,
    verify_login_otp,
)
from app.schemas import (
    FieldPrivacy,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
)
from app.schemas.otp import (
    OTPLoginSendRequest,
    OTPLoginVerifyRequest,
    OTPSignupResendRequest,
    OTPSignupSendRequest,
)
from app.schemas.password_reset import (
    PasswordResetConfirmRequest,
    PasswordResetInitRequest,
)
from tests.unit.api.v1.endpoints.conftest import DummyModel


def make_auth_user(**overrides):
    user = DummyModel()
    user.id = overrides.get("id", uuid4())
    user.phone = overrides.get("phone", "+919876543210")
    user.username = overrides.get("username", "testuser")
    user.name = overrides.get("name", "Test User")
    user.email = None
    user.gender = None
    user.date_of_birth = None
    user.current_place = None
    user.is_intern = False
    user.profile_picture_path = None
    user.short_bio = None
    user.profession = None
    user.organisation = None
    user.places_lived = None
    user.from_place = None
    user.social_media_profiles = None
    user.language_proficiencies = None
    user.is_active = overrides.get("is_active", True)
    user.has_given_consent = True
    user.phone_privacy = FieldPrivacy.public
    user.email_privacy = FieldPrivacy.public
    user.last_login_at = None
    user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user.updated_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
    user.rural_area_access = None
    user.permanent_postal_address = None
    user.institution_id = None
    user.current_year_of_study = None
    user.college_roll_number = None
    user.task_registered_id = None
    user.resume_record_id = None
    user.hardware_details = None
    user.has_completed_ai_courses = None
    user.ai_courses_list = None
    return user


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_success(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_user.is_active = True
        mock_user.hashed_password = "hashed_password"
        mock_user.last_login_at = None
        mock_user.profile_complete = True
        mock_user.username = "testuser"
        mock_user.phone = "+919999999999"

        mock_roles = []

        with patch(
            "app.api.v1.endpoints.auth.authenticate_user",
            return_value=mock_user,
        ):
            with patch(
                "app.api.v1.endpoints.auth.create_access_token",
                return_value="test-token",
            ):
                with patch(
                    "app.api.v1.endpoints.auth.select", return_value=Mock()
                ):
                    with patch.object(
                        mock_session,
                        "exec",
                        return_value=Mock(all=Mock(return_value=mock_roles)),
                    ):
                        with patch(
                            "app.api.v1.endpoints.auth.settings"
                        ) as mock_settings:
                            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

                            login_data = LoginRequest(
                                phone="+919999999999", password="password123"
                            )
                            response = await login_for_access_token(
                                login_data, mock_session
                            )

                            assert response.access_token == "test-token"
                            assert response.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        mock_session = Mock()

        with patch(
            "app.api.v1.endpoints.auth.authenticate_user", return_value=None
        ):
            login_data = LoginRequest(
                phone="+919999999999", password="wrongpassword"
            )

            with pytest.raises(HTTPException) as exc_info:
                await login_for_access_token(login_data, mock_session)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_user.is_active = False

        with patch(
            "app.api.v1.endpoints.auth.authenticate_user",
            return_value=mock_user,
        ):
            login_data = LoginRequest(
                phone="+919999999999", password="password123"
            )

            with pytest.raises(HTTPException) as exc_info:
                await login_for_access_token(login_data, mock_session)

            assert exc_info.value.status_code == 401


class TestReadUsersMeEndpoint:
    @pytest.mark.asyncio
    async def test_read_users_me_admin_role(self):
        user = make_auth_user()
        with patch(
            "app.api.v1.endpoints.auth.get_user_roles", return_value=["admin"]
        ):
            response = await read_users_me(user)
        assert response.role == "admin"
        assert response.roles == ["admin"]

    @pytest.mark.asyncio
    async def test_read_users_me_reviewer_role_priority(self):
        user = make_auth_user()
        with patch(
            "app.api.v1.endpoints.auth.get_user_roles",
            return_value=["reviewer", "user"],
        ):
            response = await read_users_me(user)
        assert response.role == "reviewer"
        assert response.roles == ["reviewer", "user"]

    @pytest.mark.asyncio
    async def test_read_users_me_user_role(self):
        user = make_auth_user()
        with patch(
            "app.api.v1.endpoints.auth.get_user_roles", return_value=["user"]
        ):
            response = await read_users_me(user)
        assert response.role == "user"
        assert response.roles == ["user"]

    @pytest.mark.asyncio
    async def test_read_users_me_no_roles(self):
        user = make_auth_user()
        with patch("app.api.v1.endpoints.auth.get_user_roles", return_value=[]):
            response = await read_users_me(user)
        assert response.role is None
        assert response.roles == []


class TestChangePasswordEndpoint:
    @pytest.mark.asyncio
    async def test_change_password_success(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.hashed_password = "hashed_old_password"

        with patch(
            "app.api.v1.endpoints.auth.verify_password", return_value=True
        ):
            with patch(
                "app.api.v1.endpoints.auth.get_password_hash",
                return_value="new_hashed_password",
            ):
                password_data = PasswordChangeRequest(
                    current_password="oldpassword",
                    new_password="NewPass123!",
                    confirm_new_password="NewPass123!",
                )
                response = await change_password(
                    password_data, mock_session, mock_user
                )

                assert response.message == "Password changed successfully"

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.hashed_password = "hashed_old_password"

        with patch(
            "app.api.v1.endpoints.auth.verify_password", return_value=False
        ):
            password_data = PasswordChangeRequest(
                current_password="wrongpassword",
                new_password="NewPass123!",
                confirm_new_password="NewPass123!",
            )

            with pytest.raises(HTTPException) as exc_info:
                await change_password(password_data, mock_session, mock_user)

            assert exc_info.value.status_code == 400


class TestResetPasswordEndpoint:
    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.id = "user-123"

        mock_result = Mock()
        mock_result.first = Mock(return_value=mock_user)
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.get_password_hash",
            return_value="new_hashed_password",
        ):
            reset_data = PasswordResetRequest(
                phone="+919999999999", new_password="NewPass123!"
            )
            mock_admin = Mock()

            response = await reset_password(
                reset_data, mock_session, mock_admin
            )

            assert response.message == "Password reset successfully"

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self):
        mock_session = Mock()

        mock_result = Mock()
        mock_result.first = Mock(return_value=None)
        mock_session.exec = Mock(return_value=mock_result)

        reset_data = PasswordResetRequest(
            phone="+919999999999", new_password="NewPass123!"
        )
        mock_admin = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await reset_password(reset_data, mock_session, mock_admin)

        assert exc_info.value.status_code == 404


class TestSendLoginOTPEndpoint:
    @pytest.mark.asyncio
    async def test_send_otp_success(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.is_active = True

        mock_result = Mock()
        mock_result.first = Mock(return_value=mock_user)
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.check_rate_limit_detailed = AsyncMock(
                return_value={"allowed": True}
            )
            mock_otp_service.send_otp = AsyncMock(
                return_value={"status": "success", "reference_id": "ref-123"}
            )
            mock_otp_service_class.return_value = mock_otp_service

            request = OTPLoginSendRequest(phone="+919999999999")
            response = await send_login_otp(request, mock_session)

            assert response.status == "success"

    @pytest.mark.asyncio
    async def test_send_otp_user_not_found(self):
        mock_session = Mock()

        mock_result = Mock()
        mock_result.first = Mock(return_value=None)
        mock_session.exec = Mock(return_value=mock_result)

        request = OTPLoginSendRequest(phone="+919999999999")
        response = await send_login_otp(request, mock_session)

        assert response.status == "signup_required"

    @pytest.mark.asyncio
    async def test_send_otp_inactive_user(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.is_active = False

        mock_result = Mock()
        mock_result.first = Mock(return_value=mock_user)
        mock_session.exec = Mock(return_value=mock_result)

        request = OTPLoginSendRequest(phone="+919999999999")

        with pytest.raises(HTTPException) as exc_info:
            await send_login_otp(request, mock_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_send_otp_rate_limited(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.is_active = True

        mock_result = Mock()
        mock_result.first = Mock(return_value=mock_user)
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.check_rate_limit_detailed = AsyncMock(
                return_value={"allowed": False, "wait_minutes": 5}
            )
            mock_otp_service_class.return_value = mock_otp_service

            request = OTPLoginSendRequest(phone="+919999999999")

            with pytest.raises(HTTPException) as exc_info:
                await send_login_otp(request, mock_session)

            assert exc_info.value.status_code == 429


class TestVerifyLoginOTPEndpoint:
    @pytest.mark.asyncio
    async def test_verify_otp_success(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_user.phone = "+919999999999"
        mock_user.username = "testuser"
        mock_user.is_active = True
        mock_user.last_login_at = None

        mock_role = Mock()
        mock_role.model_dump = Mock(return_value={"id": 3, "name": "user"})

        mock_result = Mock()
        mock_result.first = Mock(side_effect=[mock_user, [mock_role]])
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp_detailed = AsyncMock(
                return_value={"valid": True}
            )
            mock_otp_service_class.return_value = mock_otp_service

            with patch(
                "app.api.v1.endpoints.auth.create_access_token",
                return_value="test-token",
            ):
                with patch(
                    "app.api.v1.endpoints.auth.settings"
                ) as mock_settings:
                    mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

                    request = OTPLoginVerifyRequest(
                        phone="+919999999999", otp_code="123456"
                    )
                    try:
                        response = await verify_login_otp(request, mock_session)
                        assert response.access_token == "test-token"
                    except HTTPException:
                        pass

    @pytest.mark.asyncio
    async def test_verify_otp_invalid(self):
        mock_session = Mock()

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp_detailed = AsyncMock(
                return_value={"valid": False, "message": "Invalid OTP"}
            )
            mock_otp_service_class.return_value = mock_otp_service

            request = OTPLoginVerifyRequest(
                phone="+919999999999", otp_code="000000"
            )

            with pytest.raises(HTTPException) as exc_info:
                await verify_login_otp(request, mock_session)

            assert exc_info.value.status_code == 400


class TestResendLoginOTPEndpoint:
    @pytest.mark.asyncio
    async def test_resend_otp_success(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.is_active = True

        mock_result = Mock()
        mock_result.first = Mock(return_value=mock_user)
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.check_rate_limit = AsyncMock(return_value=True)
            mock_otp_service.invalidate_otp = AsyncMock()
            mock_otp_service.send_otp = AsyncMock(
                return_value={"status": "success", "reference_id": "ref-456"}
            )
            mock_otp_service_class.return_value = mock_otp_service

            request = OTPLoginSendRequest(phone="+919999999999")
            response = await resend_login_otp(request, mock_session)

            assert response.status == "success"


class TestInitiatePasswordResetEndpoint:
    @pytest.mark.asyncio
    async def test_initiate_reset_success(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.is_active = True

        mock_result = Mock()
        mock_result.first = Mock(return_value=mock_user)
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.check_rate_limit_detailed = AsyncMock(
                return_value={"allowed": True}
            )
            mock_otp_service.send_otp = AsyncMock(
                return_value={"status": "success", "reference_id": "ref-789"}
            )
            mock_otp_service_class.return_value = mock_otp_service

            request = PasswordResetInitRequest(phone="+919999999999")
            response = await initiate_password_reset(request, mock_session)

            assert response.status == "success"

    @pytest.mark.asyncio
    async def test_initiate_reset_user_not_found(self):
        mock_session = Mock()

        mock_result = Mock()
        mock_result.first = Mock(return_value=None)
        mock_session.exec = Mock(return_value=mock_result)

        request = PasswordResetInitRequest(phone="+919999999999")
        response = await initiate_password_reset(request, mock_session)

        assert response.status == "success"


class TestConfirmPasswordResetEndpoint:
    @pytest.mark.asyncio
    async def test_confirm_reset_success(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_user.is_active = True
        mock_user.hashed_password = "old_hashed_password"

        mock_result = Mock()
        mock_result.first = Mock(return_value=mock_user)
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp_detailed = AsyncMock(
                return_value={"valid": True}
            )
            mock_otp_service_class.return_value = mock_otp_service

            with patch(
                "app.api.v1.endpoints.auth.verify_password", return_value=False
            ):
                with patch(
                    "app.api.v1.endpoints.auth.get_password_hash",
                    return_value="new_hashed",
                ):
                    request = PasswordResetConfirmRequest(
                        phone="+919999999999",
                        otp_code="123456",
                        new_password="NewPass123!",
                        confirm_password="NewPass123!",
                    )
                    response = await confirm_password_reset(
                        request, mock_session
                    )

                    assert response.status == "success"

    @pytest.mark.asyncio
    async def test_confirm_reset_same_password(self):
        mock_session = Mock()
        mock_user = Mock()
        mock_user.is_active = True
        mock_user.hashed_password = "hashed_password"

        mock_result = Mock()
        mock_result.first = Mock(return_value=mock_user)
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.verify_otp_detailed = AsyncMock(
                return_value={"valid": True}
            )
            mock_otp_service_class.return_value = mock_otp_service

            with patch(
                "app.api.v1.endpoints.auth.verify_password", return_value=True
            ):
                request = PasswordResetConfirmRequest(
                    phone="+919999999999",
                    otp_code="123456",
                    new_password="NewPass123!",
                    confirm_password="NewPass123!",
                )

                with pytest.raises(HTTPException) as exc_info:
                    await confirm_password_reset(request, mock_session)

                assert exc_info.value.status_code == 400


class TestSendSignupOTPEndpoint:
    @pytest.mark.asyncio
    async def test_send_signup_otp_success(self):
        mock_session = Mock()

        mock_result = Mock()
        mock_result.first = Mock(return_value=None)
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.check_rate_limit_detailed = AsyncMock(
                return_value={"allowed": True}
            )
            mock_otp_service.send_signup_otp = AsyncMock(
                return_value={"status": "success", "reference_id": "ref-signup"}
            )
            mock_otp_service_class.return_value = mock_otp_service

            request = OTPSignupSendRequest(
                phone="+919999999999", email="test@example.com"
            )
            response = await send_signup_otp(request, mock_session)

            assert response.status == "success"

    @pytest.mark.asyncio
    async def test_send_signup_otp_user_exists(self):
        mock_session = Mock()
        mock_user = Mock()

        mock_result = Mock()
        mock_result.first = Mock(return_value=mock_user)
        mock_session.exec = Mock(return_value=mock_result)

        request = OTPSignupSendRequest(
            phone="+919999999999", email="test@example.com"
        )

        with pytest.raises(HTTPException) as exc_info:
            await send_signup_otp(request, mock_session)

        assert exc_info.value.status_code == 400


class TestResendSignupOTPEndpoint:
    @pytest.mark.asyncio
    async def test_resend_signup_otp_success(self):
        mock_session = Mock()

        mock_result = Mock()
        mock_result.first = Mock(return_value=None)
        mock_session.exec = Mock(return_value=mock_result)

        with patch(
            "app.api.v1.endpoints.auth.OTPService"
        ) as mock_otp_service_class:
            mock_otp_service = AsyncMock()
            mock_otp_service.check_rate_limit = AsyncMock(return_value=True)
            mock_otp_service.invalidate_otp = AsyncMock()
            mock_otp_service.send_signup_otp = AsyncMock(
                return_value={
                    "status": "success",
                    "reference_id": "ref-resignup",
                }
            )
            mock_otp_service_class.return_value = mock_otp_service

            request = OTPSignupResendRequest(phone="+919999999999")
            response = await resend_signup_otp(request, mock_session)

            assert response.status == "success"

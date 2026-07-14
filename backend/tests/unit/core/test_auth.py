"""Tests for app/core/auth.py authentication utilities."""

from datetime import timedelta
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.core.auth import (
    authenticate_user,
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestCreateAccessToken:
    """Test JWT token creation."""

    def test_create_token_with_default_expiry(self):
        """Test creating token with default expiry."""
        token = create_access_token("test_user")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_custom_expiry(self):
        """Test creating token with custom expiry."""
        token = create_access_token(
            "test_user", expires_delta=timedelta(hours=1)
        )
        assert token is not None
        assert isinstance(token, str)

    def test_create_token_with_uuid(self):
        """Test creating token with UUID subject."""
        user_id = uuid4()
        token = create_access_token(user_id)
        assert token is not None

        decoded = decode_token(token)
        assert decoded == str(user_id)

    def test_decode_created_token(self):
        """Test that created token can be decoded."""
        user_id = "test_user_123"
        token = create_access_token(user_id)
        decoded = decode_token(token)
        assert decoded == user_id


class TestVerifyPassword:
    """Test password verification."""

    def test_verifies_correct_password(self):
        """Test verifying correct password."""
        password = "test_password"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_rejects_wrong_password(self):
        """Test rejecting wrong password."""
        password = "test_password"
        hashed = get_password_hash(password)
        assert verify_password("wrong_password", hashed) is False

    def test_handles_empty_password(self):
        """Test handling empty password."""
        assert verify_password("", "some_hash") is False

    def test_handles_invalid_hash(self):
        """Test handling invalid hash format."""
        assert verify_password("test", "invalid_hash_format") is False

    def test_hash_contains_dollar_signs(self):
        """Bcrypt hashes contain multiple $ signs."""
        hashed = get_password_hash("test")
        assert "$" in hashed

    def test_short_password_works(self):
        """Test short password hashing works."""
        hashed = get_password_hash("a")
        assert verify_password("a", hashed) is True

    def test_verify_password_correct(self):
        """Test verifying correct password (alias test)."""
        password = "SecurePass123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "SecurePass123!"
        hashed = get_password_hash(password)
        assert verify_password("WrongPassword123!", hashed) is False

    def test_verify_password_empty_password(self):
        """Test verifying empty password."""
        hashed = get_password_hash("SomePassword123!")
        assert verify_password("", hashed) is False

    def test_verify_password_empty_hash(self):
        """Test verifying against empty hash."""
        assert verify_password("password", "") is False

    def test_verify_password_wrong_hash_format(self):
        """Test verifying against malformed hash."""
        assert verify_password("password", "not_a_valid_bcrypt_hash") is False


class TestGetPasswordHash:
    """Test password hashing."""

    def test_returns_hashed_password(self):
        """Test returning hashed password."""
        password = "test_password"
        hashed = get_password_hash(password)
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_different_hashes_for_same_password(self):
        """Test different hashes for same password."""
        password = "test_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2

    def test_hash_contains_dollar_sign(self):
        """Bcrypt hashes contain multiple $ signs."""
        hashed = get_password_hash("test")
        assert "$" in hashed

    def test_short_password_works(self):
        """Test short password works."""
        hashed = get_password_hash("a")
        assert verify_password("a", hashed) is True


class TestDecodeToken:
    """Test JWT token decoding."""

    def test_decode_valid_token(self):
        """Test decoding a valid token."""
        user_id = "test_user_123"
        token = create_access_token(user_id)
        decoded = decode_token(token)
        assert decoded == user_id

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        assert decode_token("invalid_token") is None

    def test_decode_malformed_token(self):
        """Test decoding malformed token returns None."""
        assert decode_token("not.a.jwt") is None

    def test_decode_token_without_sub(self):
        """Test decoding token without subject returns None."""
        with patch("app.core.auth.jwt.decode") as mock_decode:
            mock_decode.return_value = {}
            assert decode_token("some_token") is None

    def test_decode_expired_token(self):
        """Test decoding expired token returns None."""
        token = create_access_token(
            "test_user", expires_delta=timedelta(seconds=-1)
        )
        assert decode_token(token) is None


class TestAuthenticateUser:
    """Test user authentication."""

    def test_authenticate_valid_user(self):
        """Test authenticating valid user credentials."""
        password = "SecurePass123!"
        hashed = get_password_hash(password)

        mock_user = Mock()
        mock_user.phone = "9876543210"
        mock_user.hashed_password = hashed

        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = mock_user

        result = authenticate_user(mock_session, "9876543210", password)
        assert result == mock_user

    def test_authenticate_invalid_password(self):
        """Test authenticating with wrong password."""
        hashed = get_password_hash("CorrectPass123!")

        mock_user = Mock()
        mock_user.phone = "9876543210"
        mock_user.hashed_password = hashed

        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = mock_user

        result = authenticate_user(mock_session, "9876543210", "WrongPass123!")
        assert result is None

    def test_authenticate_nonexistent_user(self):
        """Test authenticating non-existent user."""
        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = None

        result = authenticate_user(mock_session, "9876543210", "password")
        assert result is None

    def test_authenticate_user_no_password(self):
        """Test authenticating user without password set."""
        mock_user = Mock()
        mock_user.phone = "9876543210"
        mock_user.hashed_password = None

        mock_session = Mock()
        mock_session.exec.return_value.first.return_value = mock_user

        result = authenticate_user(mock_session, "9876543210", "password")
        assert result is None


class TestPasswordHashEdgeCases:
    """Test edge cases in password hashing."""

    def test_hash_unicode_password(self):
        """Test hashing password with unicode characters."""
        password = "пароль密码🔒"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_hash_very_long_password(self):
        """Test hashing very long password truncates to 72 bytes."""
        password = "a" * 1000
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_hash_special_characters_password(self):
        """Test hashing password with special characters."""
        password = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestGetCurrentUser:
    """Test get_current_user function."""

    def test_get_current_user_invalid_token(self):
        """Test invalid token raises 401."""
        from fastapi import HTTPException

        from app.core.auth import get_current_user

        mock_credentials = Mock()
        mock_credentials.credentials = "invalid_token"

        with pytest.raises(HTTPException) as exc_info:
            import asyncio

            asyncio.run(get_current_user(Mock(), mock_credentials))
        assert exc_info.value.status_code == 401

    def test_get_current_user_expired_token(self):
        """Test expired token raises 401."""
        from fastapi import HTTPException

        from app.core.auth import get_current_user

        mock_credentials = Mock()
        mock_credentials.credentials = "expired_token"

        with patch("app.core.auth.decode_token", return_value=None):
            import asyncio

            try:
                asyncio.run(get_current_user(Mock(), mock_credentials))
                assert False, "Should have raised HTTPException"
            except HTTPException as exc:
                assert exc.status_code == 401

    def test_get_current_user_invalid_user_id_format(self):
        """Test invalid user ID format raises 401."""
        from fastapi import HTTPException

        from app.core.auth import get_current_user

        mock_credentials = Mock()
        mock_credentials.credentials = "valid_token"

        with patch("app.core.auth.decode_token", return_value="not-a-uuid"):
            import asyncio

            try:
                asyncio.run(get_current_user(Mock(), mock_credentials))
                assert False, "Should have raised HTTPException"
            except HTTPException as exc:
                assert exc.status_code == 401
                assert "Invalid user ID format" in exc.detail

    def test_get_current_user_not_found(self):
        """Test user not found raises 401."""
        from uuid import uuid4

        from fastapi import HTTPException

        from app.core.auth import get_current_user

        mock_credentials = Mock()
        mock_credentials.credentials = "valid_token"
        mock_session = Mock()

        with patch("app.core.auth.decode_token", return_value=str(uuid4())):
            mock_session.get.return_value = None
            import asyncio

            try:
                asyncio.run(get_current_user(mock_session, mock_credentials))
                assert False, "Should have raised HTTPException"
            except HTTPException as exc:
                assert exc.status_code == 401
                assert "User not found" in exc.detail

    def test_get_current_user_inactive(self):
        """Test inactive user raises 401."""
        from uuid import uuid4

        from fastapi import HTTPException

        from app.core.auth import get_current_user

        mock_credentials = Mock()
        mock_credentials.credentials = "valid_token"
        mock_session = Mock()
        mock_user = Mock()
        mock_user.is_active = False

        with patch("app.core.auth.decode_token", return_value=str(uuid4())):
            mock_session.get.return_value = mock_user
            import asyncio

            try:
                asyncio.run(get_current_user(mock_session, mock_credentials))
                assert False, "Should have raised HTTPException"
            except HTTPException as exc:
                assert exc.status_code == 401
                assert "Inactive user" in exc.detail

    def test_get_current_user_success(self):
        """Test successful user retrieval."""
        from uuid import uuid4

        from app.core.auth import get_current_user

        mock_credentials = Mock()
        mock_credentials.credentials = "valid_token"
        mock_session = Mock()
        mock_user = Mock()
        mock_user.is_active = True
        user_id = uuid4()

        with patch("app.core.auth.decode_token", return_value=str(user_id)):
            mock_session.get.return_value = mock_user
            import asyncio

            result = asyncio.run(
                get_current_user(mock_session, mock_credentials)
            )
            assert result == mock_user


class TestGetCurrentActiveUser:
    """Test get_current_active_user function."""

    def test_inactive_user_raises_400(self):
        """Test inactive user raises 400."""
        from fastapi import HTTPException

        from app.core.auth import get_current_active_user

        mock_user = Mock()
        mock_user.is_active = False

        import asyncio

        try:
            asyncio.run(get_current_active_user(mock_user))
            assert False, "Should have raised HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 400
            assert "Inactive user" in exc.detail

    def test_active_user_returns(self):
        """Test active user is returned."""
        from app.core.auth import get_current_active_user

        mock_user = Mock()
        mock_user.is_active = True

        import asyncio

        result = asyncio.run(get_current_active_user(mock_user))
        assert result == mock_user


class TestRequireRoles:
    """Test require_roles function."""

    def test_returns_callable(self):
        """Test require_roles returns a callable."""
        from app.core.auth import require_roles
        from app.models.role import RoleEnum

        dependency = require_roles([RoleEnum.admin])
        assert callable(dependency)

    def test_with_single_role(self):
        """Test with single role parameter."""
        from app.core.auth import require_roles
        from app.models.role import RoleEnum

        dependency = require_roles([RoleEnum.admin])
        assert callable(dependency)

    def test_with_multiple_roles(self):
        """Test with multiple roles parameter."""
        from app.core.auth import require_roles
        from app.models.role import RoleEnum

        dependency = require_roles([RoleEnum.admin, RoleEnum.reviewer])
        assert callable(dependency)


class TestRoleDependencies:
    """Test role-specific dependencies."""

    def test_require_admin_dependency(self):
        """Test require_admin is a valid dependency."""
        from app.core.auth import require_admin

        assert require_admin is not None

    def test_require_admin_or_reviewer_dependency(self):
        """Test require_admin_or_reviewer is a valid dependency."""
        from app.core.auth import require_admin_or_reviewer

        assert require_admin_or_reviewer is not None

    def test_require_any_role_dependency(self):
        """Test require_any_role is a valid dependency."""
        from app.core.auth import require_any_role

        assert require_any_role is not None

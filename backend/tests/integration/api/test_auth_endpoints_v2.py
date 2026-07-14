"""Integration tests for authentication endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.core.auth import get_password_hash
from app.models.otp import OTP
from app.models.user import User


class TestLoginEndpoint:
    """Tests for login endpoint."""

    def test_login_success(self, client, db_session, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": test_user.phone, "password": "testpassword"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client, db_session, test_user):
        """Test login with invalid password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": test_user.phone, "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "Incorrect phone number or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client, db_session):
        """Test login with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "+919988877766", "password": "password123"},
        )

        assert response.status_code == 401

    def test_login_inactive_user(self, client, db_session):
        """Test login with inactive user."""
        # Create inactive user
        user = User(
            id=uuid4(),
            phone="+919988877766",
            name="Inactive User",
            username="inactiveuser",
            hashed_password=get_password_hash("password123"),
            is_active=False,
            has_given_consent=True,
        )
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"phone": "+919988877766", "password": "password123"},
        )

        assert response.status_code == 401
        assert "Inactive user" in response.json()["detail"]


class TestGetCurrentUser:
    """Tests for /me endpoint."""

    def test_get_current_user_success(
        self, client, db_session, test_user, auth_headers
    ):
        """Test getting current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == test_user.phone
        assert data["username"] == test_user.username

    def test_get_current_user_no_token(self, client, db_session, test_user):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 403

    def test_get_current_user_invalid_token(
        self, client, db_session, test_user
    ):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401


class TestChangePassword:
    """Tests for change password endpoint."""

    def test_change_password_success(
        self, client, db_session, test_user, auth_headers
    ):
        """Test successful password change."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword",
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!",
            },
        )

        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]

    def test_change_password_wrong_current(
        self, client, db_session, test_user, auth_headers
    ):
        """Test password change with wrong current password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "NewPass123!",
                "confirm_password": "NewPass123!",
            },
        )

        assert response.status_code == 400
        assert "Incorrect current password" in response.json()["detail"]


class TestOTPFlow:
    """Tests for OTP login flow."""

    @patch("app.services.otp_service.requests.post")
    def test_send_login_otp_success(
        self, mock_post, client, db_session, test_user
    ):
        """Test sending login OTP."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_post.return_value = mock_response

        response = client.post(
            "/api/v1/auth/login/send-otp", json={"phone": test_user.phone}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch("app.services.otp_service.requests.post")
    def test_send_login_otp_nonexistent_user(
        self, mock_post, client, db_session
    ):
        """Test sending OTP for non-existent user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_post.return_value = mock_response

        response = client.post(
            "/api/v1/auth/login/send-otp", json={"phone": "+919988877766"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "signup_required"

    def test_send_login_otp_invalid_phone(self, client, db_session):
        """Test sending OTP with invalid phone."""
        response = client.post(
            "/api/v1/auth/login/send-otp", json={"phone": "invalid"}
        )

        assert response.status_code == 422

    @patch("app.services.otp_service.requests.post")
    def test_verify_login_otp_success(
        self, mock_post, client, db_session, test_user
    ):
        """Test verifying login OTP."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_post.return_value = mock_response

        # Create OTP in database
        otp = OTP(
            phone=test_user.phone,
            otp_code="123456",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            is_verified=False,
            attempts=0,
        )
        db_session.add(otp)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login/verify-otp",
            json={"phone": test_user.phone, "otp_code": "123456"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestSignupFlow:
    """Tests for signup flow."""

    @patch("app.services.otp_service.requests.post")
    def test_send_signup_otp_success(self, mock_post, client, db_session):
        """Test sending signup OTP."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_post.return_value = mock_response

        response = client.post(
            "/api/v1/auth/signup/send-otp", json={"phone": "+919988877766"}
        )

        assert response.status_code == 200

    @patch("app.services.otp_service.requests.post")
    def test_send_signup_otp_existing_user(
        self, mock_post, client, db_session, test_user
    ):
        """Test sending OTP for existing user."""
        response = client.post(
            "/api/v1/auth/signup/send-otp", json={"phone": test_user.phone}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @patch("app.services.otp_service.requests.post")
    def test_verify_signup_otp_success(self, mock_post, client, db_session):
        """Test verifying signup OTP and creating user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_post.return_value = mock_response

        # Create OTP in database
        otp = OTP(
            phone="+919988877766",
            otp_code="123456",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            is_verified=False,
            attempts=0,
        )
        db_session.add(otp)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/signup/verify-otp",
            json={
                "phone": "+919988877766",
                "otp_code": "123456",
                "username": "newuser",
                "password": "TestPass123!",
                "confirm_password": "TestPass123!",
                "name": "New User",
                "gender": "male",
                "date_of_birth": "2000-01-01",
                "current_place": "Mumbai, India",
                "has_given_consent": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["username"] == "newuser"

    def test_verify_signup_no_consent(self, client, db_session):
        """Test signup without consent."""
        response = client.post(
            "/api/v1/auth/signup/verify-otp",
            json={
                "phone": "+919988877766",
                "otp_code": "123456",
                "username": "newuser",
                "password": "TestPass123!",
                "confirm_password": "TestPass123!",
                "name": "New User",
                "gender": "male",
                "date_of_birth": "2000-01-01",
                "current_place": "Mumbai, India",
                "has_given_consent": False,
            },
        )

        assert response.status_code == 400
        assert "consent" in response.json()["detail"]


class TestPasswordReset:
    """Tests for password reset flow."""

    @patch("app.services.otp_service.requests.post")
    def test_initiate_password_reset(
        self, mock_post, client, db_session, test_user
    ):
        """Test initiating password reset."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_post.return_value = mock_response

        response = client.post(
            "/api/v1/auth/forgot-password/init", json={"phone": test_user.phone}
        )

        # Returns success regardless of user existence (privacy)
        assert response.status_code == 200

    @patch("app.services.otp_service.requests.post")
    def test_confirm_password_reset_success(
        self, mock_post, client, db_session, test_user
    ):
        """Test confirming password reset."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "success"
        mock_post.return_value = mock_response

        # Create OTP in database
        otp = OTP(
            phone=test_user.phone,
            otp_code="123456",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            is_verified=False,
            attempts=0,
        )
        db_session.add(otp)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/forgot-password/confirm",
            json={
                "phone": test_user.phone,
                "otp_code": "123456",
                "new_password": "ResetPass123!",
            },
        )

        assert response.status_code == 200

    def test_confirm_password_reset_same_password(
        self, client, db_session, test_user
    ):
        """Test confirming password reset with same as current."""
        # Set password to known value
        test_user.hashed_password = get_password_hash("TestPass123!")
        db_session.add(test_user)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/forgot-password/confirm",
            json={
                "phone": test_user.phone,
                "otp_code": "123456",
                "new_password": "TestPass123!",
            },
        )

        assert response.status_code == 400
        assert "same as current password" in response.json()["detail"]

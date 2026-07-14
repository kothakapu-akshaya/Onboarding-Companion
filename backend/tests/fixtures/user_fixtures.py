"""User-related fixtures for testing.

Provides standardized user objects and mock data.
"""

import uuid
from datetime import date
from unittest.mock import Mock

import pytest

from app.models.user import User
from tests.data.test_data import TestData


@pytest.fixture
def mock_user():
    """Create a mock user for tests that don't need database."""
    user = Mock()
    user.id = uuid.uuid4()
    user.phone = "+919876543210"
    user.name = "Test User"
    user.email = "test@example.com"
    user.gender = "male"
    user.date_of_birth = date(1990, 1, 1)
    user.place = "Test City, India"
    user.has_given_consent = True
    user.is_active = True
    user.hashed_password = "hashed_password"
    return user


@pytest.fixture
def test_user(db_session):
    """Create a test user in the database."""
    user_data = TestData.mock_user_data()
    user = User(
        id=user_data["id"],
        phone=user_data["phone"],
        name=user_data["name"],
        email=user_data["email"],
        gender=user_data["gender"],
        date_of_birth=user_data["date_of_birth"],
        place=user_data["place"],
        has_given_consent=user_data["has_given_consent"],
        is_active=user_data["is_active"],
        hashed_password=user_data["hashed_password"],
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def multiple_test_users(db_session):
    """Create multiple test users for complex testing scenarios."""
    users = []
    for i in range(3):
        user_data = TestData.mock_user_data(
            phone=f"+9187654321{i}",
            email=f"test{i}@example.com",
            name=f"Test User {i}",
        )
        user = User(**user_data)
        db_session.add(user)
        users.append(user)

    db_session.commit()
    for user in users:
        db_session.refresh(user)

    yield users

    for user in users:
        db_session.delete(user)
    db_session.commit()


@pytest.fixture
def user_registration_data():
    """Provide standard user registration data."""
    return TestData.user_registration_data()


@pytest.fixture
def user_login_data():
    """Provide standard user login data."""
    return TestData.user_login_data()


@pytest.fixture
def invalid_user_data():
    """Provide invalid user data for error testing."""
    return TestData.user_registration_data(
        phone="5876543210",  # Invalid starting digit
        name="J",  # Too short
        password="weak",  # Too weak
        confirm_password="different",  # Doesn't match
        has_given_consent=False,  # Must be True
    )

"""Pytest configuration and fixtures for the corpus server tests."""

import os
import sys
from pathlib import Path

# Ensure the project root is importable even when pytest is invoked via the
# console script (where sys.path[0] is typically the venv's bin directory).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

pytest_plugins = [
    "tests.fixtures.api_fixtures",
]

import uuid  # noqa: E402
from datetime import date  # noqa: E402
from unittest.mock import Mock  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, create_engine  # noqa: E402

from app.core.auth import get_password_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from tests.data.test_data import TestData  # noqa: E402


@pytest.fixture
def user_registration_data():
    return TestData.user_registration_data()


@pytest.fixture
def user_login_data():
    return TestData.user_login_data()


@pytest.fixture
def otp_data():
    return TestData.otp_data()


@pytest.fixture
def invalid_user_data():
    return TestData.user_registration_data(email="invalid-email")


@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine."""
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

    if not database_url or "postgres" not in database_url.lower():
        # Skip tests that require database if not available locally
        pytest.skip("Database not available for testing")

    try:
        engine = create_engine(database_url)
        with engine.connect():
            pass
        return engine
    except Exception:
        pytest.skip("Database not available for testing")


@pytest.fixture
def session(db_engine):
    """Create a database session for tests."""
    with Session(db_engine) as session:
        yield session
        session.rollback()  # Clean up after each test


@pytest.fixture
def db_session(session):
    """Alias for session fixture for backward compatibility."""
    return session


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock user for tests that don't need database."""
    user = Mock()
    user.id = 1
    user.phone = "+919999999999"
    user.name = "Test User"
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def test_user(session):
    """Create a test user in the database."""
    user = User(
        id=uuid.uuid4(),
        phone="+919999999999",
        name="Test User",
        email=f"test-{uuid.uuid4()}@example.com",
        hashed_password=get_password_hash("testpassword"),
        gender="male",
        date_of_birth=date(1990, 1, 1),
        place="Test City, India",
        has_given_consent=True,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    yield user
    session.delete(user)
    session.commit()


@pytest.fixture
def auth_headers(test_user):
    """Create authorization headers for a regular user."""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
def admin_headers(test_admin):
    """Create authorization headers for an admin user."""
    return {"Authorization": "Bearer admin_token"}


@pytest.fixture
def test_admin(session):
    """Create an admin test user in the database."""
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        phone="+919999999998",
        name="Admin User",
        email=f"admin-{uuid.uuid4()}@example.com",
        hashed_password=get_password_hash("testpassword"),
        gender="male",
        date_of_birth=date(1990, 1, 1),
        place="Admin City, India",
        has_given_consent=True,
        is_active=True,
        is_admin=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    yield user
    session.delete(user)
    session.commit()


# Skip database tests when database is not available
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "database: mark test as requiring database connection"
    )


def pytest_runtest_setup(item):
    """Auto-skip database tests when database is not available."""
    database_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

    # Skip tests that use database fixtures when database is not available
    if not database_url or "postgres" not in database_url.lower():
        db_fixtures = ["session", "db_session", "test_user"]
        if any(fixture in item.fixturenames for fixture in db_fixtures):
            pytest.skip("Database not available for testing")

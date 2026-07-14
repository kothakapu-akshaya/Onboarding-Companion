"""API-related fixtures for testing.

Provides centralized client and database session fixtures.
"""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session
from app.main import app


@pytest.fixture(scope="function")
def app_client(db_session):
    """Create a single test client for all tests."""
    # FastAPI dependency overrides are keyed by the dependency callable, not the
    # Annotated type alias (SessionDep). Override get_session
    # to inject db_session.
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(app_client, test_user):
    """Create an authenticated client with a test user."""
    # Log in the test user to get a valid JWT token
    login_data = {
        "phone": test_user.phone,
        "password": "testpassword",  # Assuming a default password for test_user
    }
    response = app_client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Configure the client to use this token for subsequent requests
    app_client.headers["Authorization"] = f"Bearer {token}"
    return app_client


@pytest.fixture
def mock_session():
    """Create a mock database session for unit tests."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.rollback = Mock()
    session.delete = Mock()
    return session

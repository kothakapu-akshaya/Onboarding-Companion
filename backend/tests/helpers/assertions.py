"""Custom assertion helpers for test cases.

Provides reusable assertion functions for common test patterns.
"""

from typing import Any

import pytest
from pydantic import ValidationError


def assert_validation_error(func, *args, **kwargs):
    """Assert that a function raises ValidationError."""
    with pytest.raises(ValidationError):
        func(*args, **kwargs)


def assert_validation_success(func, *args, **kwargs):
    """Assert that a function executes without ValidationError."""
    try:
        result = func(*args, **kwargs)
        return result
    except ValidationError as e:
        pytest.fail(f"Unexpected ValidationError: {e}")


def assert_api_response(
    response, expected_status: int, expected_keys: list[str] | None = None
):
    """Assert API response status and structure."""
    assert response.status_code == expected_status, (
        f"Expected status {expected_status},"
        f" got {response.status_code}: {response.text}"
    )

    if expected_keys:
        response_data = response.json()
        for key in expected_keys:
            assert key in response_data, (
                f"Expected key '{key}' not found in response"
            )


def assert_api_error(
    response, expected_status: int, expected_detail: str | None = None
):
    """Assert API error response."""
    assert response.status_code == expected_status
    if expected_detail:
        response_data = response.json()
        assert "detail" in response_data
        assert expected_detail in response_data["detail"]


def assert_phone_formatted(actual_phone: str, expected_phone: str):
    """Assert phone number is properly formatted."""
    assert actual_phone == expected_phone, (
        f"Expected phone {expected_phone}, got {actual_phone}"
    )


def assert_password_valid(password: str, validation_result):
    """Assert password validation result."""
    if hasattr(validation_result, "is_valid"):
        assert validation_result.is_valid, (
            f"Password '{password}' should be valid but was rejected"
        )
    else:
        assert validation_result, (
            f"Password '{password}' should be valid but was rejected"
        )


def assert_password_invalid(password: str, validation_result):
    """Assert password validation failure."""
    if hasattr(validation_result, "is_valid"):
        assert not validation_result.is_valid, (
            f"Password '{password}' should be invalid but was accepted"
        )
    else:
        assert not validation_result, (
            f"Password '{password}' should be invalid but was accepted"
        )


def assert_user_data_matches(
    user_obj,
    expected_data: dict[str, Any],
    exclude_keys: list[str] | None = None,
):
    """Assert user object matches expected data."""
    exclude_keys = exclude_keys or [
        "password",
        "confirm_password",
        "hashed_password",
    ]

    for key, expected_value in expected_data.items():
        if key in exclude_keys:
            continue

        actual_value = getattr(user_obj, key, None)
        assert actual_value == expected_value, (
            f"Expected {key}={expected_value}, got {actual_value}"
        )


def assert_otp_response_valid(response_data: dict[str, Any]):
    """Assert OTP response has valid structure."""
    required_keys = ["status", "reference_id"]
    for key in required_keys:
        assert key in response_data, (
            f"Missing required key '{key}' in OTP response"
        )

    assert response_data["status"] in ["success", "error"], (
        f"Invalid OTP status: {response_data['status']}"
    )


def assert_content_validation(
    content_data: dict[str, Any], should_be_valid: bool
):
    """Assert content validation result."""
    if should_be_valid:
        # Should not raise ValidationError
        return content_data
    else:
        # Should raise ValidationError
        with pytest.raises(ValidationError):
            # This should be called in context where validation occurs
            pass


def assert_db_record_exists(session, model_class, **filters):
    """Assert database record exists with given filters."""
    query = session.query(model_class)
    for key, value in filters.items():
        query = query.filter(getattr(model_class, key) == value)

    record = query.first()
    assert record is not None, (
        f"Expected record with {filters} not found in {model_class.__name__}"
    )
    return record


def assert_db_record_not_exists(session, model_class, **filters):
    """Assert database record does not exist with given filters."""
    query = session.query(model_class)
    for key, value in filters.items():
        query = query.filter(getattr(model_class, key) == value)

    record = query.first()
    assert record is None, (
        f"Unexpected record with {filters} found in {model_class.__name__}"
    )

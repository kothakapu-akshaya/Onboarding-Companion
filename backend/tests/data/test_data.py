"""Centralized test data for all test suites.

Provides standardized test data and builder patterns.
"""

import uuid
from datetime import date
from typing import Any

from app.schemas.upload_validation import MediaType, ReleaseRights


class TestData:
    """Centralized test data constants and builders."""

    # Password test cases
    VALID_PASSWORDS = [
        "SecurePass123!",
        "MyStr0ng#Password",
        "Complex@Pass1",
        "Test#Password123",
    ]

    INVALID_PASSWORDS = [
        "weak",
        "12345678",
        "password",
        "PASSWORD",
        "Pass123",  # Missing special char
        "Pass@word",  # Missing number
    ]

    # Phone number test cases
    VALID_PHONES = [
        "9876543210",
        "8123456789",
        "7987654321",
        "+919876543210",
        "91 9876543210",
        "919876543210",
    ]

    INVALID_PHONES = [
        "5876543210",  # Starts with 5
        "4123456789",  # Starts with 4
        "987654321",  # Too short
        "98765432100",  # Too long
        "abcd123456",  # Contains letters
        "123456789",  # Too short
    ]

    # Email test cases
    VALID_EMAILS = [
        "john@example.com",
        "test.user@domain.co.in",
        "user+tag@example.org",
        "test123@test-domain.com",
    ]

    INVALID_EMAILS = [
        "invalid.email",
        "@example.com",
        "user@",
        "user name@example.com",
        "user@domain",
    ]

    # Name test cases
    VALID_NAMES = [
        "John Doe",
        "José María",
        "李小明",  # Chinese characters
        "Anna Müller",  # Accented characters
        "Test User",
        "John Smith Jr.",
    ]

    INVALID_NAMES = [
        "J",  # Too short
        "A",  # Too short
        "X" * 101,  # Too long
        "John123",  # Contains numbers
        "User@Name",  # Contains special chars
    ]

    # Content validation test cases
    VALID_TITLES = [
        "Sample Audio Recording",
        "Test Content Title",
        "Valid Content Name",
    ]

    INVALID_TITLES = [
        "",  # Empty
        "A",  # Too short
        "X" * 201,  # Too long
    ]

    VALID_DESCRIPTIONS = [
        (
            "This is a valid description for test content"
            " that meets the minimum word requirement."
        ),
        (
            "Sample description with proper length and content"
            " that provides sufficient detail for testing."
        ),
        (
            "Valid test description for audio content with"
            " enough words to pass the validation threshold."
        ),
    ]

    INVALID_DESCRIPTIONS = [
        "",  # Empty
        "Short",  # Too short
        "X" * 1001,  # Too long
    ]

    @staticmethod
    def user_registration_data(**overrides) -> dict[str, Any]:
        """Build user registration data with optional overrides."""
        default = {
            "username": "johndoe",
            "phone": "9876543210",
            "name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "gender": "male",
            "date_of_birth": "1990-01-01",
            "current_place": "Hyderabad, India",
            "has_given_consent": True,
        }
        return {**default, **overrides}

    @staticmethod
    def user_login_data(**overrides) -> dict[str, Any]:
        """Build user login data with optional overrides."""
        default = {
            "phone": "9876543210",
            "password": "SecurePass123!",
        }
        return {**default, **overrides}

    @staticmethod
    def otp_data(**overrides) -> dict[str, Any]:
        """Build OTP data with optional overrides."""
        default = {
            "phone": "9876543210",
            "otp_code": "123456",
            "reference_id": "test_ref_id",
        }
        return {**default, **overrides}

    @staticmethod
    def content_data(**overrides) -> dict[str, Any]:
        """Build content data with optional overrides."""
        default = {
            "title": "Sample Audio Recording",
            "description": (
                "This is a valid description for test content that "
                "meets the minimum word requirement."
            ),
            "language": "hindi",
            "release_rights": ReleaseRights.creator,
            "media_type": MediaType.audio,
            "location": {"latitude": 12.9716, "longitude": 77.5946},
            "audio_file": {
                "file_name": "test.wav",
                "file_type": "audio/wav",
                "file_size_bytes": 1024 * 1024,
            },
        }
        if overrides.get("media_type") == MediaType.text:
            default["text_content"] = (
                "This is a sample text content with more than"
                " fifty characters to satisfy the validation"
                " rules and make the test pass. This should be"
                " long enough."
            )
            default.pop("audio_file", None)
        return {**default, **overrides}

    @staticmethod
    def mock_user_data(**overrides) -> dict[str, Any]:
        """Build mock user data for unit tests."""
        default = {
            "id": uuid.uuid4(),
            "phone": "+919876543210",
            "name": "Test User",
            "email": "test@example.com",
            "gender": "male",
            "date_of_birth": date(1990, 1, 1),
            "place": "Test City, India",
            "has_given_consent": True,
            "is_active": True,
            "hashed_password": "hashed_password",
        }
        return {**default, **overrides}

    @staticmethod
    def api_response_data(
        status_code: int = 200, **overrides
    ) -> dict[str, Any]:
        """Build API response data for testing."""
        default = {
            "status_code": status_code,
            "detail": "Success" if status_code == 200 else "Error",
        }
        return {**default, **overrides}


# Parameterized test data sets
PASSWORD_VALIDATION_CASES = [
    (password, True) for password in TestData.VALID_PASSWORDS
] + [(password, False) for password in TestData.INVALID_PASSWORDS]

PHONE_VALIDATION_CASES = [(phone, True) for phone in TestData.VALID_PHONES] + [
    (phone, False) for phone in TestData.INVALID_PHONES
]

EMAIL_VALIDATION_CASES = [(email, True) for email in TestData.VALID_EMAILS] + [
    (email, False) for email in TestData.INVALID_EMAILS
]

NAME_VALIDATION_CASES = [(name, True) for name in TestData.VALID_NAMES] + [
    (name, False) for name in TestData.INVALID_NAMES
]

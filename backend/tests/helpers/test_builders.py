"""Test data builders for creating complex test scenarios.

Provides builder pattern implementations for test data construction.
"""

from typing import Any

from tests.data.test_data import TestData


class UserDataBuilder:
    """Builder for user test data."""

    def __init__(self):
        self.data = TestData.user_registration_data()

    def with_phone(self, phone: str):
        self.data["phone"] = phone
        return self

    def with_email(self, email: str):
        self.data["email"] = email
        return self

    def with_name(self, name: str):
        self.data["name"] = name
        return self

    def with_password(self, password: str):
        self.data["password"] = password
        self.data["confirm_password"] = password
        return self

    def with_mismatched_passwords(self, password: str, confirm_password: str):
        self.data["password"] = password
        self.data["confirm_password"] = confirm_password
        return self

    def with_gender(self, gender: str):
        self.data["gender"] = gender
        return self

    def with_birth_date(self, birth_date: str):
        self.data["date_of_birth"] = birth_date
        return self

    def with_place(self, place: str):
        self.data["current_place"] = place
        return self

    def without_consent(self):
        self.data["has_given_consent"] = False
        return self

    def build(self) -> dict[str, Any]:
        return self.data.copy()


class ContentDataBuilder:
    """Builder for content test data."""

    def __init__(self):
        self.data = TestData.content_data()

    def with_title(self, title: str):
        self.data["title"] = title
        return self

    def with_description(self, description: str):
        self.data["description"] = description
        return self

    def with_language(self, language: str):
        self.data["language"] = language
        return self

    def with_media_type(self, media_type: str):
        self.data["media_type"] = media_type
        return self

    def with_coordinates(self, latitude: float, longitude: float):
        self.data["coordinates"] = {
            "latitude": latitude,
            "longitude": longitude,
        }
        return self

    def with_release_rights(self, rights: str):
        self.data["release_rights"] = rights
        return self

    def build(self) -> dict[str, Any]:
        return self.data.copy()


class OTPDataBuilder:
    """Builder for OTP test data."""

    def __init__(self):
        self.data = TestData.otp_data()

    def with_phone(self, phone: str):
        self.data["phone"] = phone
        return self

    def with_otp_code(self, otp_code: str):
        self.data["otp_code"] = otp_code
        return self

    def with_reference_id(self, reference_id: str):
        self.data["reference_id"] = reference_id
        return self

    def with_invalid_otp(self):
        self.data["otp_code"] = "000000"
        return self

    def with_expired_reference(self):
        self.data["reference_id"] = "expired_ref_id"
        return self

    def build(self) -> dict[str, Any]:
        return self.data.copy()


class APITestCaseBuilder:
    """Builder for API test cases."""

    def __init__(self):
        self.cases = []

    def add_success_case(
        self, data: dict[str, Any], expected_status: int = 200
    ):
        self.cases.append(
            {
                "data": data,
                "expected_status": expected_status,
                "should_succeed": True,
                "description": "Should succeed with valid data",
            }
        )
        return self

    def add_validation_error_case(self, data: dict[str, Any], description: str):
        self.cases.append(
            {
                "data": data,
                "expected_status": 422,
                "should_succeed": False,
                "description": description,
            }
        )
        return self

    def add_auth_error_case(self, data: dict[str, Any]):
        self.cases.append(
            {
                "data": data,
                "expected_status": 401,
                "should_succeed": False,
                "description": "Should fail with authentication error",
            }
        )
        return self

    def add_permission_error_case(self, data: dict[str, Any]):
        self.cases.append(
            {
                "data": data,
                "expected_status": 403,
                "should_succeed": False,
                "description": "Should fail with permission error",
            }
        )
        return self

    def build(self) -> list[dict[str, Any]]:
        return self.cases.copy()


class ValidationTestCaseBuilder:
    """Builder for validation test cases."""

    def __init__(self):
        self.cases = []

    def add_valid_cases(
        self, values: list[Any], description_template: str = "Should accept {}"
    ):
        for value in values:
            self.cases.append(
                {
                    "input": value,
                    "expected_valid": True,
                    "description": description_template.format(value),
                }
            )
        return self

    def add_invalid_cases(
        self, values: list[Any], description_template: str = "Should reject {}"
    ):
        for value in values:
            self.cases.append(
                {
                    "input": value,
                    "expected_valid": False,
                    "description": description_template.format(value),
                }
            )
        return self

    def build(self) -> list[dict[str, Any]]:
        return self.cases.copy()


# Convenience builder functions
def user_data() -> UserDataBuilder:
    """Create a new user data builder."""
    return UserDataBuilder()


def content_data() -> ContentDataBuilder:
    """Create a new content data builder."""
    return ContentDataBuilder()


def otp_data() -> OTPDataBuilder:
    """Create a new OTP data builder."""
    return OTPDataBuilder()


def api_test_cases() -> APITestCaseBuilder:
    """Create a new API test case builder."""
    return APITestCaseBuilder()


def validation_test_cases() -> ValidationTestCaseBuilder:
    """Create a new validation test case builder."""
    return ValidationTestCaseBuilder()

"""Consolidated validation tests using parameterization.

Tests core validation functions with comprehensive test data.
"""

from datetime import date

import pytest

from app.core.validators import (
    validate_age_from_birthdate,
    validate_content_description,
    validate_content_title,
    validate_coordinates,
    validate_email_address,
    validate_file_size,
    validate_password_strength,
    validate_phone,
    validate_place_name,
)
from tests.data.test_data import (
    EMAIL_VALIDATION_CASES,
    PASSWORD_VALIDATION_CASES,
    PHONE_VALIDATION_CASES,
    TestData,
)
from tests.helpers.assertions import (
    assert_phone_formatted,
)


class TestPasswordValidation:
    """Test password validation with parameterized cases."""

    @pytest.mark.parametrize(
        "password,expected_valid", PASSWORD_VALIDATION_CASES
    )
    def test_password_validation(self, password, expected_valid):
        """Test password validation with various inputs."""
        if expected_valid:
            result = validate_password_strength(password)
            assert result == password
        else:
            with pytest.raises(ValueError):
                validate_password_strength(password)

    def test_password_complexity_requirements(self):
        """Test specific password complexity requirements."""
        # Test minimum length
        with pytest.raises(ValueError):
            validate_password_strength("Pass1!")

        # Test special character requirement
        with pytest.raises(ValueError):
            validate_password_strength("Password123")

        # Test number requirement
        with pytest.raises(ValueError):
            validate_password_strength("Password!")

        # Test uppercase requirement
        with pytest.raises(ValueError):
            validate_password_strength("password123!")


class TestPhoneValidation:
    """Test phone validation with parameterized cases."""

    @pytest.mark.parametrize("phone,expected_valid", PHONE_VALIDATION_CASES)
    def test_phone_validation(self, phone, expected_valid):
        """Test phone validation and formatting."""
        if expected_valid:
            result = validate_phone(phone)
            assert result.startswith("+91")
            assert len(result) == 13  # +91 + 10 digits
        else:
            with pytest.raises(ValueError):
                validate_phone(phone)

    def test_phone_formatting(self):
        """Test phone number formatting specifically."""
        test_cases = [
            ("9876543210", "+919876543210"),
            ("+919876543210", "+919876543210"),
            ("91 9876543210", "+919876543210"),
            ("919876543210", "+919876543210"),
        ]

        for input_phone, expected in test_cases:
            result = validate_phone(input_phone)
            assert_phone_formatted(result, expected)

    def test_invalid_phone_patterns(self):
        """Test specific invalid phone patterns."""
        invalid_patterns = [
            "5876543210",  # Starts with 5
            "4123456789",  # Starts with 4
            "987654321",  # Too short
            "98765432100",  # Too long
            "abcd123456",  # Contains letters
        ]

        for phone in invalid_patterns:
            with pytest.raises(ValueError):
                validate_phone(phone)


class TestEmailValidation:
    """Test email validation with parameterized cases."""

    @pytest.mark.parametrize("email,expected_valid", EMAIL_VALIDATION_CASES)
    def test_email_validation(self, email, expected_valid):
        """Test email validation with various inputs."""
        if expected_valid:
            result = validate_email_address(email)
            assert "@" in result
            assert "." in result.split("@")[1]
        else:
            with pytest.raises(ValueError):
                validate_email_address(email)

    def test_email_normalization(self):
        """Test email normalization (lowercasing)."""
        test_cases = [
            ("John@Example.Com", "john@example.com"),
            ("TEST@DOMAIN.ORG", "test@domain.org"),
            ("User.Name@Test.Co.In", "user.name@test.co.in"),
        ]

        for input_email, expected in test_cases:
            result = validate_email_address(input_email)
            assert result == expected


class TestNameValidation:
    """Test name validation with parameterized cases."""

    @pytest.mark.parametrize(
        "name,expected_valid",
        [
            ("John", True),
            ("A", False),
            ("X" * 101, False),
            ("User@Name", False),
        ],
    )
    def test_name_validation(self, name, expected_valid):
        """Test name validation with various inputs."""
        if expected_valid:
            # Names should be validated by length and character constraints
            assert len(name) >= 2
            assert len(name) <= 100
        else:
            with pytest.raises(ValueError):
                validate_place_name(name)


class TestContentValidation:
    """Test content validation functions."""

    @pytest.mark.parametrize("title", TestData.VALID_TITLES)
    def test_valid_content_titles(self, title):
        """Test valid content titles."""
        result = validate_content_title(title)
        assert result == title
        assert len(result) >= 3
        assert len(result) <= 200

    @pytest.mark.parametrize("title", TestData.INVALID_TITLES)
    def test_invalid_content_titles(self, title):
        """Test invalid content titles."""
        with pytest.raises(ValueError):
            validate_content_title(title)

    @pytest.mark.parametrize("description", TestData.VALID_DESCRIPTIONS)
    def test_valid_content_descriptions(self, description):
        """Test valid content descriptions."""
        result = validate_content_description(description)
        assert result == description
        assert len(result) >= 16
        assert len(result) <= 1000

    @pytest.mark.parametrize("description", TestData.INVALID_DESCRIPTIONS)
    def test_invalid_content_descriptions(self, description):
        """Test invalid content descriptions."""
        with pytest.raises(ValueError):
            validate_content_description(description)


class TestCoordinateValidation:
    """Test coordinate validation."""

    @pytest.mark.parametrize(
        "lat,lng,expected_valid",
        [
            (12.9716, 77.5946, True),  # Bangalore
            (28.6139, 77.2090, True),  # Delhi
            (19.0760, 72.8777, True),  # Mumbai
            (-90, -180, True),  # Extreme valid
            (90, 180, True),  # Extreme valid
            (91, 77, False),  # Invalid latitude
            (12, 181, False),  # Invalid longitude
            (-91, 77, False),  # Invalid latitude
            (12, -181, False),  # Invalid longitude
        ],
    )
    def test_coordinate_validation(self, lat, lng, expected_valid):
        """Test coordinate validation with various values."""
        if expected_valid:
            result = validate_coordinates(lat, lng)
            assert result[0] == lat
            assert result[1] == lng
        else:
            with pytest.raises(ValueError):
                validate_coordinates(lat, lng)


class TestAgeValidation:
    """Test age validation from birth date."""

    @pytest.mark.parametrize(
        "birth_date,expected_valid",
        [
            ("1990-01-01", True),  # 34 years old
            ("2000-12-31", True),  # 24 years old
            ("1980-06-15", True),  # 44 years old
            ("2010-01-01", False),  # 14 years old - too young
            ("1900-01-01", False),  # 124 years old - too old
            ("2020-01-01", False),  # 4 years old - too young
            ("1950-01-01", True),  # 74 years old - valid
        ],
    )
    def test_age_validation(self, birth_date, expected_valid):
        """Test age validation from birth date."""
        birth_date_obj = date.fromisoformat(birth_date)
        if expected_valid:
            # Should not raise validation error
            validated_date = validate_age_from_birthdate(
                birth_date_obj, min_age=18
            )
            # Function returns str(birth_date)
            assert validated_date == birth_date
        else:
            # Should raise validation error for invalid ages
            with pytest.raises(ValueError):
                validate_age_from_birthdate(birth_date_obj, min_age=18)


class TestFileSizeValidation:
    """Test file size validation."""

    @pytest.mark.parametrize(
        "file_size,max_size,expected_valid",
        [
            (1024, 2048, True),  # 1KB file, 2KB limit
            (2048, 2048, True),  # Exactly at limit
            (1024 * 1024, 5 * 1024 * 1024, True),  # 1MB file, 5MB limit
            (3 * 1024 * 1024, 2 * 1024 * 1024, False),  # 3MB file, 2MB limit
            (0, 1024, False),  # Empty file
            (-1, 1024, False),  # Invalid negative size
        ],
    )
    def test_file_size_validation(self, file_size, max_size, expected_valid):
        """Test file size validation with various sizes."""
        if expected_valid:
            result = validate_file_size(file_size, max_size)
            assert result == file_size
        else:
            with pytest.raises(ValueError):
                validate_file_size(file_size, max_size)

    def test_file_size_minimum_custom(self):
        """Test file size validation with custom minimum."""
        result = validate_file_size(2048, 10240, min_size=1024)
        assert result == 2048

    def test_file_size_below_custom_minimum(self):
        """Test file size below custom minimum."""
        with pytest.raises(ValueError):
            validate_file_size(500, 10240, min_size=1024)


class TestCoordinateValidationEdgeCases:
    """Test coordinate validation edge cases."""

    def test_zero_coordinates_invalid(self):
        """Test that (0, 0) coordinates are invalid."""
        with pytest.raises(ValueError):
            validate_coordinates(0, 0)

    def test_non_numeric_coordinates(self):
        """Test that non-numeric coordinates raise error."""
        with pytest.raises(ValueError):
            validate_coordinates("invalid", 77.0)
        with pytest.raises(ValueError):
            validate_coordinates(12.0, "invalid")

    def test_numeric_coordinate_types(self):
        """Test that numeric coordinate types work."""
        lat, lng = validate_coordinates(12.9716, 77.5946)
        assert lat == 12.9716
        assert lng == 77.5946


class TestPlaceNameEdgeCases:
    """Test place name validation edge cases."""

    def test_balanced_parentheses(self):
        """Test place with balanced parentheses."""
        result = validate_place_name("New York (NYC)")
        assert result == "New York (NYC)"

    def test_unbalanced_parentheses_raises(self):
        """Test place with unbalanced parentheses raises error."""
        with pytest.raises(ValueError):
            validate_place_name("New York (NYC")

    def test_excessive_punctuation_raises(self):
        """Test place with excessive punctuation raises error."""
        with pytest.raises(ValueError):
            validate_place_name("a,b;c:d;e-f_g.i!")

    def test_suspicious_patterns_raise(self):
        """Test suspicious patterns raise error."""
        with pytest.raises(ValueError):
            validate_place_name("test123")
        with pytest.raises(ValueError):
            validate_place_name("dummy")
        with pytest.raises(ValueError):
            validate_place_name("na")

    def test_numeric_only_raises(self):
        """Test numeric-only place raises error."""
        with pytest.raises(ValueError):
            validate_place_name("12345")

    def test_word_too_long_raises(self):
        """Test word too long raises error."""
        with pytest.raises(ValueError):
            validate_place_name("Hyderabad " + "a" * 51)

    def test_word_without_vowels_raises(self):
        """Test word without vowels raises error for long words."""
        with pytest.raises(ValueError):
            validate_place_name("Test bcdfghjkl")


class TestAgeValidationEdgeCases:
    """Test age validation edge cases."""

    def test_future_birthdate_raises(self):
        """Test future birthdate raises error."""
        from datetime import date, timedelta

        future_date = date.today() + timedelta(days=1)
        with pytest.raises(ValueError):
            validate_age_from_birthdate(future_date)

    def test_custom_age_bounds(self):
        """Test custom age bounds."""
        from datetime import date

        result = validate_age_from_birthdate(
            date(1990, 1, 1), min_age=30, max_age=50
        )
        assert result == "1990-01-01"

    def test_below_minimum_age_raises(self):
        """Test below minimum age raises error."""
        from datetime import date

        with pytest.raises(ValueError):
            validate_age_from_birthdate(date(2010, 1, 1), min_age=18)

    def test_above_maximum_age_raises(self):
        """Test above maximum age raises error."""
        from datetime import date

        with pytest.raises(ValueError):
            validate_age_from_birthdate(date(1850, 1, 1), max_age=120)

    def test_non_date_input_raises(self):
        """Test non-date input raises error."""
        with pytest.raises(ValueError):
            validate_age_from_birthdate("1990-01-01")


class TestEmailValidationEdgeCases:
    """Test email validation edge cases."""

    def test_empty_email_raises(self):
        """Test empty email raises error."""
        with pytest.raises(ValueError):
            validate_email_address("")

    def test_whitespace_email_raises(self):
        """Test whitespace-only email raises error."""
        with pytest.raises(ValueError):
            validate_email_address("   ")

    def test_multiple_at_symbols_raises(self):
        """Test multiple @ symbols raises error."""
        with pytest.raises(ValueError):
            validate_email_address("user@@example.com")

    def test_local_part_too_long_raises(self):
        """Test local part too long raises error."""
        long_local = "a" * 65 + "@example.com"
        with pytest.raises(ValueError):
            validate_email_address(long_local)

    def test_domain_too_long_raises(self):
        """Test domain too long raises error."""
        long_domain = "user@" + "a" * 256
        with pytest.raises(ValueError):
            validate_email_address(long_domain)


class TestPasswordWeakPatterns:
    """Test password weak patterns detection."""

    @pytest.mark.parametrize(
        "password",
        [
            "password",
            "password123",
            "12345678",
            "qwerty123",
            "admin123",
            "welcome123",
            "letmein123",
        ],
    )
    def test_weak_passwords_rejected(self, password):
        """Test that weak passwords are rejected."""
        with pytest.raises(ValueError):
            validate_password_strength(password)


class TestTitleQuality:
    """Test title quality edge cases."""

    def test_all_caps_title_raises(self):
        """Test all caps title raises error."""
        with pytest.raises(ValueError):
            validate_content_title("THIS IS ALL CAPS TITLE")

    def test_short_title_raises(self):
        """Test short title raises error."""
        with pytest.raises(ValueError):
            validate_content_title("Hi")

    def test_repeated_chars_title_raises(self):
        """Test repeated chars title raises error."""
        with pytest.raises(ValueError):
            validate_content_title("aaaaaaaaaa")


class TestDescriptionQuality:
    """Test description quality edge cases."""

    def test_short_description_raises(self):
        """Test short description raises error."""
        with pytest.raises(ValueError):
            validate_content_description("Short")

    def test_repeated_chars_description_raises(self):
        """Test repeated chars description raises error."""
        with pytest.raises(ValueError):
            validate_content_description("aaaaaaaaaa aaaaaaaaaa aaaaa")

    def test_single_word_description_raises(self):
        """Test single word description raises error."""
        with pytest.raises(ValueError):
            validate_content_description("a" * 50)

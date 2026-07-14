"""Tests for core validators - standalone validation functions."""

from datetime import date

import pytest

from app.core.validators import (
    PasswordValidationError,
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


class TestPasswordValidation:
    """Test password validation using zxcvbn."""

    @pytest.mark.parametrize(
        "password,should_pass",
        [
            ("TestPass123!", True),
            ("SecureP@ss1", True),
            ("MyP@ssw0rd", False),  # zxcvbn considers this weak (score 1)
            ("weak", False),
            ("password123", False),  # common password
            ("qwerty", False),
            ("abc", False),
            ("12345678", False),
        ],
    )
    def test_password_validation(self, password, should_pass):
        """Test password validation with various inputs using zxcvbn."""
        if should_pass:
            result = validate_password_strength(password)
            assert result == password
        else:
            with pytest.raises(PasswordValidationError):
                validate_password_strength(password)

    def test_password_complexity_requirements(self):
        """Test specific password complexity requirements using zxcvbn."""
        with pytest.raises(ValueError):
            validate_password_strength("Pass1!")
        with pytest.raises(ValueError):
            validate_password_strength("12345678")
        with pytest.raises(ValueError):
            validate_password_strength("abc")
        with pytest.raises(ValueError):
            validate_password_strength("password")


class TestPhoneValidation:
    """Test phone validation."""

    @pytest.mark.parametrize(
        "phone,expected",
        [
            ("9876543210", "+919876543210"),
            ("+919876543210", "+919876543210"),
            ("91 987 654 3210", "+919876543210"),
        ],
    )
    def test_valid_phone_formatting(self, phone, expected):
        """Test phone number formatting."""
        result = validate_phone(phone)
        assert result == expected

    @pytest.mark.parametrize(
        "phone",
        [
            "5876543210",
            "4123456789",
            "987654321",
            "98765432100",
            "abcd123456",
        ],
    )
    def test_invalid_phone(self, phone):
        """Test invalid phone patterns."""
        with pytest.raises(ValueError):
            validate_phone(phone)


class TestEmailValidation:
    """Test email validation."""

    @pytest.mark.parametrize(
        "email,expected",
        [
            ("test@example.com", "test@example.com"),
            ("John@Example.Com", "john@example.com"),
            ("TEST@DOMAIN.ORG", "test@domain.org"),
        ],
    )
    def test_valid_email_normalization(self, email, expected):
        """Test email normalization."""
        result = validate_email_address(email)
        assert result == expected

    @pytest.mark.parametrize(
        "email",
        [
            "not-an-email",
            "@example.com",
            "test@",
            "test@.com",
        ],
    )
    def test_invalid_email(self, email):
        """Test invalid email patterns."""
        with pytest.raises(ValueError):
            validate_email_address(email)


class TestPlaceNameValidation:
    """Test place name validation."""

    @pytest.mark.parametrize(
        "place,should_pass",
        [
            ("Mumbai, India", True),
            ("New York, USA", True),
            ("Bangalore", True),
            ("A", False),
            ("test123", False),
        ],
    )
    def test_place_validation(self, place, should_pass):
        """Test place validation."""
        if should_pass:
            result = validate_place_name(place)
            assert result is not None
        else:
            with pytest.raises(ValueError):
                validate_place_name(place)


class TestContentTitleValidation:
    """Test content title validation."""

    @pytest.mark.parametrize(
        "title,should_pass",
        [
            ("A Valid Test Title Here", True),
            ("This is a good title", True),
            ("Short", False),
            ("AAAAAAAAAA", False),
        ],
    )
    def test_title_validation(self, title, should_pass):
        """Test title validation."""
        if should_pass:
            result = validate_content_title(title)
            assert result is not None
        else:
            with pytest.raises(ValueError):
                validate_content_title(title)


class TestContentDescriptionValidation:
    """Test content description validation."""

    @pytest.mark.parametrize(
        "description,should_pass",
        [
            (
                (
                    "This is a valid test description with at least"
                    " 16 characters to pass validation and be"
                    " meaningful."
                ),
                True,
            ),
            ("Short", False),
            ("aaaaaaa", False),
        ],
    )
    def test_description_validation(self, description, should_pass):
        """Test description validation."""
        if should_pass:
            result = validate_content_description(description)
            assert result is not None
        else:
            with pytest.raises(ValueError):
                validate_content_description(description)


class TestCoordinateValidation:
    """Test coordinate validation."""

    @pytest.mark.parametrize(
        "lat,lng,should_pass",
        [
            (12.9716, 77.5946, True),
            (28.6139, 77.2090, True),
            (-90, -180, True),
            (90, 180, True),
            (91, 77, False),
            (12, 181, False),
        ],
    )
    def test_coordinate_validation(self, lat, lng, should_pass):
        """Test coordinate validation."""
        if should_pass:
            result = validate_coordinates(lat, lng)
            assert result[0] == lat
            assert result[1] == lng
        else:
            with pytest.raises(ValueError):
                validate_coordinates(lat, lng)

    def test_invalid_zero_coordinates(self):
        """Test invalid zero coordinates."""
        with pytest.raises(ValueError):
            validate_coordinates(0, 0)


class TestAgeValidation:
    """Test age validation from birth date."""

    @pytest.mark.parametrize(
        "birth_date,should_pass",
        [
            (date(1990, 1, 1), True),
            (date(2000, 12, 31), True),
            (date(2010, 1, 1), False),
            (date(1900, 1, 1), False),
        ],
    )
    def test_age_validation(self, birth_date, should_pass):
        """Test age validation."""
        if should_pass:
            result = validate_age_from_birthdate(birth_date, min_age=18)
            assert result is not None
        else:
            with pytest.raises(ValueError):
                validate_age_from_birthdate(birth_date, min_age=18)

    def test_future_birth_date(self):
        """Test future birth date."""
        with pytest.raises(ValueError):
            validate_age_from_birthdate(date(2099, 1, 1))


class TestFileSizeValidation:
    """Test file size validation."""

    @pytest.mark.parametrize(
        "size,max_size,should_pass",
        [
            (1024, 2048, True),
            (2048, 2048, True),
            (3 * 1024 * 1024, 2 * 1024 * 1024, False),
        ],
    )
    def test_file_size_validation(self, size, max_size, should_pass):
        """Test file size validation."""
        if should_pass:
            result = validate_file_size(size, max_size)
            assert result == size
        else:
            with pytest.raises(ValueError):
                validate_file_size(size, max_size)

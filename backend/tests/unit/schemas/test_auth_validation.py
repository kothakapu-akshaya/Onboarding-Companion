"""Tests for auth_validation schemas."""

from app.schemas.auth_validation import Gender


class TestGender:
    """Test Gender enum."""

    def test_gender_values(self):
        """Test Gender enum values."""
        assert Gender.male.value == "male"
        assert Gender.female.value == "female"
        assert Gender.other.value == "other"

    def test_gender_is_string_enum(self):
        """Test Gender is a string enum."""
        assert isinstance(Gender.male, str)
        assert Gender.male == "male"

    def test_gender_other(self):
        """Test Gender.other value."""
        assert Gender.other.value == "other"

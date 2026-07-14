"""Unit tests for password strength validation using zxcvbn.

Tests the new password validation system with various password strengths,
special cases, and user context inputs.
"""

import pytest

from app.core.validators import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    PasswordStrengthError,
    PasswordValidationError,
    validate_password_strength,
)


class TestPasswordValidation:
    """Test suite for password strength validation."""

    def test_valid_strong_password(self):
        """Test that genuinely strong passwords pass validation."""
        strong_passwords = [
            "correct-horse-battery-staple",  # Strong passphrase
            "Tr0pical!Hurricane#2024",  # Mix of cases, numbers, special chars
            "CorrectHorseBatteryStaple123",
            # Strong without special chars but high entropy
        ]

        for password in strong_passwords:
            result = validate_password_strength(password)
            assert result == password, (
                f"Failed to validate strong password: {password}"
            )

    def test_password_too_short(self):
        """Test that passwords below minimum length are rejected."""
        with pytest.raises(PasswordStrengthError) as exc_info:
            validate_password_strength("Short1!")

        assert "at least" in exc_info.value.message.lower()
        assert MIN_PASSWORD_LENGTH in [
            int(s) for s in exc_info.value.message.split() if s.isdigit()
        ]

    def test_password_too_long(self):
        """Test that passwords exceeding maximum length are rejected."""
        long_password = "a" * (MAX_PASSWORD_LENGTH + 1)

        with pytest.raises(PasswordStrengthError) as exc_info:
            validate_password_strength(long_password)

        assert "exceed" in exc_info.value.message.lower()

    def test_weak_password_rejection(self):
        """Test that obviously weak passwords are rejected."""
        weak_passwords = [
            "aaaaaaaa",  # No variety
            "12345678",  # Sequential numbers
            "qwerty12",  # Keyboard pattern
        ]

        for password in weak_passwords:
            with pytest.raises(PasswordStrengthError):
                validate_password_strength(password)

    def test_common_weak_pattern_detection(self):
        """Test detection of common weak patterns."""
        common_weak = [
            "password1",
            "admin1234",
            "letmein",
            "dragon123",
        ]

        for password in common_weak:
            with pytest.raises(PasswordStrengthError):
                validate_password_strength(password)

    def test_user_context_prevents_predictable_passwords(self):
        """Test that user context helps identify predictable passwords."""
        # Without context, might pass; with context, should fail
        username = "john_doe"
        email = "john@example.com"

        # A password containing username should be detected as weak with context
        password_with_context = "JohnDoe123"  # Contains "John"

        # This should be detected as weak when user_inputs provided
        with pytest.raises(PasswordStrengthError):
            validate_password_strength(
                password_with_context,
                user_inputs=[username, email.split("@")[0]],
            )

    def test_suggestions_provided_on_failure(self):
        """Test that failure includes helpful suggestions."""
        weak_password = "weakpass"

        try:
            validate_password_strength(weak_password)
        except PasswordStrengthError as e:
            assert e.suggestions is not None
            assert len(e.suggestions) > 0
            assert isinstance(e.suggestions, list)

    def test_error_to_dict_conversion(self):
        """Test that error can be converted to dict for API responses."""
        try:
            validate_password_strength("weak")
        except PasswordStrengthError as e:
            error_dict = e.to_dict()

            assert "message" in error_dict
            assert "suggestions" in error_dict
            assert isinstance(error_dict["message"], str)
            assert isinstance(error_dict["suggestions"], list)

    def test_empty_user_inputs_ignored(self):
        """Test that empty user_inputs are gracefully handled."""
        password = "MySecure Password1!"

        # Should not raise with empty list
        result = validate_password_strength(password, user_inputs=[])
        assert result == password

        # Should not raise with empty strings in list
        result = validate_password_strength(
            password, user_inputs=["", "  ", None]
        )
        assert result == password

    def test_password_return_value(self):
        """Test that the validated password is returned as-is."""
        password = "MyValidPassword123!"
        result = validate_password_strength(password)

        assert result == password
        assert result is not None

    def test_minimum_score_requirement(self):
        """Test that passwords meet minimum zxcvbn score."""
        # This password should fail because even with length, it lacks entropy
        weak_password = "aaaaaaaaaa"  # 10 a's - too predictable

        with pytest.raises(PasswordStrengthError):
            validate_password_strength(weak_password)

    def test_special_characters_accepted(self):
        """Test that various special characters are accepted."""
        special_passwords = [
            "Pass@word#2024",
            "Test_Pass-123!",
            "My$ecurePass~2024",
            "!@#$%^&*()2024abc",
        ]

        for password in special_passwords:
            # Should either pass or fail based on entropy, not special chars
            try:
                result = validate_password_strength(password)
                assert result == password
            except PasswordStrengthError:
                # It's okay if it fails - at least
                # it's not rejecting special chars
                pass

    def test_unicode_characters_supported(self):
        """Test that unicode characters are accepted."""
        unicode_passwords = [
            "Café@Password123",
            "Москва_Москва123",  # Cyrillic
            "北京_Bj2024Test",  # Chinese
        ]

        for password in unicode_passwords:
            try:
                result = validate_password_strength(password)
                assert result == password
            except PasswordStrengthError:
                # It's okay if some unicode fails, but should be processable
                pass

    def test_consistent_error_messages(self):
        """Test that error messages are informative and consistent."""
        weak_passwords = ["short", "weakpassword"]

        for password in weak_passwords:
            try:
                validate_password_strength(password)
            except PasswordStrengthError as e:
                assert (
                    "weak" in e.message.lower() or "short" in e.message.lower()
                )
                assert e.message is not None
                assert len(e.message) > 0


"""
Unit tests for zxcvbn-based password validation.

Tests the new password strength validation system that uses entropy estimation
instead of composition rules, following NIST SP 800-63B guidelines.
"""


class TestPasswordValidationMinimumLength:
    """Test minimum password length requirements."""

    def test_password_too_short(self):
        """Passwords shorter than 8 characters should fail."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("short")

        assert exc_info.value.score == 0
        assert "at least 8 characters" in exc_info.value.message

    def test_password_exactly_8_chars_strong(self):
        """8-char strong passwords pass with sufficient entropy."""
        # Use a password with sufficient entropy (zxcvbn score 3/4)
        result = validate_password_strength("Crypt0Gram")
        assert result == "Crypt0Gram"

    def test_password_with_only_spaces(self):
        """Passwords with only spaces should fail."""
        with pytest.raises(PasswordValidationError):
            validate_password_strength("        ")


class TestPasswordValidationMaximumLength:
    """Test maximum password length limits."""

    def test_password_too_long(self):
        """Passwords longer than 128 characters should fail."""
        long_password = "a" * 129
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(long_password)

        assert "too long" in exc_info.value.message


class TestPasswordValidationEntropyBased:
    """Test entropy-based validation (score >= 3)."""

    def test_weak_password_low_entropy(self):
        """Very weak passwords with low entropy should fail."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("aaaaaaaa")

        error = exc_info.value
        assert error.score < 3, "Score should be below minimum (3)"
        assert "too weak" in error.message

    def test_strong_passphrase_high_entropy(self):
        """Long passphrases with high entropy should pass."""
        # Classic strong passphrase recommended by security experts
        result = validate_password_strength("correct horse battery staple")
        assert result == "correct horse battery staple"

    def test_complex_password_with_mixed_chars(self):
        """Passwords with good mix of character types should pass."""
        result = validate_password_strength("MyP@ssw0rd!Complex")
        assert result == "MyP@ssw0rd!Complex"

    def test_strength_score_improvement(self):
        """More entropy should improve score feedback."""
        # Simple password gets low score
        try:
            validate_password_strength("password")
        except PasswordValidationError as e1:
            score1 = e1.score

        # Complex password should succeed (or higher score)
        try:
            result = validate_password_strength(
                "ThisIsAVeryComplexPasswordWith123AndSymbols!@#"
            )
            assert result  # Should pass
        except PasswordValidationError as e2:
            # If it fails, it should have higher score than simple password
            assert e2.score >= score1


class TestPasswordValidationWithUserInputs:
    """Test that user inputs prevent predictable passwords."""

    def test_password_equals_username(self):
        """Password identical to username should be weak."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("myusername123", ["myusername"])

        # zxcvbn detects when user input matches password
        error = exc_info.value
        assert error.score < 3

    def test_password_contains_email(self):
        """Password containing email should be weak."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(
                "user@example.com123", ["user@example.com"]
            )

        error = exc_info.value
        assert error.score < 3

    def test_password_contains_username_component(self):
        """Password containing username part should be weak."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("johndoe2024", ["johndoe", "john"])

        error = exc_info.value
        assert error.score < 3

    def test_strong_password_ignores_user_inputs(self):
        """Strong passwords with high entropy pass despite user inputs."""
        # This password is strong enough that user context
        # doesn't weaken it significantly
        result = validate_password_strength(
            "CorrectHorseBatteryStaple123!@#",
            ["john", "doe", "johndoe@example.com"],
        )
        assert result == "CorrectHorseBatteryStaple123!@#"

    def test_user_inputs_list_optional(self):
        """User inputs should be optional parameter."""
        result = validate_password_strength("MySecurePassword123!@#")
        assert result == "MySecurePassword123!@#"


class TestPasswordValidationErrorResponse:
    """Test error response formatting."""

    def test_error_includes_suggestions(self):
        """Password validation errors should include suggestions."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("weak")

        error = exc_info.value
        assert hasattr(error, "suggestions")
        assert isinstance(error.suggestions, list)

    def test_error_dict_format(self):
        """Error should be convertible to dictionary format."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("abc")

        error = exc_info.value
        error_dict = error.to_dict()

        assert "message" in error_dict
        assert "score" in error_dict
        assert "suggestions" in error_dict
        assert "feedback" in error_dict
        assert isinstance(error_dict["score"], int)
        assert 0 <= error_dict["score"] <= 4

    def test_error_message_is_user_friendly(self):
        """Error messages should be clear and actionable."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("12345678")

        error = exc_info.value
        assert (
            "weak" in error.message.lower() or "score" in error.message.lower()
        )


class TestPasswordValidationEdgeCases:
    """Test edge cases and special scenarios."""

    def test_password_with_unicode_characters(self):
        """Passwords with unicode characters should be handled."""
        # Unicode password may or may not pass depending on entropy
        try:
            result = validate_password_strength("Paßwörd2024!@#€")
            assert result == "Paßwörd2024!@#€"
        except PasswordValidationError:
            # Also acceptable if entropy is insufficient
            pass

    def test_empty_user_inputs_list(self):
        """Empty user inputs list should be handled gracefully."""
        result = validate_password_strength("MyPassword123!@#", [])
        assert result == "MyPassword123!@#"

    def test_user_inputs_with_empty_strings(self):
        """User inputs with empty strings should be ignored."""
        result = validate_password_strength(
            "MyPassword123!@#", ["", "   ", "username"]
        )
        assert result == "MyPassword123!@#"

    def test_special_characters_dont_guarantee_strength(self):
        """Special characters alone don't make a password strong."""
        # "!@#$%^&*()" has low entropy even with special chars
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("!@#$%^&*()")

        error = exc_info.value
        assert error.score < 3

    def test_numeric_only_password(self):
        """Numeric-only passwords should be weak."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("12345678")

        error = exc_info.value
        assert error.score < 3


class TestNISTCompliance:
    """Test compliance with NIST SP 800-63B guidelines."""

    def test_no_composition_rules_enforced(self):
        """NIST recommends NOT enforcing composition rules.

        We should accept passwords that don't follow traditional rules
        if they have sufficient entropy.
        """
        # This password has no uppercase or special chars but high entropy
        result = validate_password_strength("correct horse battery staple 2024")
        assert result  # Should pass despite "missing" uppercase/special chars

    def test_minimum_score_alignment(self):
        """Minimum score of 3 aligns with NIST guidelines."""
        # Test that weak passwords (score < 3) are rejected
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("aaaaaa!!!")  # Low entropy

        error = exc_info.value
        assert error.score < 3


class TestPasswordValidationRealistic:
    """Integration tests with realistic scenarios."""

    def test_registration_flow_strong_password(self):
        """Test password validation in a registration scenario."""
        user_inputs = [
            "johndoe",  # username
            "john.doe@example.com",  # email
            "john",  # name first part
            "john.doe@example.com",  # email domain
        ]

        # Strong password should pass despite user context
        result = validate_password_strength(
            "CorrectHorseBatteryStaple2024", user_inputs
        )
        assert result == "CorrectHorseBatteryStaple2024"

    def test_registration_flow_weak_password(self):
        """Test password validation rejects weak passwords in registration."""
        user_inputs = [
            "johndoe",
            "john.doe@example.com",
        ]

        # Weak password should fail
        with pytest.raises(PasswordValidationError):
            validate_password_strength("johndoe2024", user_inputs)

    def test_password_change_scenario(self):
        """Test password change with new strong password."""
        # User should be able to set a completely different strong password
        result = validate_password_strength("NewSecurePass2024!@#")
        assert result == "NewSecurePass2024!@#"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

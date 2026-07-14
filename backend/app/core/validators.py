"""Core atomic validation functions.

These are low-level, reusable validation utilities used across validation
modules.
"""

import re
from datetime import date
from typing import Any

from zxcvbn import zxcvbn

MAX_PASSWORD_LENGTH = 128
MIN_PASSWORD_LENGTH = 8
MIN_PASSWORD_SCORE = 3  # 0-4 scale from zxcvbn


class PasswordStrengthError(ValueError):
    """Exception raised when password validation fails."""

    def __init__(
        self,
        message: str,
        suggestions: list[str] | None = None,
        score: int | None = None,
        feedback: dict[str, Any] | None = None,
    ):
        """Initialize the PasswordStrengthError."""
        self.message = message
        self.suggestions = suggestions or []
        self.score = score
        self.feedback = feedback or {
            "warning": "",
            "suggestions": self.suggestions,
        }
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format for API responses."""
        payload: dict[str, Any] = {
            "message": self.message,
            "suggestions": self.suggestions,
            "feedback": self.feedback,
        }
        if self.score is not None:
            payload["score"] = self.score
        return payload


class PasswordValidationError(PasswordStrengthError):
    """Legacy alias for password validation errors."""

    def __init__(
        self,
        message: str,
        suggestions: list[str] | None = None,
        score: int | None = None,
        feedback: dict[str, Any] | None = None,
    ):
        """Initialize the PasswordValidationError."""
        super().__init__(message, suggestions, score, feedback)


def validate_password_strength(
    password: str, user_inputs: list[str] | None = None
) -> str:
    """Validate password strength using zxcvbn algorithm.

    Uses entropy-based analysis instead of composition rules
    (NIST SP 800-63B compliant).
    Requires a minimum score of 3 out of 4 to be considered strong.

    Args:
        password: The password to validate
        user_inputs: Optional list of user-specific context (e.g., username,
                    email, app name) used to prevent predictable patterns

    Returns:
        str: The validated password itself if validation passes

    Raises:
        PasswordStrengthError: If password doesn't meet strength requirements
                              with suggestions for improvement
    """
    # Basic length validation
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordValidationError(
            f"Password is too short. Please use at least "
            f"{MIN_PASSWORD_LENGTH} characters.",
            suggestions=["Use a longer password"],
            score=0,
            feedback={
                "warning": "Password is too short.",
                "suggestions": ["Use a longer password"],
            },
        )

    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordValidationError(
            f"Password is too long and exceeds the maximum length of "
            f"{MAX_PASSWORD_LENGTH} characters.",
            suggestions=["Use a shorter password"],
            score=0,
            feedback={
                "warning": "Password is too long and exceeds maximum length.",
                "suggestions": ["Use a shorter password"],
            },
        )

    # Use zxcvbn for strength estimation
    # user_inputs helps zxcvbn detect common patterns related to user info
    context = user_inputs or []
    result = zxcvbn(password, user_inputs=context)

    score = result.get("score", 0)
    feedback = result.get("feedback", {})

    # Check if password meets minimum score requirement
    if score < MIN_PASSWORD_SCORE:
        # Collect all suggestions from feedback
        suggestions = []

        # Add warning if present
        if feedback.get("warning"):
            suggestions.append(f"Warning: {feedback['warning']}")

        # Add all suggestions
        if feedback.get("suggestions"):
            suggestions.extend(feedback["suggestions"])

        # Provide default suggestion if none available
        if not suggestions:
            suggestions.append("Choose a password with more variety and length")

        error_message = (
            f"Password is too weak (score: {score}/4). "
            "Please choose a stronger password with better variety."
        )

        raise PasswordValidationError(
            error_message,
            suggestions,
            score=score,
            feedback={
                "warning": feedback.get("warning", ""),
                "suggestions": feedback.get("suggestions", []),
            },
        )

    return password


def validate_phone(phone: str, country_code: str = "91") -> str:
    """Validate and format phone number for Indian numbers.

    Args:
        phone: Phone number to validate
        country_code: Country code (default: "91" for India)

    Returns:
        str: Formatted phone number with country code

    Raises:
        ValueError: If phone number is invalid
    """
    # Remove all non-digit characters
    cleaned = re.sub(r"\D", "", phone)

    # Handle different input formats
    if len(cleaned) == 10:
        digits = cleaned
    elif cleaned.startswith(country_code) and len(cleaned) == 12:
        digits = cleaned[2:]
    else:
        raise ValueError("Phone number must be 10 digits")

    # Validate digits
    if not digits.isdigit():
        raise ValueError("Phone number must contain only digits")

    # Indian phone number specific validation
    if country_code == "91":
        if int(digits[0]) <= 5:
            raise ValueError(
                "Indian phone numbers must start with a digit greater than 5"
            )

    return f"+{country_code}{digits}"


def validate_email_address(email: str) -> str:
    """Validate and normalize email address format.

    Args:
        email: Email address to validate

    Returns:
        str: Normalized email address

    Raises:
        ValueError: If email format is invalid
    """
    if not email or not email.strip():
        raise ValueError("Email address is required")

    # Normalize email
    normalized = email.strip().lower()

    # Enhanced email validation pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(pattern, normalized):
        raise ValueError("Invalid email address format")

    # Check for suspicious patterns
    if normalized.count("@") != 1:
        raise ValueError("Email must contain exactly one @ symbol")

    local, domain = normalized.split("@")

    # Local part validation
    if len(local) > 64:
        raise ValueError("Email local part too long (max 64 characters)")

    # Domain part validation
    if len(domain) > 255:
        raise ValueError("Email domain part too long (max 255 characters)")

    return normalized


def validate_place_name(place: str) -> str:
    """Comprehensive validation for place/location names.

    Args:
        place: Place name to validate

    Returns:
        str: Cleaned place name

    Raises:
        ValueError: If place name is invalid
    """
    if not place or not place.strip():
        raise ValueError("Place is required and cannot be empty")

    cleaned = place.strip()

    # Length validation
    if len(cleaned) < 2:
        raise ValueError("Place must be at least 2 characters long")

    if len(cleaned) > 200:
        raise ValueError("Place name is too long (maximum 200 characters)")

    # Character validation - allow letters, spaces, numbers, and common
    # location characters
    if not re.match(r"^[a-zA-Z0-9\s,.\-'()]+$", cleaned):
        raise ValueError(
            "Place should contain only letters, numbers, spaces, commas, "
            "periods, hyphens, apostrophes, and parentheses"
        )

    # Check for meaningful content (not just repeated characters or spaces)
    unique_chars = set(
        cleaned.lower().replace(" ", "").replace(",", "").replace(".", "")
    )
    if len(unique_chars) < 2:
        raise ValueError(
            "Place must contain meaningful content, not just repeated "
            "characters"
        )

    # Prevent obviously fake or test entries
    suspicious_patterns = [
        r"^test\d*$",
        r"^dummy\d*$",
        r"^fake\d*$",
        r"^sample\d*$",
        r"^placeholder\d*$",
        r"^temp\d*$",
        r"^xxx+$",
        r"^aaa+$",
        r"^111+$",
        r"^na$",
        r"^n/a$",
        r"^none$",
        r"^null$",
        r"^undefined$",
    ]

    for pattern in suspicious_patterns:
        if re.match(pattern, cleaned.lower()):
            raise ValueError(
                "Please provide a valid place name, not a test or "
                "placeholder value"
            )

    # Check for excessive punctuation (might indicate spam)
    punct_count = sum(1 for c in cleaned if c in ",.'-")
    if punct_count > len(cleaned) * 0.3:  # More than 30% punctuation
        raise ValueError("Place contains too much punctuation")

    # Check for reasonable word structure
    words = cleaned.split()
    if len(words) > 10:  # Too many words might indicate spam
        raise ValueError("Place name is too complex (maximum 10 words)")

    # Validate each word isn't too long (likely spam/gibberish)
    for word in words:
        if len(word) > 50:  # Single word too long
            raise ValueError("Place contains words that are too long")
        # Check for gibberish (no vowels in long words)
        if len(word) > 8 and not re.search(r"[aeiouAEIOU]", word):
            raise ValueError(f"'{word}' doesn't appear to be a valid word")

    # Check for numeric-only entries (like zip codes alone)
    if cleaned.isdigit():
        raise ValueError(
            "Place cannot be just numbers. Please include city/location name"
        )

    # Basic format validation for common place patterns
    # Allow: "City", "City, State", "City, Country", etc.
    if "," in cleaned:
        parts = [part.strip() for part in cleaned.split(",")]
        for part in parts:
            if not part:  # Empty part between commas
                raise ValueError(
                    "Place format is invalid (empty parts between commas)"
                )
            if len(part) < 1:
                raise ValueError(
                    "Each part of the place must have meaningful content"
                )

    # Check for balanced parentheses
    if cleaned.count("(") != cleaned.count(")"):
        raise ValueError("Unbalanced parentheses in place name")

    return cleaned


def validate_content_title(title: str) -> str:
    """Validate content title quality and format.

    Args:
        title: Title to validate

    Returns:
        str: Cleaned title

    Raises:
        ValueError: If title is invalid
    """
    if not title:
        raise ValueError("Title is required")

    cleaned = title.strip()

    if len(cleaned) < 8:
        raise ValueError("Title must be at least 8 characters long")

    if len(cleaned) > 200:
        raise ValueError("Title must not exceed 200 characters")

    # Check for meaningful content
    if len(set(cleaned.lower().replace(" ", ""))) < 3:
        raise ValueError(
            "Title must contain meaningful content, not just repeated "
            "characters"
        )

    # Discourage all caps
    if cleaned.isupper() and len(cleaned) > 10:
        raise ValueError("Please use proper capitalization instead of ALL CAPS")

    return cleaned


def validate_content_description(description: str) -> str:
    """Validate content description quality and format.

    Args:
        description: Description to validate

    Returns:
        str: Cleaned description

    Raises:
        ValueError: If description is invalid
    """
    if not description:
        raise ValueError("Description is required")

    cleaned = description.strip()

    if len(cleaned) < 16:
        raise ValueError("Description must be at least 16 characters long")

    if len(cleaned) > 2000:
        raise ValueError("Description must not exceed 2000 characters")

    # Check for meaningful content
    word_count = len(cleaned.split())
    if word_count < 5:
        raise ValueError(
            "Description should contain at least 5 meaningful words"
        )

    unique_chars = len(
        set(cleaned.lower().replace(" ", "").replace(".", "").replace(",", ""))
    )
    if unique_chars < 5:
        raise ValueError(
            "Description must contain meaningful and varied content"
        )

    return cleaned


def validate_file_size(
    size_bytes: int, max_size: int, min_size: int = 1024
) -> int:
    """Validate file size within specified limits.

    Args:
        size_bytes: File size in bytes
        max_size: Maximum allowed size in bytes
        min_size: Minimum allowed size in bytes

    Returns:
        int: Validated file size

    Raises:
        ValueError: If file size is invalid
    """
    if size_bytes < min_size:
        raise ValueError(
            f"File too small: {size_bytes} bytes. Minimum: {min_size} bytes"
        )

    if size_bytes > max_size:
        size_mb = size_bytes / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        raise ValueError(
            f"File too large: {size_mb:.1f}MB. Maximum: {max_mb:.1f}MB"
        )

    return size_bytes


def validate_coordinates(
    latitude: float, longitude: float
) -> tuple[float, float]:
    """Validate geographic coordinates.

    Args:
        latitude: Latitude value
        longitude: Longitude value

    Returns:
        tuple: Validated (latitude, longitude)

    Raises:
        ValueError: If coordinates are invalid
    """
    if not isinstance(latitude, (int, float)) or not isinstance(
        longitude, (int, float)
    ):
        raise ValueError("Coordinates must be numeric values")

    if not (-90 <= latitude <= 90):
        raise ValueError(
            f"Latitude {latitude} is out of valid range (-90 to 90 degrees)"
        )

    if not (-180 <= longitude <= 180):
        raise ValueError(
            f"Longitude {longitude} is out of valid range (-180 to 180 degrees)"
        )

    # Check for obviously invalid coordinates
    if latitude == 0 and longitude == 0:
        raise ValueError(
            "Coordinates (0,0) appear to be invalid. Please provide actual "
            "location"
        )

    return float(latitude), float(longitude)


def validate_age_from_birthdate(
    birth_date: date, min_age: int = 13, max_age: int = 120
) -> str:
    """Validate age requirements based on birth date.

    Args:
        birth_date: Date of birth
        min_age: Minimum allowed age
        max_age: Maximum allowed age

    Returns:
        str: Validated birth date as string

    Raises:
        ValueError: If age is invalid
    """
    if not isinstance(birth_date, date):
        raise ValueError("Birth date must be a valid date")

    today = date.today()

    if birth_date > today:
        raise ValueError("Date of birth cannot be in the future")

    age = (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )

    if age < min_age:
        raise ValueError(f"You must be at least {min_age} years old")

    if age > max_age:
        raise ValueError(
            f"Please enter a valid date of birth (maximum age: {max_age})"
        )

    return str(birth_date)

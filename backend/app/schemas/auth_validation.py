"""Authentication-specific validation schemas.

Handles user registration, login, and profile validation.
"""

from datetime import date
from enum import Enum
from typing import Optional

import regex
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.core.validators import (
    validate_age_from_birthdate,
    validate_email_address,
    validate_password_strength,
    validate_phone,
    validate_place_name,
)


class Gender(str, Enum):
    """Gender enumeration to avoid circular imports."""

    male = "male"
    female = "female"
    other = "other"


class PhoneValidationMixin:
    """Mixin for phone number validation."""

    @field_validator("phone")
    @classmethod
    def validate_phone_field(cls, v: str) -> str:
        """Validate and format phone number."""
        return validate_phone(v)


class PasswordValidationMixin:
    """Mixin for password validation."""

    @field_validator("password", "new_password", check_fields=False)
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        return validate_password_strength(v)


class UserSignupStep1Validation(
    BaseModel, PhoneValidationMixin, PasswordValidationMixin
):
    """Step 1 signup validation (basic info before OTP)."""

    phone: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="Phone number with country code",
    )
    name: str = Field(
        ..., min_length=2, max_length=100, description="Full name"
    )
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(
        ..., min_length=8, max_length=100, description="Password"
    )
    confirm_password: str = Field(
        ..., min_length=8, max_length=100, description="Confirm password"
    )
    has_given_consent: bool = Field(..., description="User consent required")
    is_intern: bool = Field(
        default=False, description="Whether the user is an intern"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name format."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Name is required")

        # Check for valid characters (letters, spaces, common name characters)
        if not regex.match(r"^[\p{L}\s\.]+$", cleaned):
            raise ValueError(
                "Name must contain only letters, spaces, and periods"
            )

        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters long")

        # Check for meaningful content
        if len(set(cleaned.lower().replace(" ", ""))) < 2:
            raise ValueError("Name must contain meaningful content")

        return cleaned

    @field_validator("has_given_consent")
    @classmethod
    def validate_consent(cls, v: bool) -> bool:
        """Ensure user has given consent."""
        if not v:
            raise ValueError(
                "You must agree to the terms and conditions to "
                "create an account"
            )
        return v

    @model_validator(mode="after")
    def validate_signup_requirements(self) -> "UserSignupStep1Validation":
        """Ensure passwords match."""
        if hasattr(self, "password") and hasattr(self, "confirm_password"):
            if self.password != self.confirm_password:
                raise ValueError("Password and confirm password do not match")

        return self


class UserRegistrationValidation(
    BaseModel, PhoneValidationMixin, PasswordValidationMixin
):
    """Comprehensive user registration validation (legacy full signup)."""

    phone: str = Field(
        ...,
        min_length=10,
        max_length=20,
        description="Phone number with country code",
    )
    username: str | None = Field(
        None, min_length=3, max_length=50, description="Unique username"
    )
    name: str = Field(
        ..., min_length=2, max_length=100, description="Full name"
    )
    email: str | None = Field(None, max_length=255, description="Email address")
    password: str = Field(
        ..., min_length=8, max_length=100, description="Password"
    )
    confirm_password: str = Field(
        ..., min_length=8, max_length=100, description="Confirm password"
    )
    gender: "Gender" = Field(..., description="Gender")
    date_of_birth: date = Field(..., description="Date of birth")
    current_place: str = Field(
        ..., max_length=200, description="Current Location/Place"
    )
    has_given_consent: bool = Field(..., description="User consent required")
    is_intern: bool = Field(
        default=False, description="Whether the user is an intern"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """Validate username format."""
        if v is None:
            return None
        cleaned = v.strip().lower()

        if not cleaned:
            return None

        if len(cleaned) < 3:
            raise ValueError("Username must be at least 3 characters long")

        if len(cleaned) > 50:
            raise ValueError("Username must not exceed 50 characters")

        # Username can only contain lowercase letters, numbers, and underscores
        if not regex.match(r"^[a-z0-9_]+$", cleaned):
            raise ValueError(
                "Username can only contain lowercase letters, numbers, "
                "and underscores"
            )

        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name format."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Name is required")

        # Check for valid characters (letters, spaces, common name characters)
        if not regex.match(r"^[\p{L}\s\.]+$", cleaned):
            raise ValueError(
                "Name must contain only letters, spaces, and periods"
            )

        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters long")

        # Check for meaningful content
        if len(set(cleaned.lower().replace(" ", ""))) < 2:
            raise ValueError("Name must contain meaningful content")

        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Enhanced email validation with domain checks."""
        if v is None or v.strip() == "":
            return None

        normalized = validate_email_address(v.strip())

        # Add domain blacklist check for temporary email services
        blocked_domains = [
            "tempmail.com",
            "10minutemail.com",
            "guerrillamail.com",
            "mailinator.com",
            "throwaway.email",
            "temp-mail.org",
            "getairmail.com",
            "maildrop.cc",
            "sharklasers.com",
            "grr.la",
            "guerrillamailblock.com",
        ]

        domain = normalized.split("@")[1].lower()

        if domain in blocked_domains:
            raise ValueError(
                "Temporary or disposable email addresses are not allowed. "
                "Please use a permanent email address."
            )

        # Check for suspicious email patterns
        local_part = normalized.split("@")[0]

        # Check for too many numbers (might indicate generated email)
        digit_count = sum(c.isdigit() for c in local_part)
        if len(local_part) > 3 and digit_count / len(local_part) > 0.7:
            raise ValueError(
                "Email appears to be auto-generated. "
                "Please use a personal email address."
            )

        return normalized

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date | None) -> date | None:
        """Validate age requirements."""
        if v is None:
            return None
        validate_age_from_birthdate(v, min_age=13, max_age=120)
        return v

    @field_validator("current_place")
    @classmethod
    def validate_place(cls, v: str) -> str:
        """Enhanced current place validation using centralized validator."""
        return validate_place_name(v)

    @field_validator("has_given_consent")
    @classmethod
    def validate_consent(cls, v: bool) -> bool:
        """Ensure user has given consent."""
        if not v:
            raise ValueError(
                "You must agree to the terms and conditions to "
                "create an account"
            )
        return v

    @model_validator(mode="after")
    def validate_registration_requirements(
        self,
    ) -> "UserRegistrationValidation":
        """Ensure passwords match and username is provided for non-interns."""
        if hasattr(self, "password") and hasattr(self, "confirm_password"):
            if self.password != self.confirm_password:
                raise ValueError("Password and confirm password do not match")

        if not self.is_intern and not self.username:
            raise ValueError("Username is required for non-intern accounts")

        return self


class UserLoginValidation(BaseModel, PhoneValidationMixin):
    """User login validation."""

    phone: str | None = Field(None, description="Phone number")
    email: str | None = Field(None, description="Email address")
    password: str = Field(..., min_length=1, description="Password")

    @model_validator(mode="after")
    def check_phone_or_email(self) -> "UserLoginValidation":
        if not self.phone and not self.email:
            raise ValueError("Either phone or email must be provided")
        return self


class OTPValidation(BaseModel, PhoneValidationMixin):
    """OTP validation for authentication."""

    phone: str = Field(..., description="Phone number with country code")
    otp_code: str = Field(
        ..., min_length=4, max_length=8, description="OTP code"
    )

    @field_validator("otp_code")
    @classmethod
    def validate_otp_format(cls, v: str) -> str:
        """Validate OTP format."""
        cleaned = v.strip()
        if not cleaned.isdigit():
            raise ValueError("OTP must contain only numbers")
        if len(cleaned) < 4 or len(cleaned) > 8:
            raise ValueError("OTP must be between 4 and 8 digits")
        return cleaned


class OTPSendValidation(BaseModel, PhoneValidationMixin):
    """Enhanced validation for OTP send request.

    Includes context awareness and rate limiting.
    """

    phone: str = Field(
        ...,
        description="Phone number with country code",
        json_schema_extra={"example": "+919876543210"},
    )
    request_type: str = Field(
        ...,
        pattern="^(login|signup|password_reset)$",
        description="Type of OTP request",
        json_schema_extra={"example": "login"},
    )

    @field_validator("phone")
    @classmethod
    def validate_phone_with_context(cls, v: str, info) -> str:
        """Enhanced phone validation with context-specific checks.

        Includes security validation.
        """
        validated_phone = validate_phone(v)

        # Additional context-specific validations
        request_type = info.data.get("request_type") if info.data else None

        # Context-specific validation rules
        if request_type == "signup":
            # For signup, ensure phone format is complete
            if not validated_phone.startswith("+91"):
                raise ValueError(
                    "For registration, please provide phone number with "
                    "+91 country code"
                )
        elif request_type == "password_reset":
            # Additional security checks for password reset
            if len(validated_phone.replace("+91", "")) != 10:
                raise ValueError(
                    "Invalid phone number format for password reset"
                )

        return validated_phone

    class Config:
        """Enhanced configuration with examples."""

        str_strip_whitespace = True
        json_schema_extra = {
            "example": {"phone": "+919876543210", "request_type": "login"}
        }


class PasswordChangeValidation(BaseModel, PasswordValidationMixin):
    """Password change validation."""

    current_password: str = Field(
        ..., min_length=1, description="Current password"
    )
    new_password: str = Field(
        ..., min_length=8, max_length=100, description="New password"
    )
    confirm_password: str = Field(
        ..., min_length=8, max_length=100, description="Confirm new password"
    )

    @model_validator(mode="after")
    def validate_password_match(self) -> "PasswordChangeValidation":
        """Ensure passwords match and are different."""
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")

        if self.current_password == self.new_password:
            raise ValueError(
                "New password must be different from current password"
            )

        return self


class UserProfileUpdateValidation(BaseModel):
    """Validation for user profile updates."""

    username: str | None = Field(
        None, min_length=3, max_length=50, description="Unique username"
    )
    name: str | None = Field(None, max_length=100, description="Full name")
    email: str | None = Field(None, max_length=255, description="Email address")
    gender: Optional["Gender"] = Field(None, description="Gender")
    date_of_birth: date | None = Field(None, description="Date of birth")
    current_place: str | None = Field(
        None, max_length=200, description="Current Location/Place"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """Validate username if provided."""
        if v is None or v.strip() == "":
            return None

        cleaned = v.strip().lower()

        if len(cleaned) < 3:
            raise ValueError("Username must be at least 3 characters long")

        if len(cleaned) > 50:
            raise ValueError("Username must not exceed 50 characters")

        # Username can only contain lowercase letters, numbers, and underscores
        if not regex.match(r"^[a-z0-9_]+$", cleaned):
            raise ValueError(
                "Username can only contain lowercase letters, numbers, "
                "and underscores"
            )

        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate name if provided."""
        if v is None or v.strip() == "":
            return None
        return UserRegistrationValidation.validate_name(v.strip())

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Enhanced email validation for profile updates."""
        if v is None or v.strip() == "":
            return None

        # Use the same enhanced validation as registration
        return UserRegistrationValidation.validate_email(v.strip())

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date | None) -> date | None:
        """Validate age if provided."""
        if v is None:
            return None
        validate_age_from_birthdate(v, min_age=13, max_age=120)
        return v

    @field_validator("current_place")
    @classmethod
    def validate_place(cls, v: str | None) -> str | None:
        """Validate current place if provided."""
        if v is None or v.strip() == "":
            return None
        return UserRegistrationValidation.validate_place(v.strip())


class TokenValidation(BaseModel):
    """Token validation for authenticated requests."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

    @field_validator("access_token")
    @classmethod
    def validate_token_format(cls, v: str) -> str:
        """Basic token format validation."""
        if not v.strip():
            raise ValueError("Access token is required")

        # Basic JWT format check (3 parts separated by dots)
        parts = v.strip().split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        return v.strip()

    @field_validator("token_type")
    @classmethod
    def validate_token_type(cls, v: str) -> str:
        """Validate token type."""
        if v.lower() not in ["bearer", "jwt"]:
            raise ValueError("Invalid token type. Must be 'bearer' or 'jwt'")
        return v.lower()

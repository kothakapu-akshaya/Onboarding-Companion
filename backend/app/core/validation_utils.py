"""Centralized validation utilities for FastAPI.

Provides common validation helpers and error formatting utilities.
"""

import logging
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


class ValidationErrorFormatter:
    """Enhanced error formatting for Pydantic validation errors."""

    @staticmethod
    def format_validation_error(error: ValidationError) -> str:
        """Format Pydantic validation errors into user-friendly messages.

        Args:
            error: Pydantic ValidationError instance

        Returns:
            str: Formatted error message
        """
        errors = []

        for err in error.errors():
            field_path = " -> ".join(str(loc) for loc in err["loc"])
            error_type = err["type"]
            message = err["msg"]

            # Customize error messages for better UX
            if error_type == "value_error.missing":
                errors.append(f"{field_path}: This field is required")
            elif error_type == "value_error.str.regex":
                errors.append(f"{field_path}: Invalid format - {message}")
            elif error_type == "value_error.number.not_ge":
                errors.append(
                    f"{field_path}: Value must be greater than or equal to the "
                    "minimum"
                )
            elif error_type == "value_error.str.max_length":
                errors.append(
                    f"{field_path}: Text is too long (maximum length exceeded)"
                )
            elif error_type == "value_error.str.min_length":
                errors.append(
                    f"{field_path}: Text is too short (minimum length not met)"
                )
            else:
                # Use custom message if available, otherwise use default
                errors.append(f"{field_path}: {message}")

        return "; ".join(errors)

    @staticmethod
    def create_validation_http_exception(
        error: ValidationError, status_code: int = 422
    ) -> HTTPException:
        """Create HTTPException from Pydantic ValidationError.

        With enhanced formatting.

        Args:
            error: Pydantic ValidationError instance
            status_code: HTTP status code (default 422)

        Returns:
            HTTPException: Formatted exception ready to be raised
        """
        formatted_message = ValidationErrorFormatter.format_validation_error(
            error
        )
        return HTTPException(status_code=status_code, detail=formatted_message)


class ValidationContext:
    """Context manager for validation operations with enhanced logging."""

    def __init__(self, operation: str, user_id: str | None = None):
        """Initialize the ValidationContext."""
        self.operation = operation
        self.user_id = user_id

    def __enter__(self):  # noqa: D105
        logger.info(
            f"Starting validation: {self.operation} for user {self.user_id}"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: D105
        if exc_type is None:
            logger.info(f"Validation completed successfully: {self.operation}")
        else:
            logger.warning(
                f"Validation failed: {self.operation} - {str(exc_val)}"
            )
        return False  # Don't suppress exceptions


def validate_with_enhanced_errors(
    model_class, data: dict[str, Any], **kwargs
) -> Any:
    """Validate data using a Pydantic model with enhanced error handling.

    Args:
        model_class: Pydantic model class
        data: Data to validate
        **kwargs: Additional arguments for model instantiation

    Returns:
        Validated model instance

    Raises:
        HTTPException: On validation failure with formatted errors
    """
    try:
        return model_class(**data, **kwargs)
    except ValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected validation error: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Internal server error during validation"
        )


# Async Database Validators
async def validate_phone_unique(
    phone: str, session: Session, exclude_user_id: str | None = None
) -> str:
    """Validate that phone number is unique in the database.

    Args:
        phone: Phone number to validate
        session: Database session
        exclude_user_id: User ID to exclude from uniqueness check (for updates)

    Returns:
        str: The validated phone number

    Raises:
        ValueError: If phone number already exists
    """
    from app.models.user import User

    query = select(User).where(User.phone == phone)
    if exclude_user_id:
        query = query.where(User.id != exclude_user_id)

    existing_user = session.exec(query).first()
    if existing_user:
        raise ValueError(
            "This phone number is already registered. Please use a different "
            "phone number or login with existing account."
        )

    return phone


async def validate_email_unique(
    email: str, session: Session, exclude_user_id: str | None = None
) -> str:
    """Validate that email is unique in the database.

    Args:
        email: Email to validate
        session: Database session
        exclude_user_id: User ID to exclude from uniqueness check (for updates)

    Returns:
        str: The validated email

    Raises:
        ValueError: If email already exists
    """
    from app.models.user import User

    if not email or email.strip() == "":
        return email

    query = select(User).where(User.email == email)
    if exclude_user_id:
        query = query.where(User.id != exclude_user_id)

    existing_user = session.exec(query).first()
    if existing_user:
        raise ValueError(
            "This email address is already registered. Please use a different "
            "email or login with existing account."
        )

    return email


async def validate_user_data_async(
    data: dict[str, Any], session: Session, exclude_user_id: str | None = None
) -> dict[str, Any]:
    """Perform async validation for user data.

    Includes database uniqueness checks.

    Args:
        data: User data to validate
        session: Database session
        exclude_user_id: User ID to exclude from uniqueness checks (for updates)

    Returns:
        Dict[str, Any]: Validated data

    Raises:
        ValueError: If validation fails
    """
    validated_data = data.copy()

    # Validate phone uniqueness if present
    if "phone" in validated_data:
        validated_data["phone"] = await validate_phone_unique(
            validated_data["phone"], session, exclude_user_id
        )

    # Validate email uniqueness if present
    if "email" in validated_data and validated_data["email"]:
        validated_data["email"] = await validate_email_unique(
            validated_data["email"], session, exclude_user_id
        )

    return validated_data


# Export commonly used utilities
__all__ = [
    "ValidationErrorFormatter",
    "ValidationContext",
    "validate_with_enhanced_errors",
    "validate_phone_unique",
    "validate_email_unique",
    "validate_user_data_async",
]

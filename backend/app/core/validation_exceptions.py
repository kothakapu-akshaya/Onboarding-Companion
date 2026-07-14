"""Enhanced exception handling for validation errors.

Provides consistent, user-friendly error responses across all endpoints.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ValidationErrorHandler:
    """Centralized validation error handling."""

    @staticmethod
    def format_pydantic_error(error: ValidationError) -> dict[str, Any]:
        """Format Pydantic validation errors into user-friendly messages.

        Args:
            error: Pydantic ValidationError

        Returns:
            Dict containing formatted error response
        """
        formatted_errors = []

        for err in error.errors():
            field_path = " -> ".join(str(loc) for loc in err["loc"])

            # Map common error types to user-friendly messages
            error_type = err["type"]
            error_msg = err["msg"]

            user_friendly_msg = (
                ValidationErrorHandler._get_user_friendly_message(
                    error_type, error_msg, field_path
                )
            )

            formatted_errors.append(
                {
                    "field": field_path,
                    "message": user_friendly_msg,
                    "error_type": error_type,
                    "invalid_value": err.get("input"),
                }
            )

        return {
            "success": False,
            "error_type": "validation_error",
            "message": "Please correct the following errors and try again:",
            "errors": formatted_errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _get_user_friendly_message(
        error_type: str, original_msg: str, field: str
    ) -> str:
        """Convert Pydantic error messages to user-friendly ones."""
        # Field-specific customizations
        field_lower = field.lower()

        # Common error type mappings
        error_mappings = {
            "missing": "This field is required",
            "string_too_short": "This field is too short",
            "string_too_long": "This field is too long",
            # Use the custom message from our validators
            "value_error": original_msg,
            "type_error": "Invalid format for this field",
            "enum": "Please select a valid option",
        }

        # Field-specific customizations
        if "email" in field_lower:
            if error_type == "value_error" and "email" in original_msg.lower():
                return "Please enter a valid email address"
        elif "phone" in field_lower:
            if error_type == "value_error":
                return original_msg
        elif "password" in field_lower:
            if error_type == "value_error":
                return original_msg
        elif "title" in field_lower:
            if error_type == "string_too_short":
                return "Title must be at least 8 characters long"
        elif "description" in field_lower:
            if error_type == "string_too_short":
                return "Description must be at least 32 characters long"

        return error_mappings.get(error_type, original_msg)

    @staticmethod
    def create_error_response(
        message: str,
        errors: list[dict[str, Any]] | None = None,
        status_code: int = 422,
    ) -> JSONResponse:
        """Create standardized error response.

        Args:
            message: Main error message
            errors: List of detailed errors
            status_code: HTTP status code

        Returns:
            JSONResponse with standardized error format
        """
        response_data = {
            "success": False,
            "error_type": "validation_error",
            "message": message,
            "errors": errors or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return JSONResponse(status_code=status_code, content=response_data)


async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Global handler for Pydantic validation errors.

    Args:
        request: FastAPI request object
        exc: ValidationError exception

    Returns:
        JSONResponse with formatted error message
    """
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {exc}"
    )

    error_response = ValidationErrorHandler.format_pydantic_error(exc)

    return JSONResponse(status_code=422, content=error_response)


async def http_exception_handler_custom(
    request: Request, exc: HTTPException
) -> Response:
    """Enhanced HTTP exception handler with consistent error format.

    Args:
        request: FastAPI request object
        exc: HTTPException

    Returns:
        JSONResponse with standardized error format
    """
    # For validation-related HTTP exceptions, format consistently
    if exc.status_code == 422 or "validation" in str(exc.detail).lower():
        return ValidationErrorHandler.create_error_response(
            message=str(exc.detail), status_code=exc.status_code
        )

    # For other HTTP exceptions, use standard handler but with our format
    if exc.status_code >= 400:
        error_response = {
            "success": False,
            "error_type": "http_error",
            "message": str(exc.detail),
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return JSONResponse(status_code=exc.status_code, content=error_response)

    # Fall back to default handler for other cases
    return await http_exception_handler(request, exc)


class BusinessLogicError(Exception):
    """Custom exception for business logic validation errors."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        error_code: str | None = None,
    ):
        """Initialize the BusinessLogicError."""
        self.message = message
        self.field = field
        self.error_code = error_code
        super().__init__(message)


class ContentValidationError(BusinessLogicError):
    """Specific exception for content validation errors."""

    pass


class UserValidationError(BusinessLogicError):
    """Specific exception for user validation errors."""

    pass


class FileValidationError(BusinessLogicError):
    """Specific exception for file validation errors."""

    pass


async def business_logic_exception_handler(
    request: Request, exc: BusinessLogicError
) -> JSONResponse:
    """Handler for custom business logic exceptions.

    Args:
        request: FastAPI request object
        exc: BusinessLogicError exception

    Returns:
        JSONResponse with formatted error
    """
    logger.warning(
        f"Business logic error on {request.method} {request.url.path}: "
        f"{exc.message}"
    )

    errors = []
    if exc.field:
        errors.append(
            {
                "field": exc.field,
                "message": exc.message,
                "error_code": exc.error_code,
            }
        )

    return ValidationErrorHandler.create_error_response(
        message=exc.message, errors=errors, status_code=400
    )


def register_exception_handlers(app):
    """Register all custom exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler_custom)
    app.add_exception_handler(
        BusinessLogicError, business_logic_exception_handler
    )
    app.add_exception_handler(
        ContentValidationError, business_logic_exception_handler
    )
    app.add_exception_handler(
        UserValidationError, business_logic_exception_handler
    )
    app.add_exception_handler(
        FileValidationError, business_logic_exception_handler
    )

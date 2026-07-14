"""Tests for validation_exceptions module."""

from unittest.mock import MagicMock, Mock

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.validation_exceptions import (
    BusinessLogicError,
    ContentValidationError,
    FileValidationError,
    UserValidationError,
    ValidationErrorHandler,
    business_logic_exception_handler,
    http_exception_handler_custom,
    register_exception_handlers,
    validation_exception_handler,
)


class TestValidationErrorHandler:
    """Tests for ValidationErrorHandler class."""

    def test_format_pydantic_error_basic(self):
        """Test basic pydantic error formatting."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            email: str

        try:
            TestModel(email="invalid")
        except ValidationError as e:
            result = ValidationErrorHandler.format_pydantic_error(e)

            assert result["success"] is False
            assert result["error_type"] == "validation_error"
            assert "errors" in result
            assert "timestamp" in result

    def test_format_pydantic_error_multiple_errors(self):
        """Test formatting multiple pydantic errors."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            email: str

        try:
            TestModel(name="", email="")
        except ValidationError as e:
            result = ValidationErrorHandler.format_pydantic_error(e)

            assert len(result["errors"]) >= 1
            assert result["success"] is False
            assert result["error_type"] == "validation_error"
            assert "errors" in result
            assert "timestamp" in result

    def test_get_user_friendly_message_missing_field(self):
        """Test user-friendly message for missing field."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "missing", "Field required", "email"
        )

        assert result == "This field is required"

    def test_get_user_friendly_message_string_too_short(self):
        """Test user-friendly message for string too short."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "string_too_short",
            "String should have at least 8 characters",
            "name",
        )

        assert "short" in result.lower() or result == "This field is too short"

    def test_get_user_friendly_message_string_too_long(self):
        """Test user-friendly message for string too long."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "string_too_long",
            "String should have at most 100 characters",
            "description",
        )

        assert "long" in result.lower() or result == "This field is too long"

    def test_get_user_friendly_message_type_error(self):
        """Test user-friendly message for type error."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "type_error", "Input should be a valid string", "field"
        )

        assert "Invalid format" in result or "type" in result.lower()

    def test_get_user_friendly_message_enum(self):
        """Test user-friendly message for enum error."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "enum", "Input should be one of the allowed values", "gender"
        )

        assert "valid option" in result.lower()

    def test_get_user_friendly_message_email_field(self):
        """Test user-friendly message for email field errors."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "value_error", "Invalid email format", "email"
        )

        assert "email" in result.lower()

    def test_get_user_friendly_message_phone_field(self):
        """Test user-friendly message for phone field errors."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "value_error", "Phone number must start with 6-9", "phone"
        )

        assert "Phone" in result or "phone" in result.lower()

    def test_get_user_friendly_message_password_field(self):
        """Test user-friendly message for password field errors."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "value_error", "Password must be at least 8 characters", "password"
        )

        assert "Password" in result or "password" in result.lower()

    def test_get_user_friendly_message_title_field_short(self):
        """Test user-friendly message for title field too short."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "string_too_short", "Title too short", "title"
        )

        assert "Title" in result
        assert "8 characters" in result

    def test_get_user_friendly_message_description_field_short(self):
        """Test user-friendly message for description field too short."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "string_too_short", "Description too short", "description"
        )

        assert "Description" in result
        assert "32 characters" in result

    def test_get_user_friendly_message_unknown_type(self):
        """Test user-friendly message for unknown error type."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "unknown_type", "Some unknown error message", "field"
        )

        assert result == "Some unknown error message"

    def test_get_user_friendly_message_value_error(self):
        """Test user-friendly message for value_error type."""
        result = ValidationErrorHandler._get_user_friendly_message(
            "value_error", "Custom validation error", "field"
        )

        assert result == "Custom validation error"

    def test_create_error_response_basic(self):
        """Test creating basic error response."""
        result = ValidationErrorHandler.create_error_response(
            message="Validation failed"
        )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 422
        assert result.body is not None

    def test_create_error_response_with_errors(self):
        """Test creating error response with detailed errors."""
        errors = [{"field": "email", "message": "Invalid email"}]

        result = ValidationErrorHandler.create_error_response(
            message="Validation failed", errors=errors, status_code=400
        )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    def test_create_error_response_custom_status_code(self):
        """Test creating error response with custom status code."""
        result = ValidationErrorHandler.create_error_response(
            message="Not found", status_code=404
        )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 404

    def test_create_error_response_empty_errors(self):
        """Test creating error response with empty errors list."""
        result = ValidationErrorHandler.create_error_response(
            message="Error occurred"
        )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 422


class TestBusinessLogicErrors:
    """Tests for business logic error classes."""

    def test_business_logic_error_creation(self):
        """Test creating BusinessLogicError."""
        error = BusinessLogicError(
            message="Something went wrong",
            field="email",
            error_code="INVALID_EMAIL",
        )

        assert error.message == "Something went wrong"
        assert error.field == "email"
        assert error.error_code == "INVALID_EMAIL"
        assert str(error) == "Something went wrong"

    def test_business_logic_error_without_optional_fields(self):
        """Test creating BusinessLogicError without optional fields."""
        error = BusinessLogicError(message="Error occurred")

        assert error.message == "Error occurred"
        assert error.field is None
        assert error.error_code is None

    def test_content_validation_error(self):
        """Test ContentValidationError."""
        error = ContentValidationError(
            message="Invalid content",
            field="content",
            error_code="INVALID_CONTENT",
        )

        assert isinstance(error, BusinessLogicError)
        assert error.message == "Invalid content"

    def test_user_validation_error(self):
        """Test UserValidationError."""
        error = UserValidationError(
            message="Invalid user data", field="user", error_code="INVALID_USER"
        )

        assert isinstance(error, BusinessLogicError)
        assert error.message == "Invalid user data"

    def test_file_validation_error(self):
        """Test FileValidationError."""
        error = FileValidationError(
            message="Invalid file", field="file", error_code="INVALID_FILE"
        )

        assert isinstance(error, BusinessLogicError)
        assert error.message == "Invalid file"


class TestValidationExceptionHandler:
    """Tests for validation exception handler."""

    @pytest.mark.asyncio
    async def test_validation_exception_handler_basic(self):
        """Test basic validation exception handling."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/users"

        mock_validation_error = ValidationError.from_exception_data(
            "ValidationError",
            [
                {
                    "type": "missing",
                    "loc": ("email",),
                    "msg": "Field required",
                    "input": None,
                }
            ],
        )

        result = await validation_exception_handler(
            mock_request, mock_validation_error
        )

        assert isinstance(result, JSONResponse)
        assert result.status_code == 422


class TestHTTPExceptionHandler:
    """Tests for HTTP exception handler."""

    @pytest.mark.asyncio
    async def test_http_exception_handler_validation(self):
        """Test HTTP exception handler for validation errors."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/users"

        exc = HTTPException(status_code=422, detail="Validation error")

        result = await http_exception_handler_custom(mock_request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 422

    @pytest.mark.asyncio
    async def test_http_exception_handler_not_found(self):
        """Test HTTP exception handler for not found errors."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/api/users/123"

        exc = HTTPException(status_code=404, detail="User not found")

        result = await http_exception_handler_custom(mock_request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_http_exception_handler_unauthorized(self):
        """Test HTTP exception handler for unauthorized errors."""
        mock_request = Mock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/api/protected"

        exc = HTTPException(status_code=401, detail="Not authenticated")

        result = await http_exception_handler_custom(mock_request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 401

    @pytest.mark.asyncio
    async def test_http_exception_handler_validation_in_detail(self):
        """Test HTTP exception handler with validation in detail."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/users"

        exc = HTTPException(
            status_code=422, detail="Validation failed: email is invalid"
        )

        result = await http_exception_handler_custom(mock_request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 422


class TestBusinessLogicExceptionHandler:
    """Tests for business logic exception handler."""

    @pytest.mark.asyncio
    async def test_business_logic_exception_handler_basic(self):
        """Test basic business logic exception handling."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/content"

        exc = BusinessLogicError(
            message="Invalid content",
            field="content",
            error_code="INVALID_CONTENT",
        )

        result = await business_logic_exception_handler(mock_request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_business_logic_exception_handler_no_field(self):
        """Test business logic exception handling without field."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/content"

        exc = BusinessLogicError(message="General error")

        result = await business_logic_exception_handler(mock_request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_business_logic_exception_handler_content_error(self):
        """Test handling ContentValidationError."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/content"

        exc = ContentValidationError(
            message="Invalid content",
            field="content",
            error_code="INVALID_CONTENT",
        )

        result = await business_logic_exception_handler(mock_request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_business_logic_exception_handler_user_error(self):
        """Test handling UserValidationError."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/users"

        exc = UserValidationError(
            message="Invalid user", field="user", error_code="INVALID_USER"
        )

        result = await business_logic_exception_handler(mock_request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_business_logic_exception_handler_file_error(self):
        """Test handling FileValidationError."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/api/upload"

        exc = FileValidationError(
            message="Invalid file", field="file", error_code="INVALID_FILE"
        )

        result = await business_logic_exception_handler(mock_request, exc)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400


class TestRegisterExceptionHandlers:
    """Tests for register_exception_handlers function."""

    def test_register_exception_handlers(self):
        """Test registering exception handlers with FastAPI app."""
        mock_app = MagicMock()

        register_exception_handlers(mock_app)

        assert mock_app.add_exception_handler.call_count == 6

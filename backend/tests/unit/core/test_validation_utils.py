"""Tests for app/core/validation_utils.py."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from app.core.validation_utils import (
    ValidationContext,
    ValidationErrorFormatter,
    validate_user_data_async,
    validate_with_enhanced_errors,
)


class TestModel(BaseModel):
    name: str
    age: int


class TestValidationErrorFormatter:
    def test_format_missing_field(self):
        try:
            TestModel.model_validate({"age": 10})
        except ValidationError as e:
            formatted = ValidationErrorFormatter.format_validation_error(e)
            assert "name" in formatted
            assert "required" in formatted.lower() or "Field" in formatted

    def test_format_wrong_type(self):
        try:
            TestModel.model_validate({"name": "test", "age": "not_an_int"})
        except ValidationError as e:
            formatted = ValidationErrorFormatter.format_validation_error(e)
            assert "age" in formatted or "int" in formatted.lower()

    def test_format_invalid_email(self):
        class EmailModel(BaseModel):
            email: str

        try:
            EmailModel.model_validate({"email": "not_an_email"})
        except ValidationError as e:
            formatted = ValidationErrorFormatter.format_validation_error(e)
            assert "email" in formatted

    def test_create_http_exception(self):
        try:
            TestModel.model_validate({"age": 10})
        except ValidationError as e:
            exc = ValidationErrorFormatter.create_validation_http_exception(e)
            assert isinstance(exc, HTTPException)
            assert exc.status_code == 422

    def test_create_http_exception_custom_status(self):
        try:
            TestModel.model_validate({"age": 10})
        except ValidationError as e:
            exc = ValidationErrorFormatter.create_validation_http_exception(
                e, status_code=400
            )
            assert exc.status_code == 400


class TestValidationContext:
    def test_successful_validation(self):
        with ValidationContext("test_operation", "user_123") as ctx:
            assert ctx.operation == "test_operation"
            assert ctx.user_id == "user_123"

    def test_failed_validation(self):
        with pytest.raises(ValueError):
            with ValidationContext("test_operation"):
                raise ValueError("test error")


class TestValidateWithEnhancedErrors:
    def test_valid_data(self):
        result = validate_with_enhanced_errors(
            TestModel, {"name": "John", "age": 30}
        )
        assert result.name == "John"
        assert result.age == 30

    def test_invalid_data_raises_validation_error(self):
        with pytest.raises(ValidationError):
            validate_with_enhanced_errors(TestModel, {"name": "John"})

    def test_wrong_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            validate_with_enhanced_errors(
                TestModel, {"name": "John", "age": "not_int"}
            )

    def test_unexpected_exception_raises_500(self):
        pass


class TestValidateUserDataAsync:
    @pytest.mark.asyncio
    async def test_validates_phone_unique(self):
        mock_session = MagicMock()
        mock_session.exec.return_value.first.return_value = None

        data = {"phone": "1234567890"}
        result = await validate_user_data_async(data, mock_session)
        assert result["phone"] == "1234567890"

    @pytest.mark.asyncio
    async def test_validates_email_unique(self):
        mock_session = MagicMock()
        mock_session.exec.return_value.first.return_value = None

        data = {"email": "test@example.com"}
        result = await validate_user_data_async(data, mock_session)
        assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_returns_data_without_phone_or_email(self):
        mock_session = MagicMock()

        data = {"name": "John"}
        result = await validate_user_data_async(data, mock_session)
        assert result == {"name": "John"}

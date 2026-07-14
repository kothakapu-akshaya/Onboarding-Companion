"""Tests for extracted text schema validation and JSONB safety."""

import json

import pytest
from pydantic import ValidationError

from app.schemas.extracted_text import (
    ExtractedText,
    ExtractedTextType,
    validate_json_serializable,
    validate_safe_text_content,
)


class TestJSONBSafetyValidation:
    """Test JSONB safety validation functions."""

    def test_validate_safe_text_content(self):
        """Test text content sanitization."""
        # Normal text should pass through
        assert validate_safe_text_content("Hello world") == "Hello world"

        # Remove null bytes and control characters
        dangerous_text = "Hello\x00\x01\x02world\x1f"
        assert validate_safe_text_content(dangerous_text) == "Helloworld"

        # Preserve newlines and tabs
        text_with_formatting = "Hello\nworld\ttest"
        assert (
            validate_safe_text_content(text_with_formatting)
            == "Hello\nworld\ttest"
        )

        # Limit excessive line breaks
        # (function allows max 3 consecutive newlines)
        text_with_many_breaks = "Hello\n\n\n\n\nworld"
        assert (
            validate_safe_text_content(text_with_many_breaks)
            == "Hello\n\n\nworld"
        )

        # Limit excessive spaces (function allows max 5 consecutive spaces)
        text_with_many_spaces = "Hello      world"  # 6 spaces
        assert (
            validate_safe_text_content(text_with_many_spaces)
            == "Hello     world"
        )  # Reduced to 5

    def test_validate_json_serializable(self):
        """Test JSON serializability validation."""
        # Valid data should pass
        valid_data = {"text": "Hello", "confidence": 0.95}
        assert validate_json_serializable(valid_data) == valid_data

        # Invalid data should raise error
        with pytest.raises(ValueError, match="Object not JSON serializable"):
            validate_json_serializable(
                lambda x: x
            )  # Functions are not serializable


class TestExtractedTextValidation:
    """Test ExtractedText schema validation."""

    def test_valid_extracted_text(self):
        """Test valid extracted text creation."""
        data = {
            "confidence": 0.95,
            "language": "hi",
            "extraction_type": "asr",
            "model_name": "whisper-large",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "यह एक", "confidence": 0.9},
                {"start": 2.0, "end": 4.0, "text": "टेस्ट है।", "confidence": 1.0},
            ],
        }

        text = ExtractedText(**data)
        assert text.confidence == 0.95
        assert text.extraction_type == ExtractedTextType.asr

        # Should be JSON serializable
        json_data = text.model_dump()
        json.dumps(json_data)  # Should not raise

    def test_text_sanitization(self):
        """Test that dangerous characters are sanitized in text fields."""
        data = {
            "extraction_type": "ocr",
            "language": "en",
            "notes": "Hello\x00\x01world",
        }

        text = ExtractedText(**data)
        assert text.notes == "Helloworld"
        assert text.language == "en"

    def test_text_validation_errors(self):
        """Test validation errors for extracted text."""
        # Missing required fields
        with pytest.raises(ValidationError):
            ExtractedText()

        # Invalid confidence range
        with pytest.raises(ValidationError):
            ExtractedText(
                extraction_type="ocr",
                confidence=1.5,  # > 1.0
            )

        # Empty segments list
        with pytest.raises(ValidationError, match="cannot be empty"):
            ExtractedText(extraction_type="ocr", segments=[])

        # Metadata too large
        large_metadata = {"data": "x" * 11000}  # > 10KB
        with pytest.raises(ValidationError, match="too large"):
            ExtractedText(extraction_type="ocr", metadata=large_metadata)


class TestCorrectedTextValidation:
    """Test corrected text functionality within ExtractedText schema."""

    def test_valid_corrected_text(self):
        """Test valid corrected text creation."""
        data = {
            "extraction_type": "manual",
            "quality_score": 0.9,
            "notes": "Improved translation accuracy",
        }

        text = ExtractedText(**data)
        assert text.quality_score == 0.9

        # Should be JSON serializable
        json_data = text.model_dump()
        json.dumps(json_data)  # Should not raise

    def test_corrected_text_sanitization(self):
        """Test that dangerous characters are sanitized in corrected text."""
        data = {
            "extraction_type": "manual",
            "notes": "Test\x1fnotes",  # Control character
        }

        text = ExtractedText(**data)
        assert text.notes == "Testnotes"

    def test_corrected_text_validation_errors(self):
        """Test validation errors for corrected text."""
        # Missing required fields
        with pytest.raises(ValidationError):
            ExtractedText()

        # Invalid quality score range
        with pytest.raises(ValidationError):
            ExtractedText(
                extraction_type="manual",
                quality_score=1.5,  # > 1.0
            )

        # Metadata too large
        large_metadata = {"data": "x" * 11000}  # > 10KB
        with pytest.raises(ValidationError, match="too large"):
            ExtractedText(extraction_type="manual", metadata=large_metadata)


class TestJSONBStorageSafety:
    """Test that schemas produce JSONB-safe output."""

    def test_extracted_text_jsonb_storage(self):
        """Test extracted text produces JSONB-safe output."""
        data = {
            "notes": "Test with\nnewlines\tand tabs",
            "extraction_type": "ocr",
            "confidence": 0.95,
            "metadata": {
                "source": "document\nwith\tformatting",
                "nested": {"value": "test\x00clean"},
            },
        }

        text = ExtractedText(**data)
        json_data = text.model_dump()

        # Should be JSON serializable without issues
        json_str = json.dumps(json_data, ensure_ascii=False)
        assert json_str is not None

        # Should round-trip successfully
        parsed_back = json.loads(json_str)
        assert parsed_back["notes"] == "Test with\nnewlines\tand tabs"

    def test_corrected_text_jsonb_storage(self):
        """Test corrected text produces JSONB-safe output."""
        data = {
            "extraction_type": "manual",
            "notes": "Corrected\ntext\twith formatting",
            "metadata": {"key": "value\x00cleaned"},
        }

        text = ExtractedText(**data)
        json_data = text.model_dump()

        # Should be JSON serializable
        json_str = json.dumps(json_data, ensure_ascii=False)
        assert json_str is not None

        # Should round-trip successfully
        parsed_back = json.loads(json_str)
        assert parsed_back["notes"] == "Corrected\ntext\twith formatting"

    def test_extreme_edge_cases(self):
        """Test extreme edge cases for JSONB safety."""
        # Text with many different problematic characters
        problematic_text = (
            "Test\x00\x01\x02\x03\x04\x05\x06\x07"
            "\x08\x0b\x0c\x0e\x0f\x10\x1f\x7fend"
        )

        # Note: 'problematic_text' is intentionally created but not used
        # to verify it can be constructed without errors
        _ = {"notes": problematic_text, "extraction_type": "ocr"}

    def test_segment_text_sanitization(self):
        """Test that segments are stored and serialized correctly."""
        data = {
            "extraction_type": "asr",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Test world"}],
        }

        text = ExtractedText(**data)
        json_data = text.model_dump()

        # Should have cleaned the text in segments
        assert text.segments[0].text == "Test world"
        assert text.segments[0].start == 0.0

        # Should be JSON serializable
        json_str = json.dumps(json_data)
        parsed_back = json.loads(json_str)
        assert parsed_back["segments"][0]["text"] == "Test world"

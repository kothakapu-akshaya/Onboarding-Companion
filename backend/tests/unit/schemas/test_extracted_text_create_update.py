"""Tests for ExtractedTextCreate and ExtractedTextUpdate schemas."""

import json

import pytest
from pydantic import ValidationError

from app.schemas.extracted_text import (
    ExtractedTextCreate,
    ExtractedTextType,
    ExtractedTextUpdate,
)


class TestExtractedTextCreate:
    """Test ExtractedTextCreate schema (POST)."""

    def test_valid_create(self):
        """Test valid ExtractedTextCreate with all required fields."""
        data = {
            "extraction_type": "asr",
            "language": "te",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Hello", "proofread": False},
            ],
            "model_name": "test-model",
            "confidence": 0.95,
        }
        text = ExtractedTextCreate(**data)
        assert text.extraction_type == ExtractedTextType.asr
        assert text.language == "te"
        assert len(text.segments) == 1
        assert text.model_name == "test-model"

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            ExtractedTextCreate(extraction_type="asr")
        errors = {e["loc"][0] for e in exc.value.errors()}
        assert "language" in errors
        assert "segments" in errors
        assert "model_name" in errors

    def test_inherits_confidence_validation(self):
        """Test that confidence validation is inherited."""
        with pytest.raises(ValidationError):
            ExtractedTextCreate(
                extraction_type="asr",
                language="te",
                segments=[{"text": "hello", "start": 0, "end": 1}],
                model_name="test",
                confidence=1.5,
            )

    def test_empty_segments_rejected(self):
        """Test that empty segments list is rejected."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ExtractedTextCreate(
                extraction_type="asr",
                language="te",
                segments=[],
                model_name="test",
            )

    def test_invalid_language_code(self):
        """Test that invalid language code is rejected."""
        with pytest.raises(ValidationError):
            ExtractedTextCreate(
                extraction_type="asr",
                language="invalid_long_code",
                segments=[{"text": "hello", "start": 0, "end": 1}],
                model_name="test",
            )

    def test_json_serializable_output(self):
        """Test that model output is JSON serializable."""
        data = {
            "extraction_type": "asr",
            "language": "en",
            "segments": [{"text": "test", "start": 0.0, "end": 1.0}],
            "model_name": "m",
        }
        text = ExtractedTextCreate(**data)
        json.dumps(text.model_dump())

    def test_metadata_added_by_validator(self):
        """Test that metadata is added by validator."""
        data = {
            "extraction_type": "manual",
            "language": "en",
            "segments": [{"text": "hello", "start": 0, "end": 1}],
            "model_name": "m",
        }
        text = ExtractedTextCreate(**data)
        assert text.metadata is not None
        assert "validation_timestamp" in text.metadata

    def test_metrics_fields_rejected(self):
        """Test that server-managed metric fields are rejected on create."""
        with pytest.raises(
            ValidationError,
            match="Extra inputs are not permitted",
        ):
            ExtractedTextCreate(
                extraction_type="manual",
                language="en",
                segments=[{"text": "hello", "start": 0, "end": 1}],
                model_name="m",
                word_count=5,
            )


class TestExtractedTextUpdate:
    """Test ExtractedTextUpdate schema (PATCH)."""

    def test_partial_update_one_field(self):
        """Test partial update with a single field."""
        text = ExtractedTextUpdate(extraction_type="manual")
        assert text.extraction_type == ExtractedTextType.manual

    def test_empty_body_rejected(self):
        """Test that empty body is rejected."""
        with pytest.raises(
            ValidationError, match="At least one field must be provided"
        ):
            ExtractedTextUpdate()

    def test_segments_without_extraction_type_rejected(self):
        """Test that segments without extraction_type are rejected."""
        with pytest.raises(
            ValidationError,
            match="extraction_type is required when segments are provided",
        ):
            ExtractedTextUpdate(
                segments=[{"text": "hello", "start": 0, "end": 1}]
            )

    def test_segments_with_extraction_type_ok(self):
        """Test that segments with extraction_type are accepted."""
        text = ExtractedTextUpdate(
            extraction_type="asr",
            segments=[{"text": "hello", "start": 0, "end": 1}],
        )
        assert len(text.segments) == 1

    def test_language_optional(self):
        """Test that language field is optional."""
        text = ExtractedTextUpdate(language="hi")
        assert text.language == "hi"

    def test_confidence_validated(self):
        """Test that confidence is validated on update."""
        with pytest.raises(ValidationError):
            ExtractedTextUpdate(confidence=1.5)

    def test_empty_segments_rejected(self):
        """Test that empty segments list is rejected on update."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ExtractedTextUpdate(extraction_type="ocr", segments=[])

    def test_json_serializable_output(self):
        """Test that update model output is JSON serializable."""
        text = ExtractedTextUpdate(notes="hello", extraction_type="manual")
        json.dumps(text.model_dump())

    def test_inherits_metadata_validation(self):
        """Test that metadata size validation is inherited on update."""
        with pytest.raises(ValidationError, match="too large"):
            ExtractedTextUpdate(
                extraction_type="manual",
                metadata={"data": "x" * 11000},
            )

    def test_ocr_segments_without_ocr_fields_ok(self):
        """Test OCR update segments without OCR-specific fields."""
        text = ExtractedTextUpdate(
            extraction_type="ocr",
            segments=[{"text": "hello"}],
        )
        assert len(text.segments) == 1
        assert text.segments[0].text == "hello"

    def test_update_language_format(self):
        """Test that invalid language format is rejected on update."""
        with pytest.raises(ValidationError):
            ExtractedTextUpdate(language="invalid_toolong")

    def test_metrics_fields_rejected(self):
        """Test that server-managed metric fields are rejected on update."""
        with pytest.raises(
            ValidationError,
            match="Extra inputs are not permitted",
        ):
            ExtractedTextUpdate(
                extraction_type="manual",
                character_count=42,
            )

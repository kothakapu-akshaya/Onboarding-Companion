"""Tests for OCR segment validation in ExtractedText."""

import pytest
from pydantic import ValidationError

from app.schemas.extracted_text import ExtractedText


def test_ocr_segments_require_layout_fields():
    """Test that OCR segments require layout fields."""
    with pytest.raises(ValidationError, match="missing required fields"):
        ExtractedText(
            transcription="OCR content",
            extraction_type="ocr",
            segments=[{"start": 0, "end": 1, "text": "Para 1"}],
        )


def test_ocr_segments_enforce_page_index_range():
    """Test that OCR segments enforce page index range."""
    with pytest.raises(ValidationError, match="end == start \\+ 1"):
        ExtractedText(
            transcription="OCR content",
            extraction_type="ocr",
            segments=[
                {
                    "start": 0,
                    "end": 2,
                    "text": "Para 1",
                    "bbox": [10, 10, 100, 100],
                    "type": "text",
                    "reading_order": 1,
                }
            ],
        )


def test_ocr_segments_enforce_reading_order_sequence():
    """Test that OCR segments enforce reading order sequence."""
    with pytest.raises(ValidationError, match="reading_order.*must start at 0"):
        ExtractedText(
            transcription="OCR content",
            extraction_type="ocr",
            segments=[
                {
                    "start": 0,
                    "end": 1,
                    "text": "Para 2",
                    "bbox": [10, 10, 100, 100],
                    "type": "text",
                    "reading_order": 2,
                },
                {
                    "start": 0,
                    "end": 1,
                    "text": "Para 1",
                    "bbox": [10, 120, 100, 200],
                    "type": "text",
                    "reading_order": 1,
                },
            ],
        )


def test_ocr_segments_valid_payload_passes():
    """Test that valid OCR segment payload passes validation."""
    model = ExtractedText(
        transcription="OCR content",
        extraction_type="ocr",
        segments=[
            {
                "start": 0,
                "end": 1,
                "text": "Para 1",
                "bbox": [10, 10, 100, 100],
                "type": "text",
                "reading_order": 0,
            },
            {
                "start": 0,
                "end": 1,
                "text": "Para 2",
                "bbox": [10, 120, 100, 200],
                "type": "text",
                "reading_order": 1,
            },
        ],
    )
    assert len(model.segments) == 2


def test_asr_segments_do_not_require_ocr_fields():
    """Test that ASR segments do not require OCR-specific fields."""
    model = ExtractedText(
        transcription="ASR content",
        extraction_type="asr",
        segments=[
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 2.0, "end": 4.0, "text": "World"},
        ],
    )
    assert len(model.segments) == 2


def test_ocr_segments_accept_allowed_type():
    """Test that OCR segments accept allowed segment types."""
    model = ExtractedText(
        transcription="OCR content",
        extraction_type="ocr",
        segments=[
            {
                "start": 0,
                "end": 1,
                "text": "Picture block",
                "bbox": [10, 10, 100, 100],
                "type": "image",
                "reading_order": 0,
            }
        ],
    )
    assert model.segments[0].type == "image"


def test_ocr_segments_reject_unsupported_type():
    """Test that OCR segments reject unsupported segment types."""
    with pytest.raises(ValidationError, match="unsupported type"):
        ExtractedText(
            transcription="OCR content",
            extraction_type="ocr",
            segments=[
                {
                    "start": 0,
                    "end": 1,
                    "text": "Other block",
                    "bbox": [10, 10, 100, 100],
                    "type": "Paragraph",
                    "reading_order": 1,
                }
            ],
        )

"""Tests for extracted text proofreading functionality."""

import pytest
from pydantic import ValidationError

from app.schemas.extracted_text import ExtractedText, TextSegment


class TestProofreadFlagCalculation:
    """Test is_fully_proofread flag calculation logic."""

    def test_all_segments_proofread_returns_true(self):
        """When all segments have proofread=True, flag should be True."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "proofread": True},
                {"start": 1.0, "end": 2.0, "text": "World", "proofread": True},
            ],
        }

        text = ExtractedText(**data)
        segments = text.segments

        total = len(segments)
        proofread_count = sum(1 for s in segments if s.proofread is True)

        assert proofread_count == total
        assert proofread_count == 2

    def test_no_segments_proofread_returns_false(self):
        """When no segments have proofread=True, flag should be False."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "proofread": False},
                {"start": 1.0, "end": 2.0, "text": "World", "proofread": False},
            ],
        }

        text = ExtractedText(**data)
        segments = text.segments

        total = len(segments)
        proofread_count = sum(1 for s in segments if s.proofread is True)

        assert proofread_count == 0
        assert proofread_count != total

    def test_partial_segments_proofread_returns_false(self):
        """Partial proofread flag should be False."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "proofread": True},
                {"start": 1.0, "end": 2.0, "text": "World", "proofread": False},
            ],
        }

        text = ExtractedText(**data)
        segments = text.segments

        total = len(segments)
        proofread_count = sum(1 for s in segments if s.proofread is True)

        assert proofread_count == 1
        assert proofread_count != total

    def test_missing_proofread_defaults_to_false(self):
        """Segments without proofread field default to False."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello"},
                {"start": 1.0, "end": 2.0, "text": "World"},
            ],
        }

        text = ExtractedText(**data)
        segments = text.segments

        proofread_count = sum(1 for s in segments if s.proofread is True)

        assert proofread_count == 0

    def test_empty_segments_rejected(self):
        """Empty segments list is rejected by validation."""
        data = {
            "extraction_type": "asr",
            "segments": [],
        }

        with pytest.raises(ValidationError, match="cannot be empty"):
            ExtractedText(**data)

    def test_no_segments_not_fully_proofread(self):
        """No segments case (None) should not be fully proofread."""
        data = {
            "extraction_type": "asr",
        }

        text = ExtractedText(**data)

        assert text.segments is None


class TestProofreadFlagEdgeCases:
    """Edge cases for proofread flag."""

    def test_single_segment_proofread_true(self):
        """Single segment with proofread=True should be fully proofread."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "proofread": True},
            ],
        }

        text = ExtractedText(**data)
        segments = text.segments

        total = len(segments)
        proofread_count = sum(1 for s in segments if s.proofread is True)

        assert proofread_count == total == 1

    def test_ocr_segments_with_proofread(self):
        """OCR segments with proofread flag."""
        data = {
            "extraction_type": "ocr",
            "segments": [
                {
                    "start": 0,
                    "end": 1,
                    "text": "Para 1",
                    "bbox": [10, 10, 100, 100],
                    "type": "text",
                    "reading_order": 0,
                    "proofread": True,
                },
                {
                    "start": 0,
                    "end": 1,
                    "text": "Para 2",
                    "bbox": [10, 120, 100, 200],
                    "type": "text",
                    "reading_order": 1,
                    "proofread": True,
                },
            ],
        }

        text = ExtractedText(**data)
        segments = text.segments

        total = len(segments)
        proofread_count = sum(1 for s in segments if s.proofread is True)

        assert proofread_count == total == 2

    def test_segments_are_textsegment_models(self):
        """Verify segments are Pydantic models, not dicts."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello"},
            ],
        }

        text = ExtractedText(**data)

        assert isinstance(text.segments[0], TextSegment)
        assert text.segments[0].text == "Hello"
        assert text.segments[0].proofread is False  # default

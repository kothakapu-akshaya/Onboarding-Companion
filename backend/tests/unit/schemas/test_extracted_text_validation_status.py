"""Tests for extracted text validation status tracking."""

from app.schemas.extracted_text import ExtractedText, TextSegment


class TestValidationFlagDefaults:
    """Test validated field defaults on segment creation."""

    def test_validated_defaults_to_false(self):
        """Segments without validated field default to False."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello"},
            ],
        }

        text = ExtractedText(**data)
        segment = text.segments[0]

        assert segment.validated is False

    def test_validated_explicitly_false(self):
        """Explicit validated=False is accepted."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "validated": False},
            ],
        }

        text = ExtractedText(**data)
        segment = text.segments[0]

        assert segment.validated is False

    def test_validated_explicitly_true(self):
        """Explicit validated=True is accepted."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "validated": True},
            ],
        }

        text = ExtractedText(**data)
        segment = text.segments[0]

        assert segment.validated is True

    def test_proofread_and_validated_independent(self):
        """Proofread and validated can be set independently."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {
                    "start": 0.0,
                    "end": 1.0,
                    "text": "Hello",
                    "proofread": True,
                    "validated": False,
                },
            ],
        }

        text = ExtractedText(**data)
        segment = text.segments[0]

        assert segment.proofread is True
        assert segment.validated is False


class TestValidationFlagAllSegments:
    """Test that validated flag works across multiple segments."""

    def test_all_segments_validated(self):
        """When all segments have validated=True."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "validated": True},
                {"start": 1.0, "end": 2.0, "text": "World", "validated": True},
            ],
        }

        text = ExtractedText(**data)
        validated_count = sum(1 for s in text.segments if s.validated is True)

        assert validated_count == 2

    def test_partial_segments_validated(self):
        """When some segments are validated and some are not."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "validated": True},
                {"start": 1.0, "end": 2.0, "text": "World", "validated": False},
            ],
        }

        text = ExtractedText(**data)
        validated_count = sum(1 for s in text.segments if s.validated is True)

        assert validated_count == 1

    def test_no_segments_validated(self):
        """When no segments have validated=True."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello", "validated": False},
                {"start": 1.0, "end": 2.0, "text": "World", "validated": False},
            ],
        }

        text = ExtractedText(**data)
        validated_count = sum(1 for s in text.segments if s.validated is True)

        assert validated_count == 0

    def test_segments_are_textsegment_models(self):
        """Verify segments are Pydantic models with validated attribute."""
        data = {
            "extraction_type": "asr",
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello"},
            ],
        }

        text = ExtractedText(**data)

        assert isinstance(text.segments[0], TextSegment)
        assert text.segments[0].validated is False

    def test_ocr_segments_with_validated(self):
        """OCR segments with validated flag."""
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
                    "validated": True,
                },
                {
                    "start": 0,
                    "end": 1,
                    "text": "Para 2",
                    "bbox": [10, 120, 100, 200],
                    "type": "text",
                    "reading_order": 1,
                    "validated": True,
                },
            ],
        }

        text = ExtractedText(**data)
        validated_count = sum(1 for s in text.segments if s.validated is True)

        assert validated_count == 2

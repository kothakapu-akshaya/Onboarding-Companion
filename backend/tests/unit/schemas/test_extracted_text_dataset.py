"""Tests for dataset field and story-level metadata in ExtractedText schema."""

import json

import pytest
from pydantic import ValidationError

from app.schemas.extracted_text import (
    ExtractedText,
    ExtractedTextCreate,
    ExtractedTextUpdate,
    TextSegment,
)


class TestTextSegmentStoryFields:
    """Test TextSegment story-level fields."""

    def test_segment_with_named_entities(self):
        """Test segment accepts grouped named_entities dict."""
        seg = TextSegment(
            text="Story content",
            named_entities={
                "characters": ["రాముడు", "సీత"],
                "locations": ["అడవి"],
                "keywords": ["సాహసం", "ప్రేమ"],
            },
        )
        assert seg.named_entities["characters"] == ["రాముడు", "సీత"]
        assert seg.named_entities["locations"] == ["అడవి"]

    def test_segment_with_extraction_metadata(self):
        """Test segment accepts extraction_metadata dict."""
        seg = TextSegment(
            text="Story content",
            extraction_metadata={
                "title": "నక్క బావ",
                "author": "చందమామ బృందం",
                "genre": "నీతికథ",
                "moral": "అతి ఆశతో చేసే మోసాలు...",
            },
        )
        assert seg.extraction_metadata["title"] == "నక్క బావ"
        assert seg.extraction_metadata["author"] == "చందమామ బృందం"

    def test_segment_without_story_fields(self):
        """Test segment works without optional story fields."""
        seg = TextSegment(text="Hello world")
        assert seg.named_entities is None
        assert seg.extraction_metadata is None

    def test_segment_with_both_dict_fields(self):
        """Test segment accepts both new dict fields simultaneously."""
        seg = TextSegment(
            text="Content",
            start=1.0,
            end=3.0,
            named_entities={"characters": ["A"], "locations": ["B"]},
            extraction_metadata={"title": "Test", "author": "Author"},
        )
        assert seg.named_entities["characters"] == ["A"]
        assert seg.extraction_metadata["title"] == "Test"

    def test_segment_jsonb_serializable(self):
        """Test segment with story fields serializes to JSON."""
        seg = TextSegment(
            text="Content",
            named_entities={"characters": ["A"]},
            extraction_metadata={"title": "T"},
        )
        d = seg.model_dump()
        json.dumps(d)
        assert d["named_entities"]["characters"] == ["A"]
        assert d["extraction_metadata"]["title"] == "T"

    def test_segment_named_entities_accepts_dict_values(self):
        """Test named_entities accepts dict values with roles."""
        seg = TextSegment(
            text="Story",
            named_entities={
                "characters": {
                    "రాముడు": "hero",
                    "సీత": "heroine",
                    "హనుమంతుడు": None,
                },
                "locations": {"అడవి": "setting", "సముద్రం": None},
            },
        )
        assert seg.named_entities["characters"] == {
            "రాముడు": "hero",
            "సీత": "heroine",
            "హనుమంతుడు": None,
        }
        assert seg.named_entities["locations"] == {
            "అడవి": "setting",
            "సముద్రం": None,
        }

    def test_segment_named_entities_mixed_list_and_dict(self):
        """Test named_entities accepts mixed list and dict values per field."""
        seg = TextSegment(
            text="Story",
            named_entities={
                "characters": {"రాముడు": "hero", "సీత": "heroine"},
                "keywords": ["సాహసం", "ప్రేమ"],
            },
        )
        assert seg.named_entities["characters"] == {
            "రాముడు": "hero",
            "సీత": "heroine",
        }
        assert seg.named_entities["keywords"] == ["సాహసం", "ప్రేమ"]

    def test_segment_named_entities_dict_serializable(self):
        """Test dict-format named_entities serializes to JSON."""
        seg = TextSegment(
            text="Content",
            named_entities={"characters": {"A": "hero", "B": None}},
        )
        d = seg.model_dump()
        json.dumps(d)
        assert d["named_entities"]["characters"] == {"A": "hero", "B": None}

    def test_segment_named_entities_rejects_invalid_type(self):
        """Test named_entities rejects invalid inner value types."""
        with pytest.raises(ValidationError):
            TextSegment(
                text="Content",
                named_entities={"characters": 123},
            )
        with pytest.raises(ValidationError):
            TextSegment(
                text="Content",
                named_entities={"characters": [1, 2, 3]},
            )


class TestExtractedTextDatasetField:
    """Test ExtractedText dataset field."""

    def test_dataset_default_none(self):
        """Test dataset defaults to None."""
        et = ExtractedText(extraction_type="manual")
        assert et.dataset is None

    def test_dataset_set_to_story(self):
        """Test dataset accepts 'story' value."""
        et = ExtractedText(
            extraction_type="manual",
            dataset="story",
            segments=[
                {
                    "text": "C",
                    "extraction_metadata": {"title": "T", "category": "story"},
                }
            ],
        )
        assert et.dataset == "story"

    def test_dataset_set_to_arbitrary(self):
        """Test dataset accepts any string value."""
        et = ExtractedText(
            extraction_type="manual",
            dataset="ocr_article",
            metadata={"category": "article"},
        )
        assert et.dataset == "ocr_article"

    def test_dataset_jsonb_serializable(self):
        """Test dataset is included in JSON output."""
        et = ExtractedText(extraction_type="manual", dataset="story")
        d = et.model_dump()
        json.dumps(d)
        assert d["dataset"] == "story"


class TestStoryWithManualExtraction:
    """Test dataset='story' with extraction_type='manual'."""

    def test_valid_story_manual(self):
        """Test valid story with manual extraction passes."""
        et = ExtractedText(
            extraction_type="manual",
            dataset="story",
            segments=[
                {
                    "text": "Story content here",
                    "extraction_metadata": {
                        "title": "కథ పేరు",
                        "author": "రచయిత",
                        "category": "story",
                    },
                    "named_entities": {
                        "characters": ["హీరో"],
                        "locations": ["ఊరు"],
                    },
                }
            ],
        )
        assert et.dataset == "story"
        assert et.segments[0].extraction_metadata["title"] == "కథ పేరు"
        assert et.segments[0].named_entities["characters"] == ["హీరో"]

    def test_story_manual_missing_extraction_metadata(self):
        """Test story without extraction_metadata raises error."""
        msg = "extraction_metadata required"
        with pytest.raises(ValidationError, match=msg):
            ExtractedText(
                extraction_type="manual",
                dataset="story",
                segments=[{"text": "Content without metadata"}],
            )

    def test_story_manual_missing_title(self):
        """Test story missing title in extraction_metadata."""
        with pytest.raises(ValidationError, match="extraction_metadata.title"):
            ExtractedText(
                extraction_type="manual",
                dataset="story",
                segments=[
                    {
                        "text": "Content",
                        "extraction_metadata": {"author": "Someone"},
                    }
                ],
            )

    def test_story_manual_multiple_segments(self):
        """Test story with multiple segments."""
        et = ExtractedText(
            extraction_type="manual",
            dataset="story",
            segments=[
                {
                    "start": 1,
                    "end": 3,
                    "text": "First story",
                    "extraction_metadata": {
                        "title": "Story 1",
                        "category": "story",
                    },
                },
                {
                    "start": 4,
                    "end": 6,
                    "text": "Second story",
                    "extraction_metadata": {
                        "title": "Story 2",
                        "category": "story",
                    },
                },
            ],
        )
        assert len(et.segments) == 2
        assert et.segments[1].extraction_metadata["title"] == "Story 2"


class TestStoryWithOCRExtraction:
    """Test dataset='story' with extraction_type='ocr' (relaxed validation)."""

    def test_valid_story_ocr(self):
        """Test valid story+ocr: only end==start+1 enforced."""
        et = ExtractedText(
            extraction_type="ocr",
            dataset="story",
            segments=[
                {
                    "start": 0,
                    "end": 1,
                    "text": "Page 1 content",
                    "extraction_metadata": {
                        "title": "Chapter 1",
                        "category": "story",
                    },
                },
                {
                    "start": 1,
                    "end": 2,
                    "text": "Page 2 content",
                    "extraction_metadata": {
                        "title": "Chapter 1",
                        "category": "story",
                    },
                },
            ],
        )
        assert len(et.segments) == 2

    def test_story_ocr_does_not_require_bbox(self):
        """Test story+ocr does not require bbox field."""
        et = ExtractedText(
            extraction_type="ocr",
            dataset="story",
            segments=[
                {
                    "start": 0,
                    "end": 1,
                    "text": "Page content",
                    "extraction_metadata": {
                        "title": "A Story",
                        "category": "story",
                    },
                }
            ],
        )
        assert et.segments[0].bbox is None

    def test_story_ocr_does_not_require_type(self):
        """Test story+ocr does not require type field."""
        et = ExtractedText(
            extraction_type="ocr",
            dataset="story",
            segments=[
                {
                    "start": 0,
                    "end": 1,
                    "text": "Content",
                    "extraction_metadata": {"title": "T", "category": "story"},
                }
            ],
        )
        assert et.segments[0].type is None

    def test_story_ocr_does_not_require_reading_order(self):
        """Test story+ocr does not require reading_order field."""
        et = ExtractedText(
            extraction_type="ocr",
            dataset="story",
            segments=[
                {
                    "start": 0,
                    "end": 1,
                    "text": "Content",
                    "extraction_metadata": {"title": "T", "category": "story"},
                }
            ],
        )
        assert et.segments[0].reading_order is None

    def test_story_ocr_enforces_end_greater_than_start(self):
        """Test story+ocr enforces end > start."""
        with pytest.raises(ValidationError, match="greater than start"):
            ExtractedText(
                extraction_type="ocr",
                dataset="story",
                segments=[
                    {
                        "start": 3,
                        "end": 3,
                        "text": "End equals start",
                        "extraction_metadata": {"title": "T"},
                    }
                ],
            )

    def test_story_ocr_still_requires_extraction_metadata(self):
        """Test story+ocr still requires extraction_metadata."""
        msg = "extraction_metadata required"
        with pytest.raises(ValidationError, match=msg):
            ExtractedText(
                extraction_type="ocr",
                dataset="story",
                segments=[{"start": 0, "end": 1, "text": "No metadata"}],
            )

    def test_story_ocr_still_requires_title(self):
        """Test story+ocr still requires title."""
        with pytest.raises(ValidationError, match="extraction_metadata.title"):
            ExtractedText(
                extraction_type="ocr",
                dataset="story",
                segments=[
                    {
                        "start": 0,
                        "end": 1,
                        "text": "No title",
                        "extraction_metadata": {"author": "Someone"},
                    }
                ],
            )


class TestRegularOCRStillStrict:
    """Test regular OCR still requires full fields."""

    def test_regular_ocr_requires_bbox(self):
        """Test regular OCR still requires bbox."""
        with pytest.raises(ValidationError, match="missing required fields"):
            ExtractedText(
                extraction_type="ocr",
                segments=[
                    {
                        "start": 0,
                        "end": 1,
                        "text": "No bbox",
                        "type": "text",
                        "reading_order": 0,
                    }
                ],
            )

    def test_regular_ocr_requires_type(self):
        """Test regular OCR still requires type."""
        with pytest.raises(ValidationError, match="missing required fields"):
            ExtractedText(
                extraction_type="ocr",
                segments=[
                    {
                        "start": 0,
                        "end": 1,
                        "text": "No type",
                        "bbox": [0, 0, 10, 10],
                        "reading_order": 0,
                    }
                ],
            )

    def test_regular_ocr_requires_reading_order(self):
        """Test regular OCR still requires reading_order."""
        with pytest.raises(ValidationError, match="missing required fields"):
            ExtractedText(
                extraction_type="ocr",
                segments=[
                    {
                        "start": 0,
                        "end": 1,
                        "text": "No reading order",
                        "bbox": [0, 0, 10, 10],
                        "type": "text",
                    }
                ],
            )

    def test_regular_ocr_still_enforces_end_equals_start_plus_one(self):
        """Test regular OCR still enforces end == start + 1."""
        with pytest.raises(ValidationError, match="end == start \\+ 1"):
            ExtractedText(
                extraction_type="ocr",
                segments=[
                    {
                        "start": 0,
                        "end": 5,
                        "text": "Bad range",
                        "bbox": [0, 0, 10, 10],
                        "type": "text",
                        "reading_order": 0,
                    }
                ],
            )

    def test_regular_ocr_valid_payload(self):
        """Test regular OCR valid payload still passes."""
        et = ExtractedText(
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
        assert len(et.segments) == 2


class TestExtractedTextCreateWithDataset:
    """Test ExtractedTextCreate schema with dataset field."""

    def test_create_with_dataset(self):
        """Test ExtractedTextCreate accepts dataset."""
        data = {
            "language": "te",
            "model_name": "manual",
            "extraction_type": "manual",
            "dataset": "story",
            "segments": [
                {
                    "text": "Content",
                    "extraction_metadata": {"title": "T", "category": "story"},
                }
            ],
        }
        et = ExtractedTextCreate(**data)
        assert et.dataset == "story"

    def test_create_without_dataset(self):
        """Test ExtractedTextCreate works without dataset."""
        data = {
            "language": "en",
            "model_name": "test",
            "extraction_type": "asr",
            "segments": [{"start": 0.0, "end": 1.0, "text": "Hello"}],
        }
        et = ExtractedTextCreate(**data)
        assert et.dataset is None


class TestSkipAndCategoryValidation:
    """Test skip/skip_reason/category validation rules."""

    # ── Record-level skip validation ─────────────────────────────────
    # Rule: if skipped=true, skip_reason is required (regardless of category)

    def test_record_skip_true_no_skip_reason(self):
        """skipped=true without skip_reason → error."""
        with pytest.raises(ValidationError, match="skip_reason is required"):
            ExtractedText(extraction_type="manual", skipped=True)

    def test_record_skip_true_with_skip_reason(self):
        """skipped=true with skip_reason passes."""
        et = ExtractedText(
            extraction_type="manual",
            skipped=True,
            skip_reason="Unclear page",
        )
        assert et.skip_reason == "Unclear page"

    def test_record_skip_false_no_skip_reason(self):
        """skipped=false without skip_reason passes."""
        et = ExtractedText(extraction_type="manual", skipped=False)
        assert et.skipped is False
        assert et.skip_reason is None

    # ── Segment-level skip validation (dataset=story) ────────────────
    # Rule: if seg.skipped=true and seg.category=story, seg.skip_reason required

    def test_segment_skip_true_story_no_skip_reason(self):
        """dataset='story', segment skipped=true, category=story → error."""
        with pytest.raises(ValidationError, match="skip_reason is required"):
            ExtractedText(
                extraction_type="manual",
                dataset="story",
                segments=[
                    {
                        "text": "Skipped story",
                        "skipped": True,
                        "extraction_metadata": {
                            "title": "T",
                            "category": "story",
                        },
                    }
                ],
            )

    def test_segment_skip_true_story_with_skip_reason(self):
        """Segment skipped=true, category=story, with skip_reason."""
        et = ExtractedText(
            extraction_type="manual",
            dataset="story",
            segments=[
                {
                    "text": "Skipped story",
                    "skipped": True,
                    "skip_reason": "Unclear page",
                    "extraction_metadata": {
                        "title": "T",
                        "category": "story",
                    },
                }
            ],
        )
        assert et.segments[0].skip_reason == "Unclear page"

    def test_segment_skip_true_poem_no_skip_reason(self):
        """Segment skipped=true, category=poem, skip_reason optional."""
        et = ExtractedText(
            extraction_type="manual",
            dataset="story",
            segments=[
                {
                    "text": "Skipped poem",
                    "skipped": True,
                    "extraction_metadata": {
                        "title": "T",
                        "category": "poem",
                    },
                }
            ],
        )
        assert et.segments[0].skipped is True
        assert et.segments[0].skip_reason is None

    # ── Category validation ──────────────────────────────────────────
    # Rule: category required only when dataset=story (per-segment)

    def test_dataset_story_segment_requires_category(self):
        """dataset='story' requires category in segment extraction_metadata."""
        with pytest.raises(
            ValidationError, match="extraction_metadata.category"
        ):
            ExtractedText(
                extraction_type="manual",
                dataset="story",
                segments=[
                    {
                        "text": "No category",
                        "extraction_metadata": {"title": "T"},
                    }
                ],
            )

    def test_dataset_story_segment_with_category_passes(self):
        """dataset='story' with category in segment passes."""
        et = ExtractedText(
            extraction_type="manual",
            dataset="story",
            segments=[
                {
                    "text": "Content",
                    "extraction_metadata": {"title": "T", "category": "story"},
                }
            ],
        )
        assert et.segments[0].extraction_metadata["category"] == "story"

    def test_dataset_none_no_category_required(self):
        """dataset=None does not require category."""
        et = ExtractedText(extraction_type="manual")
        assert et.dataset is None

    # ── ExtractedTextUpdate tests ────────────────────────────────────

    def test_update_skip_true_no_skip_reason(self):
        """ExtractedTextUpdate: skipped=true without skip_reason → error."""
        with pytest.raises(ValidationError, match="skip_reason is required"):
            ExtractedTextUpdate(extraction_type="manual", skipped=True)

    def test_update_skip_true_with_skip_reason(self):
        """ExtractedTextUpdate: skipped=true with skip_reason passes."""
        et = ExtractedTextUpdate(
            extraction_type="manual",
            skipped=True,
            skip_reason="Unclear page",
        )
        assert et.skip_reason == "Unclear page"


class TestExtractedTextUpdateWithDataset:
    """Test ExtractedTextUpdate schema with dataset field."""

    def test_update_dataset(self):
        """Test ExtractedTextUpdate accepts dataset change."""
        et = ExtractedTextUpdate(dataset="story")
        assert et.dataset == "story"

    def test_update_with_segments_and_dataset(self):
        """Test ExtractedTextUpdate with segments and dataset."""
        et = ExtractedTextUpdate(
            extraction_type="manual",
            dataset="story",
            segments=[
                {
                    "text": "Updated content",
                    "extraction_metadata": {
                        "title": "Updated",
                        "category": "story",
                    },
                }
            ],
        )
        assert et.dataset == "story"

    def test_update_story_ocr_relaxed(self):
        """Test ExtractedTextUpdate with story+ocr still relaxed."""
        et = ExtractedTextUpdate(
            extraction_type="ocr",
            dataset="story",
            segments=[
                {
                    "start": 0,
                    "end": 1,
                    "text": "Page",
                    "extraction_metadata": {"title": "T", "category": "story"},
                }
            ],
        )
        assert et.segments[0].text == "Page"

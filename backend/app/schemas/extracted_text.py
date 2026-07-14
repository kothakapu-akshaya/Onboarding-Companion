"""Pydantic schemas for extracted text validation with comprehensive safety."""

import json
import re
import unicodedata
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

ALLOWED_OCR_SEGMENT_TYPES = {
    "text",
    "title",
    "image_caption",
    "table",
    "image",
    "equation",
    "list",
    "header",
    "footer",
    "page_footnote",
}


class ExtractedTextType(str, Enum):
    """Type of text extraction method used."""

    ocr = "ocr"
    asr = "asr"  # Automatic Speech Recognition
    caption = "caption"
    manual = "manual"


class SkipReason(str, Enum):
    """Reason for skipping a segment."""

    unclear_page = "Unclear page"
    other = "Other"


class Category(str, Enum):
    """Category of the segment."""

    poem = "poem"
    story = "story"
    interview = "interview"
    article = "article"
    editorial = "editorial"
    miscellaneous = "miscellaneous"


class EditType(str, Enum):
    """Type of edit applied to a segment."""

    grammatical_fixes = "grammatical fixes"
    rearrangement = "rearrangement"
    others = "others"


class TextSegment(BaseModel):
    """Individual text segment with timing/position information."""

    start: float | None = Field(
        None,
        ge=0,
        description="Start time in seconds (for audio/video) or position",
    )
    end: float | None = Field(
        None,
        ge=0,
        description="End time in seconds (for audio/video) or position",
    )
    text: str = Field(
        ..., min_length=1, description="Text content of this segment"
    )
    confidence: float | None = Field(
        None, ge=0, le=1, description="Confidence score for this segment"
    )
    proofread: bool = Field(
        default=False, description="Indicates if the segment has been proofread"
    )
    validated: bool = Field(
        default=False, description="Indicates if the segment has been validated"
    )
    bbox: list[float] | None = Field(
        None, description="OCR bounding box in [x1, y1, x2, y2] format"
    )
    type: str | None = Field(
        None, min_length=1, max_length=50, description="OCR segment type"
    )
    reading_order: int | None = Field(
        None, ge=0, description="OCR reading order"
    )

    skipped: bool = Field(
        default=False,
        description="Indicates if this segment should be skipped",
    )
    skip_reason: SkipReason | None = Field(
        default=None,
        description="Reason for skipping this segment",
    )
    edit: list[EditType] | None = Field(
        default=None,
        description="Types of edits applied to this segment",
    )

    named_entities: dict[str, list[str] | dict[str, str | None]] | None = Field(
        None,
        description=(
            "Story-level named entities grouped by type "
            "(e.g. characters, locations, keywords)"
        ),
    )
    extraction_metadata: dict[str, Any] | None = Field(
        None,
        description="Story-level metadata (e.g. title, author, genre, moral)",
    )

    @field_validator("end")
    @classmethod
    def validate_end_after_start(cls, v, info):
        """Ensure end time is after start time."""
        if v is not None and info.data.get("start") is not None:
            if v <= info.data["start"]:
                raise ValueError("End time must be greater than start time")
        return v

    @field_validator("type")
    @classmethod
    def validate_segment_type(cls, v):
        """Ensure segment type is safe for JSON storage."""
        if v is None:
            return v
        return validate_safe_text_content(v, max_length=50)

    @field_validator("bbox")
    @classmethod
    def validate_bbox_shape(cls, v):
        """Validate bbox as [x1, y1, x2, y2] with valid geometry."""
        if v is None:
            return v
        if len(v) != 4:
            raise ValueError(
                "bbox must contain exactly 4 values: [x1, y1, x2, y2]"
            )
        x1, y1, x2, y2 = v
        if x2 <= x1 or y2 <= y1:
            raise ValueError(
                "bbox coordinates must satisfy x2 > x1 and y2 > y1"
            )
        return v


class ExtractedText(BaseModel):
    """Schema for extracted text with all fields and validators."""

    confidence: float | None = Field(
        None,
        ge=0,
        le=1,
        description="Overall confidence score for the extraction",
    )
    language: str | None = Field(
        None, max_length=50, description="Detected or specified language code"
    )
    extraction_type: ExtractedTextType = Field(
        ..., description="Type of extraction method used"
    )
    dataset: str | None = Field(
        None,
        max_length=50,
        description="Dataset category (e.g. story, article)",
    )
    quality_score: float | None = Field(
        None, ge=0, le=1, description="Quality/confidence score for this text"
    )
    notes: str | None = Field(
        None,
        max_length=1000,
        description="Additional notes about the text or corrections",
    )
    segments: list[TextSegment] | None = Field(
        None,
        max_length=10000,
        description="Segmented text with timing/position information",
    )
    summary: str | None = Field(
        None,
        max_length=2000,
        description="Summary of the story/document content",
    )
    named_entities: list[dict[str, str]] | None = Field(
        None,
        max_length=100,
        description="Named entities in the document",
    )
    model_name: str | None = Field(
        None, max_length=100, description="Name/version of the AI model used"
    )
    processing_date: str | None = Field(
        None, description="ISO datetime when extraction was performed"
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Additional extraction-specific metadata"
    )
    skipped: bool = Field(
        default=False,
        description="Indicates if this record should be skipped",
    )
    skip_reason: SkipReason | None = Field(
        default=None,
        description="Reason for skipping this record",
    )
    edit: list[EditType] | None = Field(
        default=None,
        description="Types of edits applied to this record",
    )

    @field_validator("confidence", "quality_score")
    @classmethod
    def validate_confidence_range(cls, v):
        if v is None:
            return v
        return validate_confidence_score(v)

    @field_validator("language")
    @classmethod
    def validate_language_format(cls, v):
        if v is None:
            return v
        return validate_language_code(v)

    @field_validator("model_name", "processing_date")
    @classmethod
    def validate_text_fields(cls, v):
        if v is None:
            return v
        return validate_safe_text_content(str(v), max_length=100)

    @field_validator("notes")
    @classmethod
    def validate_notes_content(cls, v):
        if v is None:
            return v
        cleaned = validate_safe_text_content(str(v), max_length=1000)
        if len(re.findall(r"[<>{}[\]\\]", cleaned)) > 10:
            raise ValueError("Notes contain excessive markup characters")
        return cleaned

    @field_validator("summary")
    @classmethod
    def validate_summary_content(cls, v):
        if v is None:
            return v
        return validate_safe_text_content(str(v), max_length=2000)

    @field_validator("named_entities")
    @classmethod
    def validate_named_entities(cls, v):
        if v is None:
            return v
        if len(v) > 100:
            raise ValueError("Maximum 100 named entities allowed")
        for entity in v:
            if not isinstance(entity, dict):
                raise ValueError("Each named entity must be a dictionary")
            for key, value in entity.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError(
                        "Named entity keys and values must be strings"
                    )
                if len(key) > 50:
                    raise ValueError(
                        "Named entity key too long (max 50 characters)"
                    )
                if len(value) > 200:
                    raise ValueError(
                        "Named entity value too long (max 200 characters)"
                    )
                validate_safe_text_content(key, max_length=50)
                validate_safe_text_content(value, max_length=200)
        return v

    @field_validator("segments")
    @classmethod
    def validate_segments_consistency(cls, v):
        if v is not None:
            if len(v) == 0:
                raise ValueError("Segments list cannot be empty if provided")
            segment_dicts = []
            for segment in v:
                if hasattr(segment, "model_dump"):
                    segment_dicts.append(segment.model_dump())
                else:
                    segment_dicts.append(segment)
            validate_json_serializable(segment_dicts)
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata_comprehensive(cls, v):
        if v is not None:
            if len(str(v)) > 10000:
                raise ValueError("Metadata too large, maximum 10KB allowed")
            v = validate_metadata_keys(v)
            validate_json_serializable(v)
        return v

    @model_validator(mode="after")
    def validate_model_consistency(self):
        if self.segments:
            if self.extraction_type is None:
                raise ValueError(
                    "extraction_type is required when segments are provided"
                )
            segment_dicts = [
                segment.model_dump()
                if hasattr(segment, "model_dump")
                else segment
                for segment in self.segments
            ]
            is_story_ocr = (
                self.dataset == "story"
                and self.extraction_type == ExtractedTextType.ocr
            )
            if is_story_ocr:
                for i, seg in enumerate(segment_dicts):
                    if seg.get("start") is None or seg.get("end") is None:
                        raise ValueError(
                            f"Segment {i}: start and end required"
                            " when extraction_type='ocr'"
                        )
                    if seg["end"] <= seg["start"]:
                        raise ValueError(
                            f"Segment {i}: end must be greater than start"
                        )
            elif self.extraction_type == ExtractedTextType.ocr:
                validate_ocr_segments(segment_dicts)
            else:
                validate_timestamp_segments(segment_dicts)
            if self.dataset == "story":
                for i, seg in enumerate(segment_dicts):
                    if not seg.get("extraction_metadata"):
                        raise ValueError(
                            f"Segment {i}: extraction_metadata required"
                            " when dataset='story'"
                        )
                    if "title" not in seg.get("extraction_metadata", {}):
                        raise ValueError(
                            f"Segment {i}: extraction_metadata.title"
                            " required when dataset='story'"
                        )
                    seg_meta = seg.get("extraction_metadata") or {}
                    if not seg_meta.get("category"):
                        raise ValueError(
                            f"Segment {i}: extraction_metadata.category"
                            " is required when dataset='story'"
                        )
                    if seg_meta.get("category") not in [
                        c.value for c in Category
                    ]:
                        raise ValueError(
                            f"Segment {i}: extraction_metadata.category"
                            " must be one of"
                            f" {[c.value for c in Category]}"
                        )
                    if seg.get("skipped"):
                        seg_category = seg_meta.get("category")
                        if seg_category == Category.story:
                            if not seg.get("skip_reason"):
                                raise ValueError(
                                    f"Segment {i}: skip_reason is required"
                                    " when skipped is true"
                                    " and category is 'story'"
                                )
        if (self.confidence is not None and self.confidence < 0.3) or (
            self.quality_score is not None and self.quality_score < 0.3
        ):
            if not self.metadata:
                self.metadata = {}
            self.metadata["low_confidence_warning"] = True
        if self.skipped and not self.skip_reason:
            raise ValueError("skip_reason is required when skipped is true")
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "validation_timestamp": datetime.now().isoformat(),
                "has_quality_score": self.quality_score is not None,
            }
        )
        return self


class ExtractedTextCreate(ExtractedText):
    """POST schema: language, segments, model_name required."""

    model_config = ConfigDict(extra="forbid")

    language: str = Field(
        ..., max_length=50, description="Detected or specified language code"
    )
    segments: list[TextSegment] = Field(
        ...,
        max_length=10000,
        description="Segmented text with timing/position information",
    )
    model_name: str = Field(
        ..., max_length=100, description="Name/version of the AI model used"
    )
    device_id: str | None = Field(
        None,
        max_length=255,
        description=(
            "Client-generated device identifier of the device that "
            "performed this extraction, as registered via the devices "
            "endpoint"
        ),
    )


class ExtractedTextUpdate(ExtractedText):
    """PATCH schema: all optional, body must be non-empty."""

    model_config = ConfigDict(extra="forbid")

    extraction_type: ExtractedTextType | None = Field(
        None, description="Type of extraction method used"
    )

    @model_validator(mode="after")
    def ensure_non_empty_body(self):
        user_provided = self.model_dump(exclude_unset=True)
        user_provided.pop("metadata", None)
        if not user_provided:
            raise ValueError("At least one field must be provided for update")
        return self

    @model_validator(mode="after")
    def validate_model_consistency(self):
        if self.segments:
            if self.extraction_type is None:
                raise ValueError(
                    "extraction_type is required when segments are provided"
                )
            segment_dicts = [
                seg.model_dump() if hasattr(seg, "model_dump") else seg
                for seg in self.segments
            ]
            is_story_ocr = (
                self.dataset == "story"
                and self.extraction_type == ExtractedTextType.ocr
            )
            if is_story_ocr:
                for i, seg in enumerate(segment_dicts):
                    if seg.get("start") is None or seg.get("end") is None:
                        raise ValueError(
                            f"Segment {i}: start and end required"
                            " when extraction_type='ocr'"
                        )
                    if seg["end"] <= seg["start"]:
                        raise ValueError(
                            f"Segment {i}: end must be greater than start"
                        )
            if self.dataset == "story":
                for i, seg in enumerate(segment_dicts):
                    if not seg.get("extraction_metadata"):
                        raise ValueError(
                            f"Segment {i}: extraction_metadata required"
                            " when dataset='story'"
                        )
                    if "title" not in seg.get("extraction_metadata", {}):
                        raise ValueError(
                            f"Segment {i}: extraction_metadata.title"
                            " required when dataset='story'"
                        )
                    if seg.get("skipped"):
                        seg_meta = seg.get("extraction_metadata") or {}
                        seg_category = seg_meta.get("category")
                        if seg_category == Category.story:
                            if not seg.get("skip_reason"):
                                raise ValueError(
                                    f"Segment {i}: skip_reason is required"
                                    " when skipped is true"
                                    " and category is 'story'"
                                )
        if (self.confidence is not None and self.confidence < 0.3) or (
            self.quality_score is not None and self.quality_score < 0.3
        ):
            if not self.metadata:
                self.metadata = {}
            self.metadata["low_confidence_warning"] = True
        if self.skipped and not self.skip_reason:
            raise ValueError("skip_reason is required when skipped is true")
        if not self.metadata:
            self.metadata = {}
        self.metadata.update(
            {
                "validation_timestamp": datetime.now().isoformat(),
                "has_quality_score": self.quality_score is not None,
            }
        )
        return self


def validate_safe_text_content(text: str, max_length: int | None = None) -> str:
    """Comprehensive text validation for JSONB safety and security."""
    if not text:
        return text

    # 1. Unicode normalization to prevent homograph attacks
    text = unicodedata.normalize("NFKC", text)

    # 2. Remove dangerous Unicode categories
    # Cf = Other, format (invisible formatting)
    # Cn = Other, not assigned (undefined)
    # Co = Other, private use
    # Cs = Other, surrogate (invalid in UTF-8)
    text = "".join(
        char
        for char in text
        if unicodedata.category(char) not in ["Cf", "Cn", "Co", "Cs"]
    )

    # 3. Remove null bytes and most control characters (keep \n, \t, \r)
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

    # 4. Normalize whitespace
    sanitized = re.sub(
        r"\n{4,}", "\n\n\n", sanitized
    )  # Max 3 consecutive newlines
    sanitized = re.sub(r" {6,}", "     ", sanitized)  # Max 5 consecutive spaces
    sanitized = re.sub(r"\t{4,}", "\t\t\t", sanitized)  # Max 3 consecutive tabs

    # 5. Remove potential script injection patterns
    sanitized = re.sub(
        r"<script[^>]*>.*?</script>",
        "",
        sanitized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    sanitized = re.sub(r"javascript:", "", sanitized, flags=re.IGNORECASE)

    # 6. Trim excessive length
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()

    # 7. Remove leading/trailing whitespace
    sanitized = sanitized.strip()

    return sanitized


def validate_language_code(lang_code: str) -> str:
    """Validate language codes (ISO 639-1/639-3 format)."""
    if not lang_code:
        return lang_code

    # Basic validation for language codes
    lang_code = lang_code.lower().strip()

    # Allow ISO 639-1 (2 chars), ISO 639-3 (3 chars), and locale formats (en-US)
    if not re.match(r"^[a-z]{2,3}(-[a-z]{2,4})?$", lang_code):
        raise ValueError(f"Invalid language code format: {lang_code}")

    return lang_code


def validate_confidence_score(score: float) -> float:
    """Validate and normalize confidence scores."""
    if score < 0 or score > 1:
        raise ValueError(
            f"Confidence score must be between 0 and 1, got {score}"
        )

    # Round to reasonable precision (4 decimal places)
    return round(score, 4)


def validate_timestamp_segments(segments: list[dict]) -> list[dict]:
    """Validate temporal consistency in text segments."""
    if not segments or len(segments) <= 1:
        return segments

    prev_end = 0
    for i, segment in enumerate(segments):
        start = segment.get("start")
        end = segment.get("end")

        if start is not None:
            # Check start time is not before previous segment's end
            if start < prev_end:
                raise ValueError(
                    f"Segment {i} starts before previous segment ends"
                )

            # Update previous end time
            if end is not None:
                prev_end = end

    return segments


def validate_ocr_segments(segments: list[dict]) -> list[dict]:
    """Validate OCR segment payload.

    - bbox/type/reading_order must be present
    - start/end must follow page-index rule: end == start + 1
    - reading_order must be increasing within each start/end pair
    - reading_order must reset to 0 for each new start/end pair.
    """
    if not segments:
        raise ValueError("OCR extraction requires non-empty segments")

    prev_start_end = None
    expected_reading_order = 0

    for i, segment in enumerate(segments):
        missing_fields = [
            field_name
            for field_name in ("bbox", "type", "reading_order", "start", "end")
            if segment.get(field_name) is None
        ]
        if missing_fields:
            raise ValueError(
                f"OCR segment {i} missing required fields: "
                f"{', '.join(missing_fields)}"
            )

        start = segment["start"]
        end = segment["end"]
        if end != start + 1:
            raise ValueError(f"OCR segment {i} must have end == start + 1")

        segment_type = str(segment["type"]).strip()
        if segment_type not in ALLOWED_OCR_SEGMENT_TYPES:
            allowed = sorted(ALLOWED_OCR_SEGMENT_TYPES)
            raise ValueError(
                f"OCR segment {i} has unsupported type '{segment_type}'. "
                f"Allowed types: {allowed}"
            )

        reading_order = segment["reading_order"]
        current_start_end = (start, end)

        # Check if we have a new start/end pair
        if current_start_end != prev_start_end:
            # Reading order must reset to 0 for new start/end pair
            if reading_order != 0:
                raise ValueError(
                    f"OCR segment {i} has reading_order {reading_order}, "
                    f"but must start at 0 for new start/end pair "
                    f"({start}, {end})"
                )
            expected_reading_order = 1
        else:
            # Same start/end pair - reading_order must be strictly increasing
            if reading_order != expected_reading_order:
                raise ValueError(
                    f"OCR segment {i} has reading_order {reading_order}, "
                    f"but expected {expected_reading_order} for start/end "
                    f"pair ({start}, {end})"
                )
            expected_reading_order += 1

        prev_start_end = current_start_end

    return segments


def detect_potential_pii(text: str) -> list[str]:
    """Detect potential PII patterns and return warnings."""
    warnings = []

    # Email patterns
    if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text):
        warnings.append("potential_email_detected")

    # Phone number patterns (basic)
    if re.search(
        r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
        text,
    ):
        warnings.append("potential_phone_detected")

    # Credit card patterns (basic)
    if re.search(r"\b(?:\d[ -]*?){13,19}\b", text):
        warnings.append("potential_credit_card_detected")

    # Social security number patterns (US)
    if re.search(r"\b\d{3}-?\d{2}-?\d{4}\b", text):
        warnings.append("potential_ssn_detected")

    return warnings


def validate_metadata_keys(metadata: dict[str, Any]) -> dict[str, Any]:
    """Validate metadata dictionary keys and structure."""
    if not isinstance(metadata, dict):
        return metadata

    clean_metadata: dict[str, Any] = {}
    reserved_keys = {
        "_id",
        "_rev",
        "_type",
        "constructor",
        "prototype",
        "__proto__",
    }

    for key, value in metadata.items():
        # Validate key format
        if not isinstance(key, str):
            raise ValueError(f"Metadata keys must be strings, got {type(key)}")

        # Check for reserved/dangerous keys
        if key.lower() in reserved_keys or key.startswith("__"):
            raise ValueError(f"Reserved metadata key not allowed: {key}")

        # Sanitize key
        safe_key = re.sub(r"[^\w\-_.]", "_", key)[:50]  # Limit key length

        # Recursively validate nested objects
        if isinstance(value, dict):
            clean_metadata[safe_key] = validate_metadata_keys(value)
        elif isinstance(value, str):
            clean_metadata[safe_key] = validate_safe_text_content(
                value, max_length=1000
            )
        else:
            clean_metadata[safe_key] = value

    return clean_metadata


def validate_json_serializable(obj: Any) -> Any:
    """Ensure the object is JSON serializable to prevent storage issues."""
    try:
        # Test JSON serialization
        json.dumps(obj, ensure_ascii=False)
        return obj
    except (TypeError, ValueError) as e:
        raise ValueError(f"Object not JSON serializable: {e}")


class ExtractedTextUpdateResponse(BaseModel):
    """Response schema for text updates."""

    message: str
    record_id: str
    new_version: int
    history_entry_id: str | None = None
    version_info: dict[str, Any]

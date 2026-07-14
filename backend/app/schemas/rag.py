"""RAG schemas for semantic metadata indexing and hybrid retrieval."""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RAGStatus(str, Enum):
    """RAG processing status enum."""

    no_text = "no_text"
    ready_for_indexing = "ready_for_indexing"
    indexed = "indexed"
    index_failed = "index_failed"


# ── Extracted Text Normalization Schemas ─────────────


class SegmentSchema(BaseModel):
    """Schema for a text segment with optional timing."""

    text: str
    page: str | None = None
    start: float | None = None
    end: float | None = None
    bbox: list[float] | None = None
    type: str | None = None
    reading_order: int | None = None


class NormalizedInputSchema(BaseModel):
    """Normalized extracted text with segments."""

    transcription: str
    segments: list[SegmentSchema] = Field(default_factory=list)


class TextNormalizer:
    """Utilities for normalizing extracted text data."""

    @staticmethod
    def _coerce_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _coerce_time_value(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def normalize_raw_text(text: str) -> NormalizedInputSchema:
        return NormalizedInputSchema(
            transcription=text, segments=[SegmentSchema(text=text)]
        )

    @staticmethod
    def normalize_json_extracted(extracted_text: Any) -> NormalizedInputSchema:
        # Handle if it's a model instance or a dict
        is_dict = isinstance(extracted_text, dict)

        def get_val(key: str, default: Any = None) -> Any:
            if is_dict:
                return extracted_text.get(key, default)
            return getattr(extracted_text, key, default)

        transcription = TextNormalizer._coerce_text(
            get_val("transcription")
            or get_val("full_text")
            or get_val("summary")
            or ""
        )

        raw_segments = get_val("segments", [])
        if not isinstance(raw_segments, list):
            raw_segments = []

        segments = []
        for seg in raw_segments:
            if isinstance(seg, dict):
                segment_text = TextNormalizer._coerce_text(seg.get("text", ""))
                page = seg.get("page")
                if page is None:
                    page = seg.get("page_num")
                raw_start = (
                    seg.get("start")
                    if seg.get("start") is not None
                    else seg.get("start_time")
                )
                raw_end = (
                    seg.get("end")
                    if seg.get("end") is not None
                    else seg.get("end_time")
                )
                bbox = seg.get("bbox")
                segment_type = seg.get("type")
                reading_order = seg.get("reading_order")
            else:
                segment_text = TextNormalizer._coerce_text(
                    getattr(seg, "text", "")
                )
                page = getattr(seg, "page", None)
                if page is None:
                    page = getattr(seg, "page_num", None)
                raw_start = getattr(seg, "start", None)
                if raw_start is None:
                    raw_start = getattr(seg, "start_time", None)
                raw_end = getattr(seg, "end", None)
                if raw_end is None:
                    raw_end = getattr(seg, "end_time", None)
                bbox = getattr(seg, "bbox", None)
                segment_type = getattr(seg, "type", None)
                reading_order = getattr(seg, "reading_order", None)

            start = TextNormalizer._coerce_time_value(raw_start)
            end = TextNormalizer._coerce_time_value(raw_end)
            segments.append(
                SegmentSchema(
                    text=segment_text,
                    page=TextNormalizer._coerce_text(page) if page else None,
                    start=start,
                    end=end,
                    bbox=bbox if isinstance(bbox, list) else None,
                    type=(
                        TextNormalizer._coerce_text(segment_type)
                        if segment_type
                        else None
                    ),
                    reading_order=(
                        reading_order
                        if isinstance(reading_order, int)
                        else None
                    ),
                )
            )

        if not transcription and segments:
            transcription = " ".join(
                [s.text for s in segments if s.text]
            ).strip()

        return NormalizedInputSchema(
            transcription=transcription, segments=segments
        )

    @staticmethod
    def has_meaningful_extracted_text(data: Any) -> bool:
        if not data:
            return False
        normalized = TextNormalizer.normalize_json_extracted(data)
        if normalized.transcription and normalized.transcription.strip():
            return True
        return any(seg.text and seg.text.strip() for seg in normalized.segments)


# ── Response & Request Schemas ───────────────────────


class ExtractedTextUpdateSchema(BaseModel):
    """Schema for direct ExtractedText table field updates."""

    summary: str = Field(min_length=1)
    named_entities: list[dict[str, str]] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def summary_not_whitespace(cls, v: str) -> str:  # noqa: vulture
        if not v.strip():
            raise ValueError("Summary cannot be empty or whitespace")
        return v.strip()


class ExtractionMetadataSchema(BaseModel):
    """Strict schema for semantic extraction results (JSONB)."""

    model_config = {"extra": "forbid"}

    topics: list[str] = Field(min_length=1)
    key_concepts: list[dict[str, Any]] = Field(default_factory=list)
    themes: list[str] = Field(min_length=1)
    content_classification: dict[str, Any] = Field(default_factory=dict)


class KnowledgeResponse(BaseModel):
    """Unified knowledge status and semantic content response."""

    status: RAGStatus
    cache_valid: bool
    current_version: int
    indexed_version: int | None = None
    record_id: UUID
    record_title: str
    summary: str | None = None
    named_entities: list[dict[str, str]] | None = None
    extraction_metadata: dict[str, Any] | None = None
    extracted_text_source_record_id: UUID | None = None


class KnowledgeUpdateRequest(BaseModel):
    """Request to update extractedtext semantic metadata."""

    extracted_text: ExtractedTextUpdateSchema
    extraction_metadata: ExtractionMetadataSchema


class KnowledgeUpdateResponse(BaseModel):
    """Response after updating knowledge data."""

    status: str
    record_id: UUID
    indexed_version: int


class RetrievalRequest(BaseModel):
    """Request to search within a record."""

    query: str = Field(min_length=1)


class RetrievedSegment(BaseModel):
    """A retrieved text segment with match scores."""

    segment_index: int
    text: str
    page: str | None = None
    start: float | None = None
    end: float | None = None
    bbox: list[float] | None = None
    type: str | None = None
    reading_order: int | None = None
    is_match: bool | None = None
    score: float | None = None
    fts_score: float | None = None
    trigram_score: float | None = None
    hybrid_score: float | None = None


class RetrievalStats(BaseModel):
    """Statistics for a retrieval operation."""

    total_segments: int
    matched_count: int
    context_count: int
    used_fallback: bool


class RetrievalResponse(BaseModel):
    """Response with retrieval results and stats."""

    record_id: UUID
    query: str
    strategy: str
    matched_segments: list[RetrievedSegment]
    context_segments: list[RetrievedSegment]
    stats: RetrievalStats
    adaptive_params: dict[str, Any]

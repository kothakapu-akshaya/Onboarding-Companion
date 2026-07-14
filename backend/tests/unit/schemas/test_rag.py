"""Unit tests for RAG schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.rag import (
    ExtractedTextUpdateSchema,
    ExtractionMetadataSchema,
    KnowledgeResponse,
    KnowledgeUpdateRequest,
    NormalizedInputSchema,
    RAGStatus,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalStats,
    RetrievedSegment,
    SegmentSchema,
    TextNormalizer,
)


class TestRAGStatus:
    def test_enum_values(self):
        assert RAGStatus.no_text.value == "no_text"
        assert RAGStatus.ready_for_indexing.value == "ready_for_indexing"
        assert RAGStatus.indexed.value == "indexed"
        assert RAGStatus.index_failed.value == "index_failed"


class TestKnowledgeResponse:
    def test_model_serialization(self):
        response = KnowledgeResponse(
            status=RAGStatus.indexed,
            cache_valid=True,
            current_version=1,
            indexed_version=1,
            record_id=uuid4(),
            record_title="Test Record",
        )

        dumped = response.model_dump()
        assert dumped["status"] == RAGStatus.indexed
        assert dumped["cache_valid"] is True
        assert dumped["current_version"] == 1


class TestKnowledgeUpdateRequest:
    def test_valid_request(self):
        extraction_meta = ExtractionMetadataSchema(
            topics=["topic1"],
            key_concepts=[{"concept": "c1", "context": "ctx"}],
            themes=["Theme1"],
            content_classification={"tone": "neutral"},
        )
        extracted_text = ExtractedTextUpdateSchema(
            summary="Top-level summary",
            named_entities=[{"text": "e1", "type": "T1"}],
        )
        request = KnowledgeUpdateRequest(
            extracted_text=extracted_text,
            extraction_metadata=extraction_meta,
        )

        assert request.extracted_text.summary == "Top-level summary"
        assert "topic1" in request.extraction_metadata.topics


class TestRetrievalRequest:
    def test_valid_request(self):
        request = RetrievalRequest(query="What is this about?")

        assert request.query == "What is this about?"

    def test_query_required(self):
        with pytest.raises(ValidationError):
            RetrievalRequest(query="")  # min_length=1


class TestTextNormalizer:
    def test_normalize_multimedia_segment_metadata(self):
        normalized = TextNormalizer.normalize_json_extracted(
            {
                "segments": [
                    {
                        "text": "Frame text",
                        "page_num": 2,
                        "start_time": 1.5,
                        "end_time": 3.0,
                        "bbox": [10.0, 20.0, 50.0, 80.0],
                        "type": "image_caption",
                        "reading_order": 4,
                    }
                ]
            }
        )

        assert isinstance(normalized, NormalizedInputSchema)
        assert normalized.segments == [
            SegmentSchema(
                text="Frame text",
                page="2",
                start=1.5,
                end=3.0,
                bbox=[10.0, 20.0, 50.0, 80.0],
                type="image_caption",
                reading_order=4,
            )
        ]


class TestKnowledgeResponseExtended:
    def test_response_model(self):
        response = KnowledgeResponse(
            record_id=uuid4(),
            record_title="Sample Record",
            status=RAGStatus.indexed,
            cache_valid=True,
            current_version=1,
            summary="Main summary",
            extraction_metadata={"topics": ["t1"]},
        )

        assert response.record_title == "Sample Record"
        assert response.summary == "Main summary"
        assert response.extraction_metadata["topics"] == ["t1"]


class TestRetrievalResponse:
    def test_nested_models(self):
        response = RetrievalResponse(
            record_id=uuid4(),
            query="Explain the topic",
            strategy="hybrid_chunks",
            matched_segments=[
                RetrievedSegment(
                    segment_index=0,
                    text="Segment text",
                    bbox=[1.0, 2.0, 3.0, 4.0],
                    type="ocr",
                    reading_order=1,
                    score=0.9,
                )
            ],
            context_segments=[],
            stats=RetrievalStats(
                total_segments=1,
                matched_count=1,
                context_count=0,
                used_fallback=False,
            ),
            adaptive_params={"top_k": 8, "context_window": 1},
        )

        assert response.matched_segments[0].text == "Segment text"
        assert response.matched_segments[0].bbox == [1.0, 2.0, 3.0, 4.0]
        assert response.stats.total_segments == 1

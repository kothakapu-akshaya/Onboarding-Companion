"""Unit tests for RAG hybrid retrieval service."""

from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.services.hybrid_retrieval import HybridRetrievalService


class TestHybridRetrievalHelpers:
    def test_strip_stop_words(self) -> None:
        result = HybridRetrievalService._strip_stop_words(
            "what is the main harvest theme"
        )

        assert result == "main harvest theme"

    def test_normalize_query(self) -> None:
        result = HybridRetrievalService._normalize_query(
            "  what   is   harvest   songs  "
        )

        assert result == "harvest songs"

    def test_build_or_tsquery(self) -> None:
        result = HybridRetrievalService._build_or_tsquery(
            "telugu harvest songs"
        )

        assert result == "telugu | harvest | songs"


class TestHybridRetrievalRetrieve:
    def test_retrieve_returns_empty_for_stop_word_query(self) -> None:
        session = Mock()

        result = HybridRetrievalService.retrieve(
            session=session,
            record_id=uuid4(),
            extracted_text=None,
            query="what is the and",
        )

        assert result["matched_segments"] == []
        assert result["context_segments"] == []
        assert result["stats"]["total_segments"] == 0

    def test_retrieve_enhanced_success_path(self) -> None:
        session = Mock()
        session.execute.return_value.scalar.return_value = 3

        hybrid_matches = [
            {
                "idx": 1,
                "seg_text": "alpha beta",
                "page": "1",
                "start": 0.0,
                "end": 1.0,
                "bbox": [0.0, 0.0, 5.0, 5.0],
                "segment_type": "ocr",
                "reading_order": 2,
                "fts_score": 0.6,
                "trigram_score": 0.2,
                "hybrid_score": 0.65,
            }
        ]
        context_segments = [
            {
                "segment_index": 1,
                "text": "alpha beta",
                "page": "1",
                "start": 0.0,
                "end": 1.0,
                "bbox": [0.0, 0.0, 5.0, 5.0],
                "type": "ocr",
                "reading_order": 2,
                "is_match": True,
                "score": 0.65,
            }
        ]

        with patch.object(
            HybridRetrievalService,
            "_run_hybrid_query",
            return_value=hybrid_matches,
        ):
            with patch.object(
                HybridRetrievalService,
                "_expand_with_neighbors",
                return_value=context_segments,
            ):
                result = HybridRetrievalService.retrieve(
                    session=session,
                    record_id=uuid4(),
                    extracted_text=SimpleNamespace(
                        segments=[{"text": "alpha beta"}]
                    ),
                    query="what alpha beta",
                    top_k=5,
                    context_window=1,
                    use_enhanced_retrieval=True,
                )

        assert result["strategy"] == "hybrid_jsonb"
        assert result["stats"]["matched_count"] == 1
        assert result["stats"]["context_count"] == 1
        assert result["stats"]["used_fallback"] is False
        assert result["matched_segments"][0]["segment_index"] == 1
        assert result["matched_segments"][0]["type"] == "ocr"
        assert result["matched_segments"][0]["bbox"] == [0.0, 0.0, 5.0, 5.0]
        total_count_sql = str(session.execute.call_args_list[-1].args[0])
        assert "FROM extractedtext" in total_count_sql

    def test_retrieve_falls_back_after_sql_error(self) -> None:
        session = Mock()
        session.execute.return_value.scalar.return_value = 1

        fallback_matches = [
            {
                "idx": 0,
                "seg_text": "fallback text",
                "page": "1",
                "start": None,
                "end": None,
                "fts_score": 0.4,
                "trigram_score": 0.0,
                "hybrid_score": 0.4,
            }
        ]

        with patch.object(
            HybridRetrievalService,
            "_run_hybrid_query",
            side_effect=SQLAlchemyError("boom"),
        ):
            with patch.object(
                HybridRetrievalService,
                "_run_fts_fallback_query",
                return_value=fallback_matches,
            ):
                with patch.object(
                    HybridRetrievalService,
                    "_expand_with_neighbors",
                    return_value=[],
                ):
                    result = HybridRetrievalService.retrieve(
                        session=session,
                        record_id=uuid4(),
                        extracted_text=SimpleNamespace(
                            segments=[{"text": "fallback text"}]
                        ),
                        query="fallback text",
                        use_enhanced_retrieval=False,
                    )

        assert result["strategy"] == "hybrid_jsonb_basic"
        assert result["stats"]["used_fallback"] is True
        assert result["matched_segments"][0]["segment_index"] == 0

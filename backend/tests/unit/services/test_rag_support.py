"""Unit tests for supporting RAG services."""

from types import SimpleNamespace

import pytest

from app.schemas.rag import TextNormalizer
from app.services.metadata_indexer import MetadataIndexer


class TestTextNormalizer:
    def test_normalize_raw_text(self) -> None:
        result = TextNormalizer.normalize_raw_text("Hello world")

        assert result.transcription == "Hello world"
        assert len(result.segments) == 1
        assert result.segments[0].text == "Hello world"

    def test_normalize_json_extracted(self) -> None:
        extracted_text = {
            "transcription": "",
            "segments": [
                {"text": "First", "start": 1.0, "end": 2.0},
                {"text": "Second", "start": 3.0, "end": 3.1},
            ],
        }

        result = TextNormalizer.normalize_json_extracted(extracted_text)

        assert result.transcription == "First Second"
        assert result.segments[0].page is None
        assert result.segments[0].start == 1.0
        assert result.segments[0].end == 2.0
        assert result.segments[1].start == 3.0
        assert result.segments[1].end == 3.1

    def test_normalize_json_extracted_ocr_metadata(self) -> None:
        extracted_text = {
            "segments": [
                {
                    "text": "Caption",
                    "page_num": 3,
                    "bbox": [1.0, 2.0, 3.0, 4.0],
                    "type": "image_caption",
                    "reading_order": 7,
                }
            ]
        }

        result = TextNormalizer.normalize_json_extracted(extracted_text)

        assert result.transcription == "Caption"
        assert result.segments[0].page == "3"
        assert result.segments[0].bbox == [1.0, 2.0, 3.0, 4.0]
        assert result.segments[0].type == "image_caption"
        assert result.segments[0].reading_order == 7

    def test_normalize_json_extracted_model_input(self) -> None:
        extracted_text_model = SimpleNamespace(
            transcription="",
            segments=[
                SimpleNamespace(text="Alpha", start=0.0, end=0.5),
                SimpleNamespace(text="Beta", start_time=0.5, end_time=1.2),
            ],
        )

        result = TextNormalizer.normalize_json_extracted(extracted_text_model)

        assert result.transcription == "Alpha Beta"
        assert len(result.segments) == 2
        assert result.segments[0].start == 0.0
        assert result.segments[0].end == 0.5
        assert result.segments[1].start == 0.5
        assert result.segments[1].end == 1.2

    @pytest.mark.parametrize(
        "data,expected",
        [
            (None, False),
            ({}, False),
            ({"transcription": "Text"}, True),
        ],
    )
    def test_has_meaningful_extracted_text(
        self, data: object, expected: bool
    ) -> None:
        assert TextNormalizer.has_meaningful_extracted_text(data) is expected

    def test_has_meaningful_extracted_text_model_input(self) -> None:
        extracted_text_model = SimpleNamespace(
            transcription="",
            segments=[SimpleNamespace(text="Meaningful text")],
        )

        assert (
            TextNormalizer.has_meaningful_extracted_text(extracted_text_model)
            is True
        )


class TestMetadataIndexer:
    def test_validate_semantic_metadata_filters_keys(self) -> None:
        raw_metadata = {
            "summary": "ignored",
            "topics": ["T1"],
            "key_concepts": [{"c": "v"}],
            "themes": ["Th1"],
            "content_classification": {"type": "A"},
            "extra": "junk",
        }

        validated = MetadataIndexer.validate_semantic_metadata(raw_metadata)

        assert "topics" in validated
        assert "key_concepts" in validated
        assert "themes" in validated
        assert "content_classification" in validated
        assert "summary" not in validated
        assert "extra" not in validated

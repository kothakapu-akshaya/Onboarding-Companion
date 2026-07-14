"""Unit tests for RAG API endpoint module."""

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.records import (
    _assert_record_access,
    create_retrieval,
    get_knowledge,
    upsert_knowledge,
)
from app.models.record import MediaType
from app.models.user import User
from app.schemas.rag import (
    ExtractedTextUpdateSchema,
    ExtractionMetadataSchema,
    KnowledgeUpdateRequest,
    RetrievalRequest,
)


class TestRAGEndpointHelpers:
    def test_assert_record_access_owner(self) -> None:
        user = cast(User, SimpleNamespace(id=uuid4()))
        record = cast(
            Any,
            SimpleNamespace(user_id=user.id, media_type=MediaType.document),
        )
        _assert_record_access(record, user)

    def test_assert_record_access_allows_multimedia_records(self) -> None:
        user = cast(User, SimpleNamespace(id=uuid4()))
        for media_type in (
            MediaType.document,
            MediaType.audio,
            MediaType.video,
            MediaType.image,
            MediaType.text,
        ):
            record = cast(
                Any,
                SimpleNamespace(user_id=user.id, media_type=media_type),
            )
            _assert_record_access(record, user)

    @pytest.mark.parametrize(
        "record_kwargs,status_code",
        [
            ({"user_id": uuid4(), "media_type": MediaType.document}, 403),
            ({"user_id": uuid4(), "media_type": MediaType.image}, 403),
        ],
    )
    def test_assert_record_access_errors(
        self,
        record_kwargs: dict[str, Any],
        status_code: int,
    ) -> None:
        user = cast(User, SimpleNamespace(id=uuid4()))
        record = cast(Any, SimpleNamespace(**record_kwargs))

        with pytest.raises(HTTPException) as exc_info:
            _assert_record_access(record, user)

        assert exc_info.value.status_code == status_code


class TestGetKnowledge:
    @pytest.mark.asyncio
    async def test_missing_record_returns_404(self) -> None:
        session = Mock()
        session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_knowledge(
                uuid4(), session, cast(User, SimpleNamespace(id=uuid4()))
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_text_returns_no_text_status(self) -> None:
        extracted_text = SimpleNamespace(
            summary="",
            segments=[],
            named_entities=None,
            extraction_metadata=None,
        )
        record = SimpleNamespace(
            uid=uuid4(),
            title="Test",
            user_id=uuid4(),
            media_type=MediaType.audio,
            extracted_text=extracted_text,
            version_info=None,
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        response = await get_knowledge(uuid4(), session, user)

        # Assuming TextNormalizer says this lacks meaningful text
        assert response.status.value == "no_text"
        assert response.cache_valid is False

    @pytest.mark.asyncio
    async def test_cached_index_returns_indexed(self) -> None:
        extracted_text = SimpleNamespace(
            summary="Hello world",
            segments=[{"text": "Hello world"}],
            named_entities=None,
            extraction_metadata={
                "semantic_indexed_version": 0,
            },
        )
        record = SimpleNamespace(
            uid=uuid4(),
            title="Test",
            user_id=uuid4(),
            media_type=MediaType.image,
            extracted_text=extracted_text,
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        with patch(
            "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
            return_value=True,
        ):
            response = await get_knowledge(uuid4(), session, user)

        assert response.status.value == "indexed"
        assert response.cache_valid is True


class TestUpsertKnowledge:
    @pytest.mark.asyncio
    async def test_upsert_knowledge_success(self) -> None:
        extracted_text = Mock()
        extracted_text.summary = ""
        extracted_text.named_entities = None
        extracted_text.extraction_metadata = None
        extracted_text.updated_at = None

        record = SimpleNamespace(
            uid=uuid4(),
            user_id=uuid4(),
            media_type=MediaType.video,
            extracted_text=extracted_text,
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        payload = KnowledgeUpdateRequest(
            extracted_text=ExtractedTextUpdateSchema(
                summary="Test Summary",
                named_entities=[{"text": "E1", "type": "T1"}],
            ),
            extraction_metadata=ExtractionMetadataSchema(
                topics=["T1"],
                key_concepts=[],
                themes=["Theme1"],
                content_classification={},
            ),
        )

        with (
            patch(
                "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.records.MetadataIndexer.validate_semantic_metadata",
                return_value={"topics": ["T1"]},
            ) as mock_validate,
        ):
            response = await upsert_knowledge(uuid4(), payload, session, user)

        assert response.status == "indexed"
        assert extracted_text.summary == "Test Summary"
        mock_validate.assert_called_once()


class TestGetKnowledgeExtended:
    @pytest.mark.asyncio
    async def test_get_knowledge_returns_metadata(self) -> None:
        extracted_text = SimpleNamespace(
            summary="ok",
            segments=[{"text": "ok"}],
            named_entities=None,
            extraction_metadata={
                "semantic_indexed_version": 0,
                "topics": ["T1"],
            },
        )
        record = SimpleNamespace(
            uid=uuid4(),
            title="Sample record",
            user_id=uuid4(),
            media_type=MediaType.text,
            extracted_text=extracted_text,
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        with patch(
            "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
            return_value=True,
        ):
            response = await get_knowledge(uuid4(), session, user)

        assert response.record_title == "Sample record"
        assert response.summary == "ok"
        assert response.extraction_metadata is not None
        assert response.extraction_metadata["topics"] == ["T1"]


class TestCreateRetrieval:
    @pytest.mark.asyncio
    async def test_create_retrieval_success(self) -> None:
        extracted_text = SimpleNamespace(
            summary="Hello world",
            segments=[{"text": "Hello world"}],
        )
        record = SimpleNamespace(
            uid=uuid4(),
            user_id=uuid4(),
            media_type=MediaType.audio,
            extracted_text=extracted_text,
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        retrieval_result = {
            "strategy": "hybrid_chunks",
            "matched_segments": [
                {
                    "segment_index": 0,
                    "text": "Hello world",
                    "page": "1",
                    "start": None,
                    "end": None,
                    "bbox": [0.0, 0.0, 10.0, 10.0],
                    "type": "caption",
                    "reading_order": 0,
                    "fts_score": 0.7,
                    "trigram_score": 0.2,
                    "hybrid_score": 0.5,
                }
            ],
            "context_segments": [],
            "stats": {
                "total_segments": 1,
                "matched_count": 1,
                "context_count": 0,
                "used_fallback": False,
            },
        }

        with (
            patch(
                "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.records.HybridRetrievalService.retrieve",
                return_value=retrieval_result,
            ) as mock_retrieve,
        ):
            response = await create_retrieval(
                uuid4(),
                RetrievalRequest(query="Hello world"),
                session,
                user,
            )

        assert response.strategy == "hybrid_chunks"
        assert response.stats.matched_count == 1
        assert response.matched_segments[0].text == "Hello world"
        mock_retrieve.assert_called_once()


# ── Sibling Fallback Tests ─────────────────────────


class TestGetKnowledgeSiblingFallback:
    """Tests for sibling fallback in get_knowledge."""

    @pytest.mark.asyncio
    async def test_returns_sibling_text_with_source_rid(self) -> None:
        """Record has no own text, but sibling exists."""
        sibling_uid = uuid4()
        sibling_text = SimpleNamespace(
            summary="Sibling summary",
            segments=[{"text": "Sibling text"}],
            named_entities=None,
            extraction_metadata={"semantic_indexed_version": 0},
        )
        record = SimpleNamespace(
            uid=uuid4(),
            title="Test",
            user_id=uuid4(),
            media_type=MediaType.document,
            extracted_text=None,  # No own text
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        with (
            patch(
                "app.api.v1.endpoints.records.ExtractedTextResolver.resolve",
                return_value=(sibling_text, sibling_uid),
            ),
            patch(
                "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
                return_value=True,
            ),
        ):
            response = await get_knowledge(uuid4(), session, user)

        assert response.extracted_text_source_record_id == sibling_uid
        assert response.summary == "Sibling summary"
        assert response.status.value == "indexed"
        assert response.cache_valid is True
        assert response.indexed_version == 0

    @pytest.mark.asyncio
    async def test_returns_none_when_no_sibling(self) -> None:
        """Record has no own text and no sibling."""
        record = SimpleNamespace(
            uid=uuid4(),
            title="Test",
            user_id=uuid4(),
            media_type=MediaType.document,
            extracted_text=None,
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        with patch(
            "app.api.v1.endpoints.records.ExtractedTextResolver.resolve",
            return_value=(None, None),
        ):
            response = await get_knowledge(uuid4(), session, user)

        assert response.extracted_text_source_record_id is None
        assert response.status.value == "no_text"

    @pytest.mark.asyncio
    async def test_sibling_without_semantic_data_returns_ready_for_indexing(
        self,
    ) -> None:
        """Sibling exists but has no summary or extraction_metadata."""
        sibling_uid = uuid4()
        sibling_text = SimpleNamespace(
            summary=None,
            segments=[{"text": "raw text"}],
            named_entities=None,
            extraction_metadata=None,
        )
        record = SimpleNamespace(
            uid=uuid4(),
            title="Test",
            user_id=uuid4(),
            media_type=MediaType.document,
            extracted_text=None,  # No own text
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        with (
            patch(
                "app.api.v1.endpoints.records.ExtractedTextResolver.resolve",
                return_value=(sibling_text, sibling_uid),
            ),
            patch(
                "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
                return_value=True,
            ),
        ):
            response = await get_knowledge(uuid4(), session, user)

        assert response.extracted_text_source_record_id == sibling_uid
        assert response.status.value == "ready_for_indexing"
        assert response.cache_valid is False

    @pytest.mark.asyncio
    async def test_sibling_summary_without_index_returns_ready_for_indexing(
        self,
    ) -> None:
        """Borrowed summary alone should not count as indexed."""
        sibling_uid = uuid4()
        sibling_text = SimpleNamespace(
            summary="Borrowed summary",
            segments=[{"text": "raw text"}],
            named_entities=None,
            extraction_metadata={"topics": ["topic"]},
        )
        record = SimpleNamespace(
            uid=uuid4(),
            title="Test",
            user_id=uuid4(),
            media_type=MediaType.document,
            extracted_text=None,
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        with (
            patch(
                "app.api.v1.endpoints.records.ExtractedTextResolver.resolve",
                return_value=(sibling_text, sibling_uid),
            ),
            patch(
                "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
                return_value=True,
            ),
        ):
            response = await get_knowledge(uuid4(), session, user)

        assert response.extracted_text_source_record_id == sibling_uid
        assert response.status.value == "ready_for_indexing"
        assert response.cache_valid is False
        assert response.indexed_version is None

    @pytest.mark.asyncio
    async def test_returns_none_when_own_text_exists(self) -> None:
        """Record has its own text — source_rid should be None."""
        own_et = SimpleNamespace(
            summary="Own summary",
            segments=[{"text": "Own text"}],
            named_entities=None,
            extraction_metadata={"semantic_indexed_version": 0},
        )
        record = SimpleNamespace(
            uid=uuid4(),
            title="Test",
            user_id=uuid4(),
            media_type=MediaType.document,
            extracted_text=own_et,
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        with patch(
            "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
            return_value=True,
        ):
            response = await get_knowledge(uuid4(), session, user)

        assert response.extracted_text_source_record_id is None
        assert response.summary == "Own summary"


class TestUpsertKnowledgeSiblingFallback:
    """Tests for copy-on-write in upsert_knowledge."""

    @pytest.mark.asyncio
    async def test_creates_new_text_when_borrowed(self) -> None:
        """Copy-on-write: create new ExtractedText when text is borrowed."""
        sibling_uid = uuid4()
        record_uid = uuid4()
        sibling_text = SimpleNamespace(
            record_id=sibling_uid,
            summary="",
            named_entities=None,
            extraction_metadata=None,
            confidence=0.95,
            language="hi",
            extraction_type="asr",
            quality_score=None,
            notes=None,
            model_name="whisper",
            processing_date=None,
            segments=[{"text": "sibling"}],
            dataset=None,
        )
        record = SimpleNamespace(
            uid=record_uid,
            user_id=uuid4(),
            media_type=MediaType.document,
            extracted_text=None,  # No own text
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        payload = KnowledgeUpdateRequest(
            extracted_text=ExtractedTextUpdateSchema(
                summary="New Summary",
                named_entities=[],
            ),
            extraction_metadata=ExtractionMetadataSchema(
                topics=["T1"],
                key_concepts=[],
                themes=["Theme1"],
                content_classification={},
            ),
        )

        with (
            patch(
                "app.api.v1.endpoints.records.ExtractedTextResolver.resolve",
                return_value=(sibling_text, sibling_uid),
            ),
            patch(
                "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.records.MetadataIndexer.validate_semantic_metadata",
                return_value={"topics": ["T1"]},
            ),
        ):
            response = await upsert_knowledge(
                record_uid, payload, session, user
            )

        assert response.status == "indexed"
        # Verify a new ExtractedText was added to session
        added_calls = [call[0][0] for call in session.add.call_args_list]
        new_et = next(
            (
                c
                for c in added_calls
                if hasattr(c, "record_id") and c.record_id == record_uid
            ),
            None,
        )
        assert new_et is not None, "Expected a new ExtractedText to be created"
        assert new_et.summary == "New Summary"

    @pytest.mark.asyncio
    async def test_no_copy_when_own_text_exists(self) -> None:
        """When record has own text, no copy-on-write needed."""
        extracted_text = Mock()
        extracted_text.summary = ""
        extracted_text.named_entities = None
        extracted_text.extraction_metadata = None
        extracted_text.updated_at = None

        record = SimpleNamespace(
            uid=uuid4(),
            user_id=uuid4(),
            media_type=MediaType.document,
            extracted_text=extracted_text,
            version_info=SimpleNamespace(current_version=0),
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        payload = KnowledgeUpdateRequest(
            extracted_text=ExtractedTextUpdateSchema(
                summary="Direct Summary",
                named_entities=[],
            ),
            extraction_metadata=ExtractionMetadataSchema(
                topics=["T1"],
                key_concepts=[],
                themes=["Theme1"],
                content_classification={},
            ),
        )

        with (
            patch(
                "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.records.MetadataIndexer.validate_semantic_metadata",
                return_value={"topics": ["T1"]},
            ),
        ):
            response = await upsert_knowledge(uuid4(), payload, session, user)

        assert response.status == "indexed"
        assert extracted_text.summary == "Direct Summary"


class TestCreateRetrievalSiblingFallback:
    """Tests for sibling fallback in create_retrieval."""

    @pytest.mark.asyncio
    async def test_queries_sibling_record_id(self) -> None:
        """Uses sibling's record_id for DB query when text is borrowed."""
        sibling_uid = uuid4()
        sibling_text = SimpleNamespace(
            summary="Sibling",
            segments=[{"text": "Sibling text"}],
        )
        record = SimpleNamespace(
            uid=uuid4(),
            user_id=uuid4(),
            media_type=MediaType.document,
            extracted_text=None,  # No own text
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        retrieval_result = {
            "strategy": "hybrid_jsonb",
            "matched_segments": [],
            "context_segments": [],
            "stats": {
                "total_segments": 0,
                "matched_count": 0,
                "context_count": 0,
                "used_fallback": False,
            },
        }

        with (
            patch(
                "app.api.v1.endpoints.records.ExtractedTextResolver.resolve",
                return_value=(sibling_text, sibling_uid),
            ),
            patch(
                "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.records.HybridRetrievalService.retrieve",
                return_value=retrieval_result,
            ) as mock_retrieve,
        ):
            await create_retrieval(
                uuid4(),
                RetrievalRequest(query="test"),
                session,
                user,
            )

        # Verify HybridRetrievalService was called with sibling's UID
        call_kwargs = mock_retrieve.call_args[1]
        assert call_kwargs["record_id"] == sibling_uid

    @pytest.mark.asyncio
    async def test_queries_own_record_id_when_own_text(self) -> None:
        """Uses own record_id for DB query when record has its own text."""
        own_et = SimpleNamespace(
            summary="Own",
            segments=[{"text": "Own text"}],
        )
        own_uid = uuid4()
        record = SimpleNamespace(
            uid=own_uid,
            user_id=uuid4(),
            media_type=MediaType.document,
            extracted_text=own_et,
        )
        session = Mock()
        session.get.return_value = record
        user = cast(User, SimpleNamespace(id=record.user_id))

        retrieval_result = {
            "strategy": "hybrid_jsonb",
            "matched_segments": [],
            "context_segments": [],
            "stats": {
                "total_segments": 0,
                "matched_count": 0,
                "context_count": 0,
                "used_fallback": False,
            },
        }

        with (
            patch(
                "app.api.v1.endpoints.records.TextNormalizer.has_meaningful_extracted_text",
                return_value=True,
            ),
            patch(
                "app.api.v1.endpoints.records.HybridRetrievalService.retrieve",
                return_value=retrieval_result,
            ) as mock_retrieve,
        ):
            await create_retrieval(
                uuid4(),
                RetrievalRequest(query="test"),
                session,
                user,
            )

        call_kwargs = mock_retrieve.call_args[1]
        assert call_kwargs["record_id"] == own_uid

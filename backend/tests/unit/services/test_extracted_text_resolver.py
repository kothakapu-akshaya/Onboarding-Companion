from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.auth import get_password_hash
from app.models.extracted_text import ExtractedText
from app.models.record import MediaType, Record
from app.models.user import User
from app.services.extracted_text_resolver import (
    ExtractedTextResolver,
    _best_from_rows,
    _group_by_hash,
    _priority_tuple,
    _query_siblings,
)


def make_text(**overrides):
    data = {
        "uid": overrides.get("uid", uuid4()),
        "record_id": overrides.get("record_id", uuid4()),
        "extraction_type": overrides.get("extraction_type", "asr"),
        "segments": overrides.get("segments", [{"text": "hello"}]),
        "confidence": overrides.get("confidence", 0.95),
        "language": overrides.get("language", "hi"),
        "quality_score": overrides.get("quality_score", None),
        "notes": overrides.get("notes", None),
        "summary": overrides.get("summary", None),
        "model_name": overrides.get("model_name", "whisper"),
        "processing_date": overrides.get("processing_date", None),
        "named_entities": overrides.get("named_entities", None),
        "extraction_metadata": overrides.get("extraction_metadata", None),
        "dataset": overrides.get("dataset", None),
        "skipped": overrides.get("skipped", False),
        "skip_reason": overrides.get("skip_reason", None),
        "edit": overrides.get("edit", None),
        "device_uid": overrides.get("device_uid", None),
        "created_at": overrides.get("created_at", datetime.now(timezone.utc)),
        "updated_at": overrides.get("updated_at", datetime.now(timezone.utc)),
    }
    return SimpleNamespace(**data)


def make_record(**overrides):
    data = {
        "uid": overrides.get("uid", uuid4()),
        "file_hash": overrides.get("file_hash", "abc123"),
        "extracted_text": overrides.get("extracted_text", None),
        "user_id": overrides.get("user_id", uuid4()),
    }
    return SimpleNamespace(**data)


def make_db_user(**overrides):
    suffix = uuid4().hex[:8]
    return User(
        phone=overrides.get("phone", f"90000{suffix[:5]}"),
        username=overrides.get("username", f"user_{suffix}"),
        name=overrides.get("name", "Resolver Test User"),
        email=overrides.get("email", f"{suffix}@example.com"),
        hashed_password=overrides.get(
            "hashed_password", get_password_hash("testpassword")
        ),
        gender=overrides.get("gender", None),
        date_of_birth=overrides.get("date_of_birth", date(1990, 1, 1)),
        current_place=overrides.get("current_place", "Hyderabad"),
        has_given_consent=overrides.get("has_given_consent", True),
    )


def make_db_record(user_id, **overrides):
    return Record(
        title=overrides.get("title", "Resolver test record"),
        description=overrides.get(
            "description",
            "This is a resolver test description long enough to pass.",
        ),
        media_type=overrides.get("media_type", MediaType.document),
        user_id=user_id,
        file_hash=overrides.get("file_hash", "hash-123"),
    )


class TestPriorityTuple:
    def test_prefers_asr_or_ocr(self):
        asr_text = make_text(
            extraction_type="asr",
            segments=[{"text": "hi"}],
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        manual_text = make_text(
            extraction_type="manual",
            segments=[{"text": "hi"}],
            created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        assert _priority_tuple(asr_text) > _priority_tuple(manual_text)

    def test_prefers_ocr_over_manual(self):
        ocr_text = make_text(
            extraction_type="ocr",
            segments=[{"text": "hi"}],
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        caption_text = make_text(
            extraction_type="caption",
            segments=[{"text": "hi"}],
            created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        assert _priority_tuple(ocr_text) > _priority_tuple(caption_text)

    def test_prefers_non_empty_segments(self):
        filled = make_text(
            extraction_type="manual",
            segments=[{"text": "hi"}],
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        empty = make_text(
            extraction_type="manual",
            segments=[],
            created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        assert _priority_tuple(filled) > _priority_tuple(empty)

    def test_prefers_non_null_segments(self):
        filled = make_text(
            extraction_type="manual",
            segments=[{"text": "hi"}],
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        null_text = make_text(
            extraction_type="manual",
            segments=None,
            created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        assert _priority_tuple(filled) > _priority_tuple(null_text)

    def test_tiebreaker_by_newest_created_at(self):
        older = make_text(
            extraction_type="asr",
            segments=[{"text": "hi"}],
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        newer = make_text(
            extraction_type="asr",
            segments=[{"text": "hi"}],
            created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        assert _priority_tuple(newer) > _priority_tuple(older)


class TestBestFromRows:
    def test_returns_best_by_priority(self):
        uid1, uid2 = uuid4(), uuid4()
        rows = [
            (
                make_text(
                    extraction_type="manual",
                    segments=[],
                    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                ),
                uid1,
                "hash1",
            ),
            (
                make_text(
                    extraction_type="asr",
                    segments=[{"text": "hi"}],
                    created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
                ),
                uid2,
                "hash1",
            ),
        ]
        best_et, best_rid = _best_from_rows(rows)
        assert best_rid == uid2

    def test_returns_first_when_tied(self):
        uid = uuid4()
        rows = [
            (
                make_text(
                    extraction_type="asr",
                    segments=[{"text": "a"}],
                    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                ),
                uid,
                "hash1",
            ),
            (
                make_text(
                    extraction_type="asr",
                    segments=[{"text": "b"}],
                    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                ),
                uuid4(),
                "hash1",
            ),
        ]
        best_et, best_rid = _best_from_rows(rows)
        assert best_rid == uid


class TestGroupByHash:
    def test_groups_correctly(self):
        owner_a = uuid4()
        owner_b = uuid4()
        rows = [
            (make_text(), uuid4(), "hash_a", owner_a),
            (make_text(), uuid4(), "hash_b", owner_a),
            (make_text(), uuid4(), "hash_a", owner_b),
        ]
        groups = _group_by_hash(rows)
        assert len(groups[("hash_a", owner_a)]) == 1
        assert len(groups[("hash_b", owner_a)]) == 1
        assert len(groups[("hash_a", owner_b)]) == 1

    def test_empty_input(self):
        assert _group_by_hash([]) == {}


class TestQuerySiblings:
    def test_calls_session_with_pairs(self):
        session = MagicMock()
        uid = uuid4()
        owner_id = uuid4()
        session.exec.return_value.all.return_value = []

        result = _query_siblings([uid], [("abc123", owner_id)], session)

        assert result == []
        session.exec.assert_called_once()

    def test_includes_skipped_filter_in_query(self):
        session = MagicMock()
        session.exec.return_value.all.return_value = []

        _query_siblings([uuid4()], [("abc123", uuid4())], session)

        query = session.exec.call_args[0][0]
        compiled = str(
            query.compile(compile_kwargs={"literal_binds": True})
        ).lower()
        assert "coalesce" in compiled
        assert "skipped" in compiled


class TestExtractedTextResolver:
    def test_resolve_returns_own_text(self):
        et = make_text()
        record = make_record(extracted_text=et)
        session = MagicMock()

        result_et, source_rid = ExtractedTextResolver.resolve(record, session)

        assert result_et == et
        assert source_rid is None

    def test_resolve_falls_back_to_sibling(self):
        session = MagicMock()
        owner_id = uuid4()
        sibling_uid = uuid4()
        sibling_et = make_text(
            extraction_type="asr", segments=[{"text": "hello"}]
        )
        session.exec.return_value.all.return_value = [
            (sibling_et, sibling_uid, "abc123", owner_id),
        ]

        record = make_record(
            uid=uuid4(),
            file_hash="abc123",
            extracted_text=None,
            user_id=owner_id,
        )
        result_et, source_rid = ExtractedTextResolver.resolve(record, session)

        assert result_et == sibling_et
        assert source_rid == sibling_uid

    def test_resolve_returns_none_when_no_sibling(self):
        session = MagicMock()
        session.exec.return_value.all.return_value = []

        record = make_record(
            uid=uuid4(), file_hash="abc123", extracted_text=None
        )
        result_et, source_rid = ExtractedTextResolver.resolve(record, session)

        assert result_et is None
        assert source_rid is None

    def test_resolve_returns_none_when_no_file_hash(self):
        record = make_record(file_hash=None, extracted_text=None)
        session = MagicMock()

        result_et, source_rid = ExtractedTextResolver.resolve(record, session)

        assert result_et is None
        assert source_rid is None
        session.exec.assert_not_called()

    def test_resolve_prioritizes_asr_over_manual(self):
        session = MagicMock()
        owner_id = uuid4()
        sibling_uid = uuid4()
        asr_et = make_text(
            extraction_type="asr",
            segments=[{"text": "asr"}],
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        manual_et = make_text(
            extraction_type="manual",
            segments=[{"text": "manual"}],
            created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        session.exec.return_value.all.return_value = [
            (asr_et, sibling_uid, "abc123", owner_id),
            (manual_et, uuid4(), "abc123", owner_id),
        ]

        record = make_record(
            uid=uuid4(),
            file_hash="abc123",
            extracted_text=None,
            user_id=owner_id,
        )
        result_et, source_rid = ExtractedTextResolver.resolve(record, session)

        assert result_et.extraction_type == "asr"

    def test_resolve_returns_none_without_owner(self):
        record = make_record(user_id=None, extracted_text=None)
        session = MagicMock()

        result_et, source_rid = ExtractedTextResolver.resolve(record, session)

        assert result_et is None
        assert source_rid is None
        session.exec.assert_not_called()

    def test_batch_resolve_returns_map(self):
        session = MagicMock()
        uid1, uid2 = uuid4(), uuid4()
        owner_id = uuid4()
        sibling_uid = uuid4()
        sibling_et = make_text(segments=[{"text": "fallback"}])

        session.exec.return_value.all.return_value = [
            (sibling_et, sibling_uid, "abc123", owner_id),
        ]

        records = [
            make_record(
                uid=uid1,
                file_hash="abc123",
                extracted_text=None,
                user_id=owner_id,
            ),
            make_record(
                uid=uid2,
                file_hash="abc123",
                extracted_text=None,
                user_id=owner_id,
            ),
        ]

        result = ExtractedTextResolver.batch_resolve(records, session)

        assert uid1 in result
        assert uid2 in result
        et, rid = result[uid1]
        assert rid == sibling_uid

    def test_batch_resolve_does_not_cross_users(self):
        session = MagicMock()
        owner_a = uuid4()
        owner_b = uuid4()
        uid_a, uid_b = uuid4(), uuid4()
        sibling_a_uid = uuid4()
        sibling_b_uid = uuid4()
        session.exec.return_value.all.return_value = [
            (
                make_text(segments=[{"text": "a"}]),
                sibling_a_uid,
                "abc123",
                owner_a,
            ),
            (
                make_text(segments=[{"text": "b"}]),
                sibling_b_uid,
                "abc123",
                owner_b,
            ),
        ]

        records = [
            make_record(
                uid=uid_a,
                file_hash="abc123",
                extracted_text=None,
                user_id=owner_a,
            ),
            make_record(
                uid=uid_b,
                file_hash="abc123",
                extracted_text=None,
                user_id=owner_b,
            ),
        ]

        result = ExtractedTextResolver.batch_resolve(records, session)

        assert result[uid_a][1] == sibling_a_uid
        assert result[uid_b][1] == sibling_b_uid

    def test_batch_resolve_skips_records_with_own_text(self):
        records = [
            make_record(
                uid=uuid4(), file_hash="abc123", extracted_text=make_text()
            ),
        ]
        session = MagicMock()

        result = ExtractedTextResolver.batch_resolve(records, session)

        assert result == {}
        session.exec.assert_not_called()

    def test_batch_resolve_skips_records_without_hash(self):
        records = [
            make_record(uid=uuid4(), file_hash=None, extracted_text=None),
        ]
        session = MagicMock()

        result = ExtractedTextResolver.batch_resolve(records, session)

        assert result == {}
        session.exec.assert_not_called()

    def test_batch_resolve_empty_input(self):
        result = ExtractedTextResolver.batch_resolve([], MagicMock())

        assert result == {}

    def test_batch_resolve_uses_exact_pairs_no_cross_product(self):
        """When two records share a hash but have different owners.

        batch should only match exact (hash, owner) pairs.
        """
        session = MagicMock()
        owner_a = uuid4()
        owner_b = uuid4()
        uid_a = uuid4()
        uid_b = uuid4()

        sibling_a = make_text(segments=[{"text": "for_a"}])
        sibling_b = make_text(segments=[{"text": "for_b"}])
        session.exec.return_value.all.return_value = [
            (sibling_a, uuid4(), "shared_hash", owner_a),
            (sibling_b, uuid4(), "shared_hash", owner_b),
        ]

        records = [
            make_record(
                uid=uid_a,
                file_hash="shared_hash",
                extracted_text=None,
                user_id=owner_a,
            ),
            make_record(
                uid=uid_b,
                file_hash="shared_hash",
                extracted_text=None,
                user_id=owner_b,
            ),
        ]

        ExtractedTextResolver.batch_resolve(records, session)

        query = session.exec.call_args[0][0]
        compiled = str(
            query.compile(compile_kwargs={"literal_binds": True})
        ).lower()
        assert "file_hash, user_id" in compiled.replace("record.", "")

        result = ExtractedTextResolver.batch_resolve(records, session)

        assert result[uid_a][1] != result[uid_b][1]
        assert result[uid_a][0].segments[0]["text"] == "for_a"
        assert result[uid_b][0].segments[0]["text"] == "for_b"


class TestCopyToRecord:
    def test_copies_all_fields(self):
        source = make_text(
            extraction_type="asr",
            segments=[{"text": "hello"}],
            named_entities=[{"entity": "test"}],
            extraction_metadata={"key": "val"},
            dataset="test_dataset",
            confidence=0.9,
            language="en",
            quality_score=0.8,
            notes="test notes",
            summary="test summary",
            model_name="test_model",
            processing_date="2024-01-01",
        )
        new_record_id = uuid4()

        cloned = ExtractedTextResolver.copy_to_record(source, new_record_id)

        assert cloned.record_id == new_record_id
        assert cloned.confidence == source.confidence
        assert cloned.language == source.language
        assert cloned.extraction_type == source.extraction_type
        assert cloned.quality_score == source.quality_score
        assert cloned.notes == source.notes
        assert cloned.summary == source.summary
        assert cloned.model_name == source.model_name
        assert cloned.processing_date == source.processing_date
        assert cloned.dataset == source.dataset
        assert cloned.uid is None or cloned.uid != source.uid
        assert (
            cloned.created_at is None or cloned.created_at != source.created_at
        )
        assert (
            cloned.updated_at is None or cloned.updated_at != source.updated_at
        )

    def test_deep_copies_json_fields(self):
        segments = [{"text": "original"}]
        named_entities = [{"entity": "original"}]
        metadata = {"nested": {"key": "original"}}
        source = make_text(
            segments=segments,
            named_entities=named_entities,
            extraction_metadata=metadata,
        )

        cloned = ExtractedTextResolver.copy_to_record(source, uuid4())

        assert cloned.segments == segments
        assert cloned.named_entities == named_entities
        assert cloned.extraction_metadata == metadata

        cloned.segments[0]["text"] = "mutated"
        cloned.named_entities[0]["entity"] = "mutated"
        cloned.extraction_metadata["nested"]["key"] = "mutated"

        assert source.segments[0]["text"] == "original"
        assert source.named_entities[0]["entity"] == "original"
        assert source.extraction_metadata["nested"]["key"] == "original"


@pytest.mark.database
class TestExtractedTextResolverDatabase:
    def test_resolve_excludes_skipped_siblings_with_real_data(self, session):
        owner = make_db_user()
        session.add(owner)
        session.commit()

        target = make_db_record(owner.id, file_hash="shared-hash-db")
        skipped_record = make_db_record(
            owner.id,
            file_hash="shared-hash-db",
            title="Skipped sibling",
        )
        active_record = make_db_record(
            owner.id,
            file_hash="shared-hash-db",
            title="Active sibling",
        )
        session.add(target)
        session.add(skipped_record)
        session.add(active_record)
        session.commit()

        skipped_text = ExtractedText(
            record_id=skipped_record.uid,
            extraction_type="asr",
            segments=[{"text": "skip me"}],
            skipped=True,
            skip_reason="duplicate",
        )
        active_text = ExtractedText(
            record_id=active_record.uid,
            extraction_type="asr",
            segments=[{"text": "use me"}],
            skipped=False,
        )
        session.add(skipped_text)
        session.add(active_text)
        session.commit()
        session.refresh(target)

        resolved, source_rid = ExtractedTextResolver.resolve(target, session)

        assert resolved is not None
        assert source_rid == active_record.uid
        assert resolved.record_id == active_record.uid
        assert resolved.segments[0]["text"] == "use me"
        assert resolved.skipped is False

    def test_resolve_returns_none_when_only_skipped_siblings(self, session):
        owner = make_db_user()
        session.add(owner)
        session.commit()

        target = make_db_record(owner.id, file_hash="only-skipped-hash")
        skipped_record = make_db_record(
            owner.id,
            file_hash="only-skipped-hash",
            title="Only skipped sibling",
        )
        session.add(target)
        session.add(skipped_record)
        session.commit()

        skipped_text = ExtractedText(
            record_id=skipped_record.uid,
            extraction_type="asr",
            segments=[{"text": "skip me"}],
            skipped=True,
            skip_reason="duplicate",
        )
        session.add(skipped_text)
        session.commit()
        session.refresh(target)

        resolved, source_rid = ExtractedTextResolver.resolve(target, session)

        assert resolved is None
        assert source_rid is None

"""Tests for the hashtag/tagging feature in records."""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.records import (
    get_records,
    patch_record,
    suggest_tags,
)
from app.schemas import MediaType, ReleaseRights


class DummyModel(SimpleNamespace):
    def model_dump(self, *args, **kwargs):
        return dict(self.__dict__)


def result_rows(*rows):
    return SimpleNamespace(
        all=lambda: list(rows), first=lambda: rows[0] if rows else None
    )


def make_record(**overrides):
    from datetime import datetime, timezone

    data = {
        "uid": overrides.get("uid", uuid4()),
        "user_id": overrides.get("user_id", uuid4()),
        "username": overrides.get("username", "recorder"),
        "category_ids": overrides.get("category_ids", [uuid4()]),
        "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2024, 1, 2, tzinfo=timezone.utc),
        "title": overrides.get("title", "Test record title"),
        "description": overrides.get(
            "description", "A descriptive enough record body for validation."
        ),
        "media_type": overrides.get("media_type", MediaType.audio),
        "file_url": overrides.get(
            "file_url", "https://storage.example.com/obj.mp3"
        ),
        "file_name": overrides.get("file_name", "obj.mp3"),
        "file_size": overrides.get("file_size", 1024),
        "status": overrides.get("status", "uploaded"),
        "location": overrides.get("location", None),
        "reviewed": overrides.get("reviewed", False),
        "reviewed_by": overrides.get("reviewed_by", None),
        "reviewed_at": overrides.get("reviewed_at", None),
        "release_rights": overrides.get(
            "release_rights", ReleaseRights.creator
        ),
        "creator": overrides.get("creator", "Recorder"),
        "language": overrides.get("language", "hindi"),
        "published_date": overrides.get("published_date", None),
        "source_label": overrides.get("source_label", None),
        "source_url": overrides.get("source_url", None),
        "duration_seconds": overrides.get("duration_seconds", 12),
        "extracted_text": overrides.get("extracted_text", None),
        "hashtags": overrides.get("hashtags", None),
        "tagged_usernames": overrides.get("tagged_usernames", None),
        "record_tags": overrides.get("record_tags", None),
    }
    return DummyModel(**data)


# ---------------------------------------------------------------------------
# Test 1: hashtags / tagged_usernames persisted on get_records response
# ---------------------------------------------------------------------------


def test_get_records_returns_hashtags_and_tagged_usernames(
    mock_session, endpoint_user
):
    record = make_record(hashtags=["python"], tagged_usernames=["alice"])
    mock_session.exec.return_value = result_rows(record)
    mock_session.get.return_value = DummyModel(username="recorder")

    records = get_records(
        session=mock_session,
        current_user=endpoint_user,
        skip=0,
        limit=10,
    )
    assert records[0]["hashtags"] == ["python"]
    assert records[0]["tagged_usernames"] == ["alice"]


# ---------------------------------------------------------------------------
# Test 2: PATCH preserves hashtags / tagged_usernames
# ---------------------------------------------------------------------------


def test_patch_record_preserves_hashtags_and_tagged_usernames(
    mock_session, endpoint_user
):
    record = make_record(hashtags=["ml"], tagged_usernames=["bob"])
    record.__fields__ = {
        k: None for k in record.__dict__ if not k.startswith("_")
    }
    mock_session.get.return_value = record

    update = DummyModel()
    update.model_dump = lambda exclude_unset=False: {
        "title": "Updated Title Two"
    }

    with (
        patch(
            "app.api.v1.endpoints.records.validate_with_enhanced_errors"
        ) as mock_val,
        patch("app.api.v1.endpoints.records.RecordHistoryService"),
        patch("app.api.v1.endpoints.records.award_for_edit"),
    ):
        mock_val.return_value = DummyModel(
            model_dump=lambda exclude_unset=False: {
                "title": "Updated Title Two"
            }
        )
        patch_record(
            record_id=record.uid,
            record_data=update,
            session=mock_session,
            current_user=endpoint_user,
        )

    # Original tag fields untouched
    assert record.hashtags == ["ml"]
    assert record.tagged_usernames == ["bob"]


# ---------------------------------------------------------------------------
# Test 3: GET /records filtered by hashtag
# ---------------------------------------------------------------------------


def test_get_records_filters_by_hashtag(mock_session, endpoint_user):
    record = make_record(hashtags=["nlp"])
    mock_session.exec.return_value = result_rows(record)
    mock_session.get.return_value = DummyModel(username="recorder")

    records = get_records(
        session=mock_session,
        hashtag="nlp",
        current_user=endpoint_user,
        skip=0,
        limit=10,
    )
    assert len(records) == 1


# ---------------------------------------------------------------------------
# Test 4: GET /records filtered by tagged_username
# ---------------------------------------------------------------------------


def test_get_records_filters_by_tagged_username(mock_session, endpoint_user):
    record = make_record(tagged_usernames=["carol"])
    mock_session.exec.return_value = result_rows(record)
    mock_session.get.return_value = DummyModel(username="recorder")

    records = get_records(
        session=mock_session,
        tagged_username="carol",
        current_user=endpoint_user,
        skip=0,
        limit=10,
    )
    assert len(records) == 1


# ---------------------------------------------------------------------------
# Test 5: suggest_tags returns expected hashtag and user suggestions
# ---------------------------------------------------------------------------


def test_suggest_tags_returns_hashtags_users_and_record_tags(
    mock_session, endpoint_user
):
    # First exec call: user search; second: hashtags; third: record_tags
    call_count = {"n": 0}

    def exec_side_effect(query, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return SimpleNamespace(all=lambda: ["alice"])
        if call_count["n"] == 2:
            return SimpleNamespace(all=lambda: [("algorithms",), ("algebra",)])
        return SimpleNamespace(all=lambda: [("internal",)])

    mock_session.exec.side_effect = exec_side_effect

    result = suggest_tags(
        session=mock_session,
        query="al",
        limit=10,
        current_user=endpoint_user,
    )

    assert any(u["username"] == "alice" for u in result["users"])
    assert any(h["tag"] == "algorithms" for h in result["hashtags"])
    assert any(t["tag"] == "internal" for t in result["record_tags"])


# ---------------------------------------------------------------------------
# Test 6: PATCH record_tags as non-admin → 403
# ---------------------------------------------------------------------------


def test_patch_record_record_tags_non_admin_succeeds(
    mock_session, endpoint_user
):
    record = make_record()
    record.__fields__ = {
        k: None for k in record.__dict__ if not k.startswith("_")
    }
    mock_session.get.return_value = record

    tag_uid = str(uuid4())

    update = DummyModel()
    update.model_dump = lambda exclude_unset=False: {"record_tags": [tag_uid]}

    with (
        patch(
            "app.api.v1.endpoints.records.validate_with_enhanced_errors"
        ) as mock_val,
        patch("app.api.v1.endpoints.records.RecordHistoryService"),
        patch("app.api.v1.endpoints.records.award_for_edit"),
    ):
        mock_val.return_value = DummyModel(
            model_dump=lambda exclude_unset=False: {"record_tags": [tag_uid]}
        )
        patch_record(
            record_id=record.uid,
            record_data=update,
            session=mock_session,
            current_user=endpoint_user,
        )

    assert record.record_tags == [tag_uid]


# ---------------------------------------------------------------------------
# Test 7: PATCH record_tags as admin → succeeds
# ---------------------------------------------------------------------------


def test_patch_record_record_tags_admin_succeeds(mock_session, endpoint_user):
    record = make_record()
    record.__fields__ = {
        k: None for k in record.__dict__ if not k.startswith("_")
    }
    mock_session.get.return_value = record

    tag_uid = str(uuid4())

    update = DummyModel()
    update.model_dump = lambda exclude_unset=False: {"record_tags": [tag_uid]}

    with (
        patch(
            "app.api.v1.endpoints.records.validate_with_enhanced_errors"
        ) as mock_val,
        patch("app.api.v1.endpoints.records.RecordHistoryService"),
        patch("app.api.v1.endpoints.records.award_for_edit"),
    ):
        mock_val.return_value = DummyModel(
            model_dump=lambda exclude_unset=False: {"record_tags": [tag_uid]}
        )
        patch_record(
            record_id=record.uid,
            record_data=update,
            session=mock_session,
            current_user=endpoint_user,
        )

    assert record.record_tags == [tag_uid]


def test_patch_record_rejects_review_fields(mock_session, endpoint_user):
    record = make_record()
    record.__fields__ = {
        k: None for k in record.__dict__ if not k.startswith("_")
    }
    mock_session.get.return_value = record

    update = DummyModel()
    update.model_dump = lambda exclude_unset=False: {
        "reviewed": True,
        "reviewed_by": endpoint_user.id,
    }

    with pytest.raises(HTTPException) as exc_info:
        patch_record(
            record_id=record.uid,
            record_data=update,
            session=mock_session,
            current_user=endpoint_user,
        )

    assert exc_info.value.status_code == 400
    assert "Review state fields are server-managed" in exc_info.value.detail


def test_patch_record_rejects_review_fields_for_admins_too(
    mock_session, endpoint_user
):
    record = make_record()
    record.__fields__ = {
        k: None for k in record.__dict__ if not k.startswith("_")
    }
    mock_session.get.return_value = record

    update = DummyModel()
    update.model_dump = lambda exclude_unset=False: {"reviewed_at": "now"}

    with pytest.raises(HTTPException) as exc_info:
        patch_record(
            record_id=record.uid,
            record_data=update,
            session=mock_session,
            current_user=endpoint_user,
        )

    assert exc_info.value.status_code == 400
    assert "Review state fields are server-managed" in exc_info.value.detail


def test_validate_record_tags_rejects_non_uuid(mock_session):
    from app.api.v1.endpoints.records import _validate_record_tags

    with pytest.raises(HTTPException) as exc_info:
        _validate_record_tags(["not-a-uuid"], mock_session)
    assert exc_info.value.status_code == 400
    assert "not a valid UUID" in exc_info.value.detail


def test_validate_record_tags_rejects_nonexistent_record(mock_session):
    from app.api.v1.endpoints.records import _validate_record_tags

    mock_session.get.return_value = None
    tag_uid = str(uuid4())

    with pytest.raises(HTTPException) as exc_info:
        _validate_record_tags([tag_uid], mock_session)
    assert exc_info.value.status_code == 400
    assert "Record not found" in exc_info.value.detail


def test_validate_record_tags_accepts_existing_records(mock_session):
    from app.api.v1.endpoints.records import _validate_record_tags

    mock_session.get.return_value = DummyModel()
    tag_1 = str(uuid4())
    tag_2 = str(uuid4())

    _validate_record_tags([tag_1, tag_2], mock_session)


def test_patch_record_rejects_invalid_record_tag_uuid(
    mock_session, endpoint_user
):
    record = make_record()
    record.__fields__ = {
        k: None for k in record.__dict__ if not k.startswith("_")
    }
    mock_session.get.return_value = record

    update = DummyModel()
    update.model_dump = lambda exclude_unset=False: {
        "record_tags": ["not-a-uuid"]
    }

    with (
        patch(
            "app.api.v1.endpoints.records.validate_with_enhanced_errors"
        ) as mock_val,
        patch("app.api.v1.endpoints.records.RecordHistoryService"),
    ):
        mock_val.return_value = DummyModel(
            model_dump=lambda exclude_unset=False: {
                "record_tags": ["not-a-uuid"]
            }
        )
        with pytest.raises(HTTPException) as exc_info:
            patch_record(
                record_id=record.uid,
                record_data=update,
                session=mock_session,
                current_user=endpoint_user,
            )

    assert exc_info.value.status_code == 400
    assert "not a valid UUID" in exc_info.value.detail


def test_validate_tagged_usernames_rejects_nonexistent_user(mock_session):
    from app.api.v1.endpoints.records import _validate_tagged_usernames

    mock_session.exec.return_value = SimpleNamespace(first=lambda: None)

    with pytest.raises(HTTPException) as exc_info:
        _validate_tagged_usernames(["nonexistent_user"], mock_session)
    assert exc_info.value.status_code == 400
    assert "User not found" in exc_info.value.detail


def test_validate_tagged_usernames_accepts_existing_users(mock_session):
    from app.api.v1.endpoints.records import _validate_tagged_usernames

    mock_session.exec.return_value = SimpleNamespace(first=lambda: DummyModel())

    _validate_tagged_usernames(["alice", "bob"], mock_session)


def test_patch_record_rejects_nonexistent_tagged_username(
    mock_session, endpoint_user
):
    record = make_record()
    record.__fields__ = {
        k: None for k in record.__dict__ if not k.startswith("_")
    }
    mock_session.get.return_value = record
    mock_session.exec.return_value = SimpleNamespace(first=lambda: None)

    update = DummyModel()
    update.model_dump = lambda exclude_unset=False: {
        "tagged_usernames": ["nobody"]
    }

    with (
        patch(
            "app.api.v1.endpoints.records.validate_with_enhanced_errors"
        ) as mock_val,
        patch("app.api.v1.endpoints.records.RecordHistoryService"),
    ):
        mock_val.return_value = DummyModel(
            model_dump=lambda exclude_unset=False: {
                "tagged_usernames": ["nobody"]
            }
        )
        with pytest.raises(HTTPException) as exc_info:
            patch_record(
                record_id=record.uid,
                record_data=update,
                session=mock_session,
                current_user=endpoint_user,
            )

    assert exc_info.value.status_code == 400
    assert "User not found" in exc_info.value.detail


def test_patch_record_rejects_nonexistent_record_tag(
    mock_session, endpoint_user
):
    record = make_record()
    record.__fields__ = {
        k: None for k in record.__dict__ if not k.startswith("_")
    }

    tag_uid = str(uuid4())
    get_calls = {"n": 0}

    def get_side_effect(model, uid):
        get_calls["n"] += 1
        if get_calls["n"] == 1:
            return record  # first call: fetch the record being patched
        return None  # subsequent calls: tag UUID lookups return None

    mock_session.get.side_effect = get_side_effect

    update = DummyModel()
    update.model_dump = lambda exclude_unset=False: {"record_tags": [tag_uid]}

    with (
        patch(
            "app.api.v1.endpoints.records.validate_with_enhanced_errors"
        ) as mock_val,
        patch("app.api.v1.endpoints.records.RecordHistoryService"),
    ):
        mock_val.return_value = DummyModel(
            model_dump=lambda exclude_unset=False: {"record_tags": [tag_uid]}
        )
        with pytest.raises(HTTPException) as exc_info:
            patch_record(
                record_id=record.uid,
                record_data=update,
                session=mock_session,
                current_user=endpoint_user,
            )

    assert exc_info.value.status_code == 400
    assert "Record not found" in exc_info.value.detail

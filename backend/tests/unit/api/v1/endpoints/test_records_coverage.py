from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.records import (
    get_next_records_for_review,
    get_records,
    get_records_with_distances,
    is_forbidden_filetype,
    resolve_device_uid,
    save_ai_extracted_text,
    search_records,
    search_records_in_bbox,
    search_records_nearby,
    update_extracted_text,
)
from app.schemas import (
    ExtractedTextCreate,
    ExtractedTextType,
    ExtractedTextUpdate,
    MediaType,
    RecordReviewFilters,
    RecordReviewRequest,
    ReleaseRights,
)


class DummyModel(SimpleNamespace):
    def model_dump(self, *args, **kwargs):
        return dict(self.__dict__)


def result_rows(*rows):
    return SimpleNamespace(
        all=lambda: list(rows), first=lambda: rows[0] if rows else None
    )


def make_record(**overrides):
    data = {
        "uid": overrides.get("uid", uuid4()),
        "user_id": overrides.get("user_id", uuid4()),
        "username": overrides.get("username", "recorder"),
        "category_ids": overrides.get("category_ids", [uuid4()]),
        "created_at": overrides.get(
            "created_at", datetime(2024, 1, 1, tzinfo=timezone.utc)
        ),
        "updated_at": overrides.get(
            "updated_at", datetime(2024, 1, 2, tzinfo=timezone.utc)
        ),
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
    }
    return DummyModel(**data)


def test_is_forbidden_filetype():
    with patch(
        "app.api.v1.endpoints.records.magic.from_file",
        return_value="application/zip",
        create=True,
    ):
        assert is_forbidden_filetype("/tmp/archive.zip") is True

    with patch(
        "app.api.v1.endpoints.records.magic.from_file",
        return_value="audio/mpeg",
        create=True,
    ):
        assert is_forbidden_filetype("/tmp/file.mp3") is False


def test_resolve_device_uid_returns_none_without_device_id(mock_session):
    assert resolve_device_uid(mock_session, uuid4(), None) is None
    mock_session.exec.assert_not_called()


def test_resolve_device_uid_raises_for_unknown_device(mock_session):
    mock_session.exec.return_value = result_rows()

    with pytest.raises(HTTPException) as exc_info:
        resolve_device_uid(mock_session, uuid4(), "unknown-device")

    assert exc_info.value.status_code == 400


def test_resolve_device_uid_returns_device_uid(mock_session):
    device = DummyModel(uid=uuid4(), last_seen_at=None, updated_at=None)
    link = DummyModel(uid=uuid4(), last_seen_at=None)
    mock_session.exec.return_value = result_rows((device, link))

    result = resolve_device_uid(mock_session, uuid4(), "device-123")

    assert result == device.uid
    assert device.last_seen_at is not None
    assert device.updated_at is not None
    assert link.last_seen_at is not None
    mock_session.add.assert_any_call(device)
    mock_session.add.assert_any_call(link)


def test_get_records_and_search_records(mock_session, endpoint_user):
    record = make_record(location={"dummy": True})
    mock_session.exec.return_value = result_rows(record)
    mock_session.get.return_value = DummyModel(username="recorder")

    with patch(
        "app.api.v1.endpoints.records.extract_coordinates_from_geometry",
        return_value=(78.5, 17.5),
    ):
        records = get_records(
            session=mock_session,
            user_id=record.user_id,
            media_type=MediaType.audio,
            current_user=endpoint_user,
            skip=0,
            limit=10,
        )

    assert records[0]["location"]["latitude"] == 17.5
    assert records[0]["username"] == "recorder"

    mock_session.exec.return_value = result_rows(record.uid)
    search = search_records(mock_session, "record", 5, endpoint_user)
    assert search[0]["record_id"] == str(record.uid)


def test_get_records_category_filter_raises_type_error(
    mock_session, endpoint_user
):
    with pytest.raises(TypeError):
        get_records(
            session=mock_session,
            category_id=uuid4(),
            current_user=endpoint_user,
        )


def make_user(**overrides):
    data = {
        "id": overrides.get("id", uuid4()),
        "credits": overrides.get("credits", 0.0),
    }
    return DummyModel(**data)


def make_extracted_text_record(**overrides):
    """Helper to create a record-like dummy for extracted text endpoints."""
    data = {
        "uid": overrides.get("uid", uuid4()),
        "media_type": overrides.get("media_type", MediaType.audio),
        "duration_seconds": overrides.get("duration_seconds", 120),
        "updated_at": datetime.now(timezone.utc),
    }
    return DummyModel(**data)


class TestSaveAiExtractedTextCredits:
    """Unit tests for credit awarding in save_ai_extracted_text (POST)."""

    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_awards_credits_for_audio(
        self, mock_claim, mock_history, mock_session, endpoint_user
    ):
        record = make_extracted_text_record(
            media_type=MediaType.audio, duration_seconds=120
        )
        user = make_user(credits=10.0)
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows()

        save_ai_extracted_text(
            record_id=record.uid,
            extracted_text=ExtractedTextCreate(
                language="hi",
                segments=[{"text": "test"}],
                model_name="whisper",
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            current_user=endpoint_user,
        )

        assert user.credits == 130.0

    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_awards_credits_for_video(
        self, mock_claim, mock_history, mock_session, endpoint_user
    ):
        record = make_extracted_text_record(
            media_type=MediaType.video, duration_seconds=60
        )
        user = make_user(credits=0.0)
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows()

        save_ai_extracted_text(
            record_id=record.uid,
            extracted_text=ExtractedTextCreate(
                language="hi",
                segments=[{"text": "test"}],
                model_name="whisper",
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            current_user=endpoint_user,
        )

        assert user.credits == 60.0

    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_no_credits_for_text(
        self, mock_claim, mock_history, mock_session, endpoint_user
    ):
        record = make_extracted_text_record(
            media_type=MediaType.text, duration_seconds=120
        )
        user = make_user(credits=5.0)
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows()

        save_ai_extracted_text(
            record_id=record.uid,
            extracted_text=ExtractedTextCreate(
                language="hi",
                segments=[{"text": "test"}],
                model_name="whisper",
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            current_user=endpoint_user,
        )

        assert user.credits == 5.0

    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_no_credits_when_duration_none(
        self, mock_claim, mock_history, mock_session, endpoint_user
    ):
        record = make_extracted_text_record(
            media_type=MediaType.audio, duration_seconds=None
        )
        user = make_user(credits=5.0)
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows()

        save_ai_extracted_text(
            record_id=record.uid,
            extracted_text=ExtractedTextCreate(
                language="hi",
                segments=[{"text": "test"}],
                model_name="whisper",
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            current_user=endpoint_user,
        )

        assert user.credits == 5.0


class TestSaveAiExtractedTextDevice:
    """Unit tests for device association in save_ai_extracted_text (POST)."""

    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_associates_compute_device(
        self, mock_claim, mock_history, mock_session, endpoint_user
    ):
        record = make_extracted_text_record(
            media_type=MediaType.audio, duration_seconds=120
        )
        user = make_user(credits=0.0)
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        device = DummyModel(uid=uuid4(), last_seen_at=None, updated_at=None)
        link = DummyModel(uid=uuid4(), last_seen_at=None)
        # First exec: existing-extraction lookup (none found).
        # Second exec: device lookup.
        mock_session.exec.side_effect = [
            result_rows(),
            result_rows((device, link)),
        ]

        save_ai_extracted_text(
            record_id=record.uid,
            extracted_text=ExtractedTextCreate(
                language="hi",
                segments=[{"text": "test"}],
                model_name="whisper",
                extraction_type=ExtractedTextType.asr,
                device_id="device-123",
            ),
            session=mock_session,
            current_user=endpoint_user,
        )

        added_extraction = mock_session.add.call_args_list[2][0][0]
        assert added_extraction.device_uid == device.uid

    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_unknown_compute_device_rejected(
        self, mock_claim, mock_history, mock_session, endpoint_user
    ):
        record = make_extracted_text_record(
            media_type=MediaType.audio, duration_seconds=120
        )
        user = make_user(credits=0.0)
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.side_effect = [result_rows(), result_rows()]

        with pytest.raises(HTTPException) as exc_info:
            save_ai_extracted_text(
                record_id=record.uid,
                extracted_text=ExtractedTextCreate(
                    language="hi",
                    segments=[{"text": "test"}],
                    model_name="whisper",
                    extraction_type=ExtractedTextType.asr,
                    device_id="unknown-device",
                ),
                session=mock_session,
                current_user=endpoint_user,
            )

        assert exc_info.value.status_code == 400


class TestUpdateExtractedTextCredits:
    """Unit tests for credit awarding in update_extracted_text (PATCH)."""

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_awards_credits_for_audio(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        record = make_extracted_text_record(
            media_type=MediaType.audio, duration_seconds=90
        )
        user = make_user(credits=30.0)
        existing_et = DummyModel(
            uid=uuid4(), record_id=record.uid, segments=[{"text": "old"}]
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(existing_et)
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 2
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[{"text": "corrected"}],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert user.credits == 120.0

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_no_credits_for_image(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        record = make_extracted_text_record(
            media_type=MediaType.image, duration_seconds=45
        )
        user = make_user(credits=10.0)
        existing_et = DummyModel(
            uid=uuid4(), record_id=record.uid, segments=[{"text": "old"}]
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(existing_et)
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 2
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[{"text": "corrected"}],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert user.credits == 10.0


class TestUpdateExtractedTextReviewState:
    """Unit tests for extracted text PATCH review-state behavior."""

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_preserves_existing_review_state_when_fully_proofread(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        existing_reviewer = uuid4()
        reviewed_at = datetime.now(timezone.utc)
        record = make_extracted_text_record()
        record.reviewed = True
        record.reviewed_by = existing_reviewer
        record.reviewed_at = reviewed_at
        user = make_user(credits=0.0)
        et_entry = DummyModel(
            uid=uuid4(),
            record_id=record.uid,
            segments=[{"text": "old", "proofread": False}],
            is_fully_proofread=False,
            updated_at=None,
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(et_entry)
        mock_history.return_value.capture_extracted_text_change.return_value = (
            DummyModel(uid=uuid4())
        )
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 2
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[{"text": "new", "proofread": True}],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert record.reviewed is True
        assert record.reviewed_by == existing_reviewer
        assert record.reviewed_at == reviewed_at
        assert et_entry.is_fully_proofread is True

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_does_not_clear_review_state_when_not_fully_proofread(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        existing_reviewer = uuid4()
        reviewed_at = datetime.now(timezone.utc)
        record = make_extracted_text_record()
        record.reviewed = True
        record.reviewed_by = existing_reviewer
        record.reviewed_at = reviewed_at
        user = make_user(credits=0.0)
        et_entry = DummyModel(
            uid=uuid4(),
            record_id=record.uid,
            segments=[{"text": "old", "proofread": True}],
            is_fully_proofread=True,
            updated_at=None,
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(et_entry)
        mock_history.return_value.capture_extracted_text_change.return_value = (
            DummyModel(uid=uuid4())
        )
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 3
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[{"text": "new", "proofread": False}],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert record.reviewed is True
        assert record.reviewed_by == existing_reviewer
        assert record.reviewed_at == reviewed_at
        assert et_entry.is_fully_proofread is False


class TestValidationStatusPreservation:
    """Tests for validated field preservation and is_fully_validated flag."""

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_preserves_existing_validated_when_not_in_incoming(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        record = make_extracted_text_record()
        user = make_user(credits=0.0)
        et_entry = DummyModel(
            uid=uuid4(),
            record_id=record.uid,
            segments=[
                {"text": "old1", "validated": True},
                {"text": "old2", "validated": False},
            ],
            is_fully_validated=False,
            updated_at=None,
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(et_entry)
        mock_history.return_value.capture_extracted_text_change.return_value = (
            DummyModel(uid=uuid4())
        )
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 2
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[
                    {"text": "new1", "validated": True},
                    {"text": "new2"},
                ],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert et_entry.segments[0]["validated"] is True
        assert et_entry.segments[1]["validated"] is False

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_new_segment_validated_defaults_to_false(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        record = make_extracted_text_record()
        user = make_user(credits=0.0)
        et_entry = DummyModel(
            uid=uuid4(),
            record_id=record.uid,
            segments=[{"text": "old", "validated": True}],
            is_fully_validated=True,
            updated_at=None,
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(et_entry)
        mock_history.return_value.capture_extracted_text_change.return_value = (
            DummyModel(uid=uuid4())
        )
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 2
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[
                    {"text": "new1", "validated": True},
                    {"text": "new2"},
                    {"text": "new3"},
                ],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert et_entry.segments[0]["validated"] is True
        assert et_entry.segments[1]["validated"] is False
        assert et_entry.segments[2]["validated"] is False

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_is_fully_validated_true_when_all_validated(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        record = make_extracted_text_record()
        user = make_user(credits=0.0)
        et_entry = DummyModel(
            uid=uuid4(),
            record_id=record.uid,
            segments=[{"text": "old", "validated": False}],
            is_fully_validated=False,
            updated_at=None,
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(et_entry)
        mock_history.return_value.capture_extracted_text_change.return_value = (
            DummyModel(uid=uuid4())
        )
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 2
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[{"text": "new", "validated": True}],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert et_entry.is_fully_validated is True

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_is_fully_validated_false_when_not_all_validated(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        record = make_extracted_text_record()
        user = make_user(credits=0.0)
        et_entry = DummyModel(
            uid=uuid4(),
            record_id=record.uid,
            segments=[{"text": "old", "validated": True}],
            is_fully_validated=True,
            updated_at=None,
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(et_entry)
        mock_history.return_value.capture_extracted_text_change.return_value = (
            DummyModel(uid=uuid4())
        )
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 3
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[{"text": "new", "validated": False}],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert et_entry.is_fully_validated is False

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_is_fully_validated_false_with_skipped_segments(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        record = make_extracted_text_record()
        user = make_user(credits=0.0)
        et_entry = DummyModel(
            uid=uuid4(),
            record_id=record.uid,
            segments=[{"text": "old", "validated": False}],
            is_fully_validated=False,
            updated_at=None,
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(et_entry)
        mock_history.return_value.capture_extracted_text_change.return_value = (
            DummyModel(uid=uuid4())
        )
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 2
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[
                    {"text": "new1", "validated": True},
                    {"text": "new2", "skipped": True},
                ],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert et_entry.is_fully_validated is False

    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_incoming_validated_overrides_existing(
        self, mock_claim, mock_history, mock_award, mock_session, endpoint_user
    ):
        record = make_extracted_text_record()
        user = make_user(credits=0.0)
        et_entry = DummyModel(
            uid=uuid4(),
            record_id=record.uid,
            segments=[{"text": "old", "validated": False}],
            is_fully_validated=False,
            updated_at=None,
        )
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.return_value = result_rows(et_entry)
        mock_history.return_value.capture_extracted_text_change.return_value = (
            DummyModel(uid=uuid4())
        )
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 2
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[{"text": "new", "validated": True}],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        assert et_entry.segments[0]["validated"] is True
        assert et_entry.is_fully_validated is True


def test_get_next_record_for_review_model_name_filter(
    mock_session, endpoint_user
):
    record_id = uuid4()
    mock_session.exec.return_value = result_rows(
        SimpleNamespace(uid=record_id, priority_level=1)
    )

    whisper_request = RecordReviewRequest(
        filters=RecordReviewFilters(model_name="whisper"),
        limit=10,
    )
    result = get_next_records_for_review(
        request=whisper_request,
        session=mock_session,
        current_user=endpoint_user,
    )
    assert result.record_ids == [{"record_id": str(record_id)}]


def test_get_next_record_for_review_combined_filters(
    mock_session, endpoint_user
):
    record_id = uuid4()
    mock_session.exec.return_value = result_rows(
        SimpleNamespace(uid=record_id, priority_level=1)
    )

    combined_request = RecordReviewRequest(
        filters=RecordReviewFilters(
            is_fully_proofread=False,
            extraction_type=ExtractedTextType.asr,
            model_name="whisper",
            language=["hindi"],
            media_type=[MediaType.audio],
        ),
        limit=20,
    )
    result = get_next_records_for_review(
        request=combined_request,
        session=mock_session,
        current_user=endpoint_user,
    )
    assert result.record_ids == [{"record_id": str(record_id)}]


def test_get_next_record_for_review_is_fully_validated_filter(
    mock_session, endpoint_user
):
    record_id = uuid4()
    mock_session.exec.return_value = result_rows(
        SimpleNamespace(uid=record_id, priority_level=1)
    )

    request = RecordReviewRequest(
        filters=RecordReviewFilters(is_fully_validated=True),
        limit=10,
    )
    result = get_next_records_for_review(
        request=request,
        session=mock_session,
        current_user=endpoint_user,
    )
    assert result.record_ids == [{"record_id": str(record_id)}]


def test_get_next_record_for_review_version_initial(
    mock_session, endpoint_user
):
    record_id = uuid4()
    mock_session.exec.return_value = result_rows(
        SimpleNamespace(uid=record_id, priority_level=1)
    )

    initial_request = RecordReviewRequest(
        filters=RecordReviewFilters(version="initial"),
        limit=10,
    )
    result = get_next_records_for_review(
        request=initial_request,
        session=mock_session,
        current_user=endpoint_user,
    )
    assert result.record_ids == [{"record_id": str(record_id)}]


def test_get_next_record_for_review_version_latest(mock_session, endpoint_user):
    record_id = uuid4()
    mock_session.exec.return_value = result_rows(
        SimpleNamespace(uid=record_id, priority_level=1)
    )

    latest_request = RecordReviewRequest(
        filters=RecordReviewFilters(version="latest"),
        limit=10,
    )
    result = get_next_records_for_review(
        request=latest_request,
        session=mock_session,
        current_user=endpoint_user,
    )
    assert result.record_ids == [{"record_id": str(record_id)}]


class TestUpdateExtractedTextCopyOnWrite:
    """Tests for copy-on-write behaviour in update_extracted_text."""

    @patch("app.api.v1.endpoints.records.ExtractedTextResolver")
    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_creates_new_text_when_borrowed_from_sibling(
        self,
        mock_claim,
        mock_history,
        mock_award,
        mock_resolver,
        mock_session,
        endpoint_user,
    ):
        record = make_extracted_text_record(
            media_type=MediaType.audio, duration_seconds=90
        )
        user = make_user(credits=10.0)
        sibling_uid = uuid4()
        sibling_et = DummyModel(
            uid=uuid4(),
            record_id=sibling_uid,
            segments=[{"text": "sibling text"}],
            confidence=0.95,
            language="hi",
            extraction_type="asr",
            quality_score=None,
            notes=None,
            summary=None,
            model_name="whisper",
            processing_date=None,
            named_entities=None,
            extraction_metadata=None,
            dataset=None,
        )
        # No existing et_entry for this record -> triggers copy-on-write
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        # First exec: et_entry lookup returns None
        # Second exec: ExtractedTextResolver.resolve returns sibling text
        mock_session.exec.side_effect = [
            result_rows(),  # no existing ExtractedText
        ]
        mock_resolver.resolve.return_value = (sibling_et, sibling_uid)
        mock_resolver.copy_to_record.return_value = DummyModel(
            record_id=record.uid,
            segments=None,
            confidence=None,
            language=None,
            extraction_type=None,
            quality_score=None,
            notes=None,
            summary=None,
            model_name=None,
            processing_date=None,
            named_entities=None,
            extraction_metadata=None,
            dataset=None,
        )
        mock_history.return_value.get_version_summary.return_value = {
            "current_version": 2
        }

        update_extracted_text(
            record_id=record.uid,
            corrected_text=ExtractedTextUpdate(
                segments=[{"text": "corrected"}],
                extraction_type=ExtractedTextType.asr,
            ),
            session=mock_session,
            expected_version=None,
            current_user=endpoint_user,
        )

        # Verify copy_to_record was called with the sibling text
        mock_resolver.copy_to_record.assert_called_once_with(
            sibling_et, record.uid
        )

        # Verify a new ExtractedText was created from sibling data
        added_calls = [call[0][0] for call in mock_session.add.call_args_list]
        new_et = next(
            (
                c
                for c in added_calls
                if hasattr(c, "record_id") and c.record_id == record.uid
            ),
            None,
        )
        assert new_et is not None, "Expected a new ExtractedText to be created"
        assert new_et.segments[0]["text"] == "corrected"

    @patch("app.api.v1.endpoints.records.ExtractedTextResolver")
    @patch("app.api.v1.endpoints.records.award_for_edit")
    @patch("app.api.v1.endpoints.records.RecordHistoryService")
    @patch("app.api.v1.endpoints.records.ClaimService")
    def test_raises_when_no_sibling_found(
        self,
        mock_claim,
        mock_history,
        mock_award,
        mock_resolver,
        mock_session,
        endpoint_user,
    ):
        record = make_extracted_text_record(
            media_type=MediaType.audio, duration_seconds=90
        )
        user = make_user(credits=10.0)
        mock_session.get.side_effect = lambda model, id: (
            record if model.__name__ == "Record" else user
        )
        mock_session.exec.side_effect = [
            result_rows(),  # no existing ExtractedText
        ]
        mock_resolver.resolve.return_value = (None, None)

        with pytest.raises(HTTPException) as exc_info:
            update_extracted_text(
                record_id=record.uid,
                corrected_text=ExtractedTextUpdate(
                    segments=[{"text": "corrected"}],
                    extraction_type=ExtractedTextType.asr,
                ),
                session=mock_session,
                expected_version=None,
                current_user=endpoint_user,
            )

        assert exc_info.value.status_code == 400


class TestSpatialEndpointsBatchResolve:
    """Verify spatial endpoints use batch_resolve."""

    @patch("app.api.v1.endpoints.records.RecordRead.model_validate")
    @patch("app.api.v1.endpoints.records.ExtractedTextResolver.batch_resolve")
    @patch("app.api.v1.endpoints.records.extract_coordinates_from_geometry")
    def test_search_records_nearby_uses_batch(
        self,
        mock_coords,
        mock_batch,
        mock_validate,
        mock_session,
        endpoint_user,
    ):
        mock_coords.return_value = (78.5, 17.5)
        mock_validate.return_value = DummyModel()
        mock_session.get.return_value = endpoint_user
        mock_session.exec.return_value = result_rows(make_record(location=None))
        mock_batch.return_value = {}

        search_records_nearby(
            session=mock_session,
            latitude=17.5,
            longitude=78.5,
            distance_meters=1000,
            current_user=endpoint_user,
            skip=0,
            limit=10,
        )

        mock_batch.assert_called_once()

    @patch("app.api.v1.endpoints.records.RecordRead.model_validate")
    @patch("app.api.v1.endpoints.records.ExtractedTextResolver.batch_resolve")
    @patch("app.api.v1.endpoints.records.extract_coordinates_from_geometry")
    def test_search_records_in_bbox_uses_batch(
        self,
        mock_coords,
        mock_batch,
        mock_validate,
        mock_session,
        endpoint_user,
    ):
        mock_coords.return_value = (78.5, 17.5)
        mock_validate.return_value = DummyModel()
        mock_session.get.return_value = endpoint_user
        mock_session.exec.return_value = result_rows(make_record(location=None))
        mock_batch.return_value = {}

        search_records_in_bbox(
            session=mock_session,
            min_lat=17.0,
            min_lng=78.0,
            max_lat=18.0,
            max_lng=79.0,
            current_user=endpoint_user,
            skip=0,
            limit=10,
        )

        mock_batch.assert_called_once()

    @patch("app.api.v1.endpoints.records.RecordRead.model_validate")
    @patch("app.api.v1.endpoints.records.ExtractedTextResolver.batch_resolve")
    def test_get_records_with_distances_uses_batch(
        self,
        mock_batch,
        mock_validate,
        mock_session,
        endpoint_user,
    ):
        record = make_record(location=None)
        mock_validate.return_value = DummyModel()
        mock_session.get.return_value = endpoint_user
        mock_session.exec.return_value = result_rows((record, 100.0))
        mock_batch.return_value = {}

        get_records_with_distances(
            session=mock_session,
            latitude=17.5,
            longitude=78.5,
            current_user=endpoint_user,
            skip=0,
            limit=50,
        )

        mock_batch.assert_called_once()

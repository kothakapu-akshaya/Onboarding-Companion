"""Tests for event endpoint behavior."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.events import (
    _serialize_review_filters,
    get_current_event,
)
from app.schemas import MediaType, RecordReviewFilters, ReleaseRights
from app.schemas.extracted_text import ExtractedTextType
from tests.unit.api.v1.endpoints.conftest import DummyModel, result_rows


def make_event(**overrides):
    now = datetime.now(timezone.utc)
    event = DummyModel(
        uid=uuid4(),
        name="Sample Event",
        description="Sample description",
        page_context="doc_digitization",
        filters=None,
        limit=20,
        is_active=True,
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=1),
        created_by=uuid4(),
        created_at=now,
        updated_at=now,
    )
    for key, value in overrides.items():
        setattr(event, key, value)
    return event


def test_current_event_returns_none_without_header(mock_session, endpoint_user):
    assert get_current_event(mock_session, None, endpoint_user) is None
    mock_session.exec.assert_not_called()


def test_current_event_returns_matching_active_event(
    mock_session, endpoint_user
):
    event = make_event()
    mock_session.exec.return_value = result_rows(event)

    result = get_current_event(
        session=mock_session,
        x_page_route="doc_digitization",
        current_user=endpoint_user,
    )

    assert result["uid"] == str(event.uid)
    assert result["page_context"] == "doc_digitization"


def test_current_event_returns_none_for_out_of_window_event(
    mock_session, endpoint_user
):
    future_event = make_event(
        start_date=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    mock_session.exec.return_value = result_rows(future_event)

    result = get_current_event(
        session=mock_session,
        x_page_route="doc_digitization",
        current_user=endpoint_user,
    )

    assert result is None


def test_current_event_returns_none_for_expired_event(
    mock_session, endpoint_user
):
    expired_event = make_event(
        end_date=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    mock_session.exec.return_value = result_rows(expired_event)

    result = get_current_event(
        session=mock_session,
        x_page_route="doc_digitization",
        current_user=endpoint_user,
    )

    assert result is None


def test_current_event_raises_conflict_for_duplicate_active_matches(
    mock_session, endpoint_user
):
    event_one = make_event()
    event_two = make_event(uid=uuid4(), name="Another Event")
    mock_session.exec.return_value = result_rows(event_one, event_two)

    with pytest.raises(HTTPException) as exc_info:
        get_current_event(
            session=mock_session,
            x_page_route="doc_digitization",
            current_user=endpoint_user,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == (
        "Multiple active events found for this page context"
    )


def test_serialize_review_filters_converts_json_unsafe_values():
    filters = RecordReviewFilters(
        language=["Telugu"],
        media_type=[MediaType.document],
        category_ids=[uuid4()],
        source_label="kathanilayam",
        release_rights=ReleaseRights.creator,
        published_date=datetime(2026, 5, 22, tzinfo=timezone.utc).date(),
        is_fully_proofread=False,
        extraction_type=ExtractedTextType.ocr,
        model_name="surya",
        is_fully_validated=True,
        version="initial",
    )

    serialized = _serialize_review_filters(filters)

    assert serialized is not None
    assert serialized["language"] == ["Telugu"]
    assert serialized["media_type"] == ["document"]
    assert serialized["category_ids"] == [str(filters.category_ids[0])]
    assert serialized["release_rights"] == "creator"
    assert serialized["published_date"] == "2026-05-22"
    assert serialized["extraction_type"] == "ocr"
    assert serialized["is_fully_proofread"] is False
    assert serialized["is_fully_validated"] is True
    assert serialized["model_name"] == "surya"
    assert serialized["version"] == "initial"

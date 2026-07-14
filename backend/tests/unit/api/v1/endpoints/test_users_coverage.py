from datetime import date, datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.users import (
    _has_populated_extracted_text,
    get_user,
    get_user_by_identifier,
    get_user_contributions,
    get_users,
    search_users,
    update_user,
)
from app.core.exceptions import DuplicateEntry, UserNotFound
from app.models.record_history import ChangeSource
from app.schemas import FieldPrivacy, Gender, MediaType, UserUpdate
from tests.unit.api.v1.endpoints.conftest import DummyModel, result_rows


def make_user(**overrides):
    user = DummyModel()
    user.id = overrides.get("id", uuid4())
    user.username = overrides.get("username", "test_user")
    user.name = overrides.get("name", "Test User")
    user.email = overrides.get("email", "test@example.com")
    user.gender = overrides.get("gender", Gender.male)
    user.date_of_birth = overrides.get("date_of_birth", date(1990, 1, 1))
    user.current_place = overrides.get("current_place", "Hyderabad")
    user.phone = overrides.get("phone", "+919876543210")
    user.profile_picture_path = None
    user.short_bio = None
    user.profession = overrides.get("profession")
    user.organisation = overrides.get("organisation")
    user.places_lived = None
    user.from_place = None
    user.social_media_profiles = None
    user.language_proficiencies = None
    user.is_active = True
    user.has_given_consent = True
    user.phone_privacy = FieldPrivacy.public
    user.email_privacy = FieldPrivacy.public
    user.last_login_at = None
    user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    user.updated_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
    user.profile_complete = True
    user.credits = overrides.get("credits", 0.0)
    return user


def make_record(**overrides):
    return DummyModel(
        uid=overrides.get("uid", uuid4()),
        user_id=overrides.get("user_id", uuid4()),
        media_type=overrides.get("media_type", MediaType.audio),
        duration_seconds=overrides.get("duration_seconds", 0),
        page_count=overrides.get("page_count", None),
        reviewed=overrides.get("reviewed", False),
        reviewed_by=overrides.get("reviewed_by", None),
        title=overrides.get("title", "Record"),
        description=overrides.get("description", "Description"),
        file_size=overrides.get("file_size", 100),
        category_ids=overrides.get("category_ids", []),
        created_at=overrides.get(
            "created_at", datetime(2024, 1, 1, tzinfo=timezone.utc)
        ),
        location=overrides.get("location", None),
        release_rights=overrides.get("release_rights", "NA"),
        language=overrides.get("language", "NA"),
        file_hash=overrides.get("file_hash", None),
        snr_frequency=overrides.get("snr_frequency", None),
        tagged_usernames=overrides.get("tagged_usernames", None),
        hashtags=overrides.get("hashtags", None),
        record_tags=overrides.get("record_tags", None),
        extracted_text=overrides.get("extracted_text", None),
    )


def make_history(**overrides):
    return DummyModel(
        record_id=overrides.get("record_id", uuid4()),
        changed_by=overrides.get("changed_by", uuid4()),
        change_source=overrides.get("change_source", ChangeSource.user_edit),
        field_changes=overrides.get(
            "field_changes",
            {"extracted_text": {"old": "before", "new": "after"}},
        ),
    )


def test_has_populated_extracted_text_accepts_json_string_and_dict():
    assert (
        _has_populated_extracted_text('{"segments": [{"text": "before"}]}')
        is True
    )
    assert (
        _has_populated_extracted_text({"segments": [{"text": "before"}]})
        is True
    )


def test_has_populated_extracted_text_ignores_timing_only_segments():
    assert (
        _has_populated_extracted_text(
            {"segments": [{"start": 0.0, "end": 1.5}]}
        )
        is False
    )


@pytest.mark.asyncio
async def test_get_users_applies_filters_and_fallback_name(
    mock_session, endpoint_user
):
    target = make_user(
        name="",
        phone="+919876543210",
        profession="archivist",
        organisation="Corpus Org",
    )
    mock_session.exec.return_value = result_rows(target)
    mock_session.get.return_value = make_user(username="recorder")

    with (
        patch(
            "app.api.v1.endpoints.users.get_user_roles", return_value=["admin"]
        ),
        patch(
            "app.api.v1.endpoints.users.filter_user_privacy",
            side_effect=lambda data, *_: data,
        ),
    ):
        result = await get_users(
            session=mock_session,
            current_user=endpoint_user,
            skip=0,
            limit=10,
            profession="arch",
            organisation="Org",
            user_id=uuid4(),
        )

    assert result[0].name == "User 3210"
    assert result[0].profession == "archivist"
    assert result[0].organisation == "Corpus Org"


def test_search_users_returns_usernames(mock_session, endpoint_user):
    mock_session.exec.return_value = result_rows("alice", "bob")

    result = search_users(mock_session, "ali", 5, endpoint_user)

    assert result == [{"username": "alice"}, {"username": "bob"}]


@pytest.mark.asyncio
async def test_get_user_populates_role_for_self(mock_session, endpoint_user):
    target = make_user(id=endpoint_user.id)
    with (
        patch(
            "app.api.v1.endpoints.users.get_user_by_identifier",
            return_value=target,
        ),
        patch(
            "app.api.v1.endpoints.users.get_user_roles",
            return_value=["reviewer", "user"],
        ),
        patch(
            "app.api.v1.endpoints.users.filter_user_privacy",
            side_effect=lambda data, *_: data,
        ),
    ):
        result = await get_user(mock_session, target.username, endpoint_user)

    assert result.username == target.username
    assert result.role == "reviewer"
    assert result.roles == ["reviewer", "user"]

    mock_session.exec.return_value = result_rows()
    with pytest.raises(UserNotFound):
        get_user_by_identifier(mock_session, "does-not-exist")


@pytest.mark.asyncio
async def test_get_user_populates_role_for_admin(mock_session, endpoint_user):
    target = make_user()
    with (
        patch(
            "app.api.v1.endpoints.users.get_user_by_identifier",
            return_value=target,
        ),
        patch(
            "app.api.v1.endpoints.users.get_user_roles",
            return_value=["admin"],
        ),
        patch(
            "app.api.v1.endpoints.users.filter_user_privacy",
            side_effect=lambda data, *_: data,
        ),
    ):
        result = await get_user(mock_session, target.username, endpoint_user)

    assert result.role == "admin"
    assert result.roles == ["admin"]


@pytest.mark.asyncio
async def test_get_user_hides_role_for_third_party(mock_session, endpoint_user):
    target = make_user()
    with (
        patch(
            "app.api.v1.endpoints.users.get_user_by_identifier",
            return_value=target,
        ),
        patch(
            "app.api.v1.endpoints.users.get_user_roles",
            return_value=["user"],
        ),
        patch(
            "app.api.v1.endpoints.users.filter_user_privacy",
            side_effect=lambda data, *_: data,
        ),
    ):
        result = await get_user(mock_session, target.username, endpoint_user)

    assert result.role is None
    assert result.roles == []


@pytest.mark.asyncio
async def test_update_user_success(mock_session, endpoint_user):
    target = make_user(id=endpoint_user.id)
    user_update = UserUpdate(name="Updated Name")

    with (
        patch(
            "app.api.v1.endpoints.users.get_user_by_identifier",
            return_value=target,
        ),
        patch(
            "app.api.v1.endpoints.users.get_user_roles", return_value=["user"]
        ),
    ):
        result = await update_user(
            session=mock_session,
            user_identifier=str(target.id),
            user_update=user_update,
            current_user=endpoint_user,
        )

    assert result.name == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_duplicate_email(mock_session, endpoint_user):
    target = make_user(id=endpoint_user.id)
    existing_email = make_user(email="existing@example.com")
    mock_session.exec.return_value = result_rows(existing_email)

    with (
        patch(
            "app.api.v1.endpoints.users.get_user_by_identifier",
            return_value=target,
        ),
        patch(
            "app.api.v1.endpoints.users.get_user_roles", return_value=["user"]
        ),
    ):
        with pytest.raises(DuplicateEntry):
            await update_user(
                session=mock_session,
                user_identifier=str(target.id),
                user_update=UserUpdate(email="existing@example.com"),
                current_user=endpoint_user,
            )


@pytest.mark.asyncio
async def test_update_user_forbidden(mock_session, endpoint_user):
    target = make_user()

    with (
        patch(
            "app.api.v1.endpoints.users.get_user_by_identifier",
            return_value=target,
        ),
        patch("app.api.v1.endpoints.users.get_user_roles", return_value=[]),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                session=mock_session,
                user_identifier=str(target.id),
                user_update=UserUpdate(name="Updated Name"),
                current_user=endpoint_user,
            )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_update_user_rejects_unknown_language_proficiencies(
    mock_session, endpoint_user
):
    target = make_user(id=endpoint_user.id)
    user_update = UserUpdate(
        language_proficiencies={
            "proficiencies": [{"language": "made-up", "proficiency": "basic"}]
        }
    )

    with (
        patch(
            "app.api.v1.endpoints.users.get_user_by_identifier",
            return_value=target,
        ),
        patch(
            "app.api.v1.endpoints.users.get_user_roles",
            return_value=["user"],
        ),
        patch(
            "app.api.v1.endpoints.users.LanguageService.validate_language_proficiencies",
            side_effect=ValueError("Unsupported language: made-up"),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                session=mock_session,
                user_identifier=str(target.id),
                user_update=user_update,
                current_user=endpoint_user,
            )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_user_contributions_counts_history_based_edit_and_review_stats(  # noqa: E501
    mock_session, endpoint_user
):
    target = make_user(id=endpoint_user.id, credits=12.5)
    uploaded_audio = make_record(
        user_id=target.id, media_type=MediaType.audio, duration_seconds=30
    )
    uploaded_document = make_record(
        user_id=target.id, media_type=MediaType.document, page_count=4
    )
    edited_audio = make_record(media_type=MediaType.audio, duration_seconds=45)
    reviewed_document = make_record(media_type=MediaType.document, page_count=7)
    ignored_text = make_record(media_type=MediaType.text)

    mock_session.scalars.side_effect = [
        result_rows(uploaded_audio, uploaded_document),
        result_rows(edited_audio, reviewed_document, ignored_text),
    ]
    mock_session.exec.side_effect = [
        result_rows(
            make_history(
                changed_by=target.id,
                record_id=edited_audio.uid,
                field_changes={"title": {"old": "A", "new": "B"}},
            ),
            make_history(
                changed_by=target.id,
                record_id=reviewed_document.uid,
                field_changes={
                    "extracted_text": {
                        "old": {"segments": [{"text": "old"}]},
                        "new": {"segments": [{"text": "new"}]},
                    }
                },
            ),
            make_history(
                changed_by=target.id,
                record_id=ignored_text.uid,
                field_changes={
                    "extracted_text": {
                        "old": None,
                        "new": {"segments": [{"text": "fresh"}]},
                    }
                },
            ),
        ),
    ]

    with patch(
        "app.api.v1.endpoints.users.get_user_by_identifier",
        return_value=target,
    ):
        result = await get_user_contributions(
            user_identifier=str(target.id),
            session=mock_session,
            current_user=endpoint_user,
        )

    assert result.audio_duration == 30
    assert result.document_pages == 4
    assert result.compute_audio_count == 0
    assert result.compute_audio_duration == 0
    assert result.compute_document_count == 1
    assert result.compute_text_count == 1
    assert result.edit_audio_count == 1
    assert result.edit_document_count == 0
    assert result.edit_text_count == 0
    assert result.review_audio_count == 0
    assert result.review_document_count == 1
    assert result.review_text_count == 0
    assert len(result.audio_contributions) == 1
    assert result.audio_contributions[0].id == uploaded_audio.uid
    assert len(result.document_contributions) == 1
    assert result.document_contributions[0].id == uploaded_document.uid
    assert result.video_contributions is None
    assert result.text_contributions is None
    assert result.image_contributions is None

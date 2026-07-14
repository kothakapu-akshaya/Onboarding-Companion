from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.languages import (
    LanguageRead,
    create_language,
    get_languages,
)


def _language_row(name: str, code: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        code=code,
        created_by=None,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )


def test_get_languages_returns_all_language_rows(mock_session, endpoint_user):
    rows = [_language_row("NA", "und"), _language_row("hindi", "hi")]

    with patch(
        "app.api.v1.endpoints.languages.LanguageService.get_all_languages",
        return_value=rows,
    ):
        result = get_languages(mock_session, endpoint_user)

    assert result == [
        LanguageRead(name="NA", code="und"),
        LanguageRead(name="hindi", code="hi"),
    ]


def test_create_language_success(mock_session, endpoint_user):
    created = _language_row("marwari", None)

    with patch(
        "app.api.v1.endpoints.languages.LanguageService.create_language",
        return_value=created,
    ):
        result = create_language(
            "Marwari",
            mock_session,
            endpoint_user,
            code=None,
        )

    assert result == LanguageRead(name="marwari", code=None)


def test_create_language_with_code(mock_session, endpoint_user):
    created = _language_row("marwari", "mwr")

    with patch(
        "app.api.v1.endpoints.languages.LanguageService.create_language",
        return_value=created,
    ):
        result = create_language(
            "Marwari",
            mock_session,
            endpoint_user,
            code="mwr",
        )

    assert result == LanguageRead(name="marwari", code="mwr")


def test_create_language_duplicate_returns_400(mock_session, endpoint_user):
    with patch(
        "app.api.v1.endpoints.languages.LanguageService.create_language",
        side_effect=ValueError("Language already exists"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            create_language(
                "Hindi",
                mock_session,
                endpoint_user,
                code=None,
            )

    assert exc_info.value.status_code == 400

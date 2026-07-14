from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.language import LanguageEntry
from app.schemas import LanguageProficiencies
from app.services.language_service import LanguageService


def _exec_result(*, all_rows=None, first_row=None):
    return SimpleNamespace(
        all=lambda: list(all_rows or []),
        first=lambda: first_row,
    )


def _language_entry(name: str, code: str | None = None):
    return LanguageEntry(id=uuid4(), name=name, code=code, created_by=uuid4())


def test_validate_language_exists_normalizes_input():
    session = MagicMock()
    session.exec.return_value = _exec_result(first_row=object())

    result = LanguageService.validate_language_exists(session, " Hindi ")

    assert result == "hindi"


def test_validate_language_exists_rejects_unknown_language():
    session = MagicMock()
    session.exec.return_value = _exec_result(first_row=None)

    with pytest.raises(ValueError, match="Unsupported language"):
        LanguageService.validate_language_exists(session, "unknown-language")


def test_create_language_rejects_duplicates():
    session = MagicMock()
    session.exec.return_value = _exec_result(first_row=object())

    with pytest.raises(ValueError, match="Language already exists"):
        LanguageService.create_language(session, "Hindi", created_by=uuid4())


def test_validate_language_proficiencies_accepts_dict_payload():
    session = MagicMock()
    session.exec.side_effect = [
        _exec_result(first_row=object()),
        _exec_result(first_row=object()),
    ]

    payload = LanguageProficiencies.model_validate(
        {
            "proficiencies": [
                {"language": " Hindi ", "proficiency": "basic"},
                {"language": "english", "proficiency": "proficient"},
            ]
        }
    ).model_dump()

    LanguageService.validate_language_proficiencies(session, payload)


def test_get_by_code_returns_entry_when_code_exists():
    session = MagicMock()
    entry = _language_entry("telugu", "te")
    session.exec.return_value = _exec_result(first_row=entry)

    result = LanguageService.get_by_code(session, "te")

    assert result is entry


def test_get_by_code_returns_none_when_code_does_not_exist():
    session = MagicMock()
    session.exec.return_value = _exec_result(first_row=None)

    result = LanguageService.get_by_code(session, "xyz")

    assert result is None


def test_get_by_code_is_case_insensitive():
    session = MagicMock()
    entry = _language_entry("telugu", "te")
    session.exec.return_value = _exec_result(first_row=entry)

    result = LanguageService.get_by_code(session, "TE")

    assert result is entry


def test_validate_language_code_returns_canonical_code():
    session = MagicMock()
    entry = _language_entry("telugu", "te")
    session.exec.return_value = _exec_result(first_row=entry)

    result = LanguageService.validate_language_code(session, "TE")

    assert result == "te"


def test_validate_language_code_raises_for_unknown_code():
    session = MagicMock()
    session.exec.return_value = _exec_result(first_row=None)

    with pytest.raises(ValueError, match="Unknown language code"):
        LanguageService.validate_language_code(session, "xyz")

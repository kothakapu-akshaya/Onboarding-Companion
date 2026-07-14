import pytest
from pydantic import ValidationError

from app.core.language_utils import (
    DEFAULT_LANGUAGE_NAMES,
    LANGUAGE_NOT_AVAILABLE,
    normalize_language_name,
)
from app.schemas import ReleaseRights
from app.schemas.geo_schemas import Coordinates
from app.schemas.upload_validation import ContentValidationBase

VALID_COORDINATES = Coordinates(latitude=17.385, longitude=78.4867)
VALID_DESCRIPTION = (
    "This is a long enough description with varied words "
    "and meaningful context."
)


def _content_data(language: str) -> dict:
    return {
        "title": "Village folklore recording",
        "description": VALID_DESCRIPTION,
        "language": language,
        "release_rights": ReleaseRights.creator,
        "location": VALID_COORDINATES,
    }


# BCP47 codes for the new languages in DEFAULT_LANGUAGE_NAMES
NEW_LANGUAGE_CODES = [
    "bhb",  # bhili
    "grt",  # garo
    "gon",  # gondi
    "hoc",  # ho
    "khn",  # khandeshi
    "kha",  # khasi
    "kru",  # kurukh
    "unr",  # mundari
    "tcy",  # tulu
]


class TestLanguageSchemas:
    def test_bcp47_codes_pass_through(self):
        """BCP47 codes pass through unchanged; schema only strips whitespace."""
        for code in NEW_LANGUAGE_CODES:
            model = ContentValidationBase(**_content_data(code))
            assert model.language == code

    def test_und_code_accepted(self):
        """'und' (undetermined) is the replacement for legacy 'NA'."""
        model = ContentValidationBase(**_content_data("und"))
        assert model.language == "und"

    @pytest.mark.parametrize(
        ("raw_language", "expected"),
        [
            (" te ", "te"),
            ("  hi  ", "hi"),
            ("und", "und"),
            (" en ", "en"),
        ],
    )
    def test_language_whitespace_is_stripped(
        self, raw_language: str, expected: str
    ):
        """Schema strips surrounding whitespace; no other normalization."""
        model = ContentValidationBase(**_content_data(raw_language))
        assert model.language == expected

    def test_language_is_required(self):
        data = _content_data("te")
        del data["language"]
        with pytest.raises(ValidationError, match="language"):
            ContentValidationBase(**data)

    def test_normalize_language_name_rejects_blank_values(self):
        with pytest.raises(ValueError, match="Language is required"):
            normalize_language_name("   ")

    def test_default_language_names_are_valid_strings(self):
        assert len(DEFAULT_LANGUAGE_NAMES) == 33
        for language in DEFAULT_LANGUAGE_NAMES:
            assert isinstance(language, str)
            if language == LANGUAGE_NOT_AVAILABLE:
                continue
            assert language == language.lower()

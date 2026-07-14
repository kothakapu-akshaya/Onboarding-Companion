"""Utilities for canonical language handling."""

LANGUAGE_NOT_AVAILABLE = "NA"
LANGUAGE_UNDETERMINED = "und"


DEFAULT_LANGUAGE_NAMES = [
    "assamese",
    "bengali",
    "bhili",
    "bodo",
    "dogri",
    "english",
    "garo",
    "gondi",
    "gujarati",
    "ho",
    "hindi",
    "kannada",
    "khandeshi",
    "kashmiri",
    "khasi",
    "konkani",
    "kurukh",
    "maithili",
    "malayalam",
    "marathi",
    "mundari",
    "meitei",
    "nepali",
    "odia",
    "punjabi",
    "sanskrit",
    "santali",
    "sindhi",
    "tamil",
    "telugu",
    "tulu",
    "urdu",
    LANGUAGE_NOT_AVAILABLE,
]

# BCP47 codes for every default language name.
# None means no widely accepted code exists for that variety.
DEFAULT_LANGUAGE_CODES: dict[str, str | None] = {
    "assamese": "as",
    "bengali": "bn",
    "bhili": "bhb",
    "bodo": "brx",
    "dogri": "doi",
    "english": "en",
    "garo": "grt",
    "gondi": "gon",
    "gujarati": "gu",
    "ho": "hoc",
    "hindi": "hi",
    "kannada": "kn",
    "khandeshi": "khn",
    "kashmiri": "ks",
    "khasi": "kha",
    "konkani": "kok",
    "kurukh": "kru",
    "maithili": "mai",
    "malayalam": "ml",
    "marathi": "mr",
    "mundari": "unr",
    "meitei": "mni",
    "nepali": "ne",
    "odia": "or",
    "punjabi": "pa",
    "sanskrit": "sa",
    "santali": "sat",
    "sindhi": "sd",
    "tamil": "ta",
    "telugu": "te",
    "tulu": "tcy",
    "urdu": "ur",
    LANGUAGE_NOT_AVAILABLE: LANGUAGE_UNDETERMINED,
}


def normalize_language_name(value: str) -> str:
    """Normalize language names to their canonical stored representation."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Language is required")

    lowered = cleaned.lower()
    if lowered == "na":
        return LANGUAGE_NOT_AVAILABLE
    return lowered

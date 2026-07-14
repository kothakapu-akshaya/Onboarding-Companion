"""Service helpers for dynamic language validation and lookup."""

from collections.abc import Iterable

from sqlalchemy import func
from sqlmodel import Session, select

from app.core.language_utils import (
    DEFAULT_LANGUAGE_CODES,
    DEFAULT_LANGUAGE_NAMES,
    normalize_language_name,
)
from app.models.language import LanguageEntry


class LanguageService:
    """Database-backed language registry helpers."""

    @staticmethod
    def ensure_default_languages(session: Session) -> None:
        """Seed the default language registry entries if they are missing."""
        existing = {
            name for name in session.exec(select(LanguageEntry.name)).all()
        }
        missing = [
            name for name in DEFAULT_LANGUAGE_NAMES if name not in existing
        ]
        for name in missing:
            session.add(
                LanguageEntry(name=name, code=DEFAULT_LANGUAGE_CODES.get(name))
            )

        # Back-fill codes on rows that predate the code column.
        entries_without_code = session.exec(
            select(LanguageEntry).where(LanguageEntry.code.is_(None))  # type: ignore[missing-attribute]
        ).all()
        for entry in entries_without_code:
            code = DEFAULT_LANGUAGE_CODES.get(entry.name)
            if code is not None:
                entry.code = code
                session.add(entry)

        session.commit()

    @staticmethod
    def get_all_languages(session: Session) -> list[LanguageEntry]:
        """Return all registered languages ordered by name."""
        query = select(LanguageEntry).order_by(LanguageEntry.name)
        return list(session.exec(query).all())

    @staticmethod
    def validate_language_exists(session: Session, language: str) -> str:
        """Normalize and verify that a language exists in the registry."""
        normalized = normalize_language_name(language)
        entry = session.exec(
            select(LanguageEntry).where(LanguageEntry.name == normalized)
        ).first()
        if not entry:
            raise ValueError(f"Unsupported language: {language}")
        return normalized

    @staticmethod
    def validate_languages_exist(
        session: Session, languages: Iterable[str]
    ) -> list[str]:
        """Normalize and verify multiple languages."""
        return [
            LanguageService.validate_language_exists(session, language)
            for language in languages
        ]

    @staticmethod
    def validate_language_proficiencies(
        session: Session, proficiencies
    ) -> None:
        """Validate language proficiency payloads against the registry."""
        if not proficiencies:
            return
        entries = (
            proficiencies.get("proficiencies", [])
            if isinstance(proficiencies, dict)
            else proficiencies.proficiencies
        )
        values = [
            entry["language"] if isinstance(entry, dict) else entry.language
            for entry in entries
        ]
        LanguageService.validate_languages_exist(session, values)

    @staticmethod
    def get_by_code(session: Session, code: str) -> LanguageEntry | None:
        """Return the LanguageEntry for a BCP47 code (case-insensitive)."""
        return session.exec(
            select(LanguageEntry).where(
                func.lower(LanguageEntry.code) == func.lower(code)
            )
        ).first()

    @staticmethod
    def validate_language_code(session: Session, code: str) -> str:
        """Verify that a BCP47 code is registered; return the canonical code."""
        entry = LanguageService.get_by_code(session, code)
        if not entry or entry.code is None:
            raise ValueError(
                f"Unknown language code '{code}'. "
                "Use a registered BCP47 code (see GET /api/v1/languages)."
            )
        return entry.code

    @staticmethod
    def create_language(
        session: Session,
        name: str,
        code: str | None = None,
        created_by=None,
    ) -> LanguageEntry:
        """Create a new normalized language entry."""
        normalized = normalize_language_name(name)
        existing = session.exec(
            select(LanguageEntry).where(LanguageEntry.name == normalized)
        ).first()
        if existing:
            raise ValueError("Language already exists")

        language = LanguageEntry(
            name=normalized, code=code, created_by=created_by
        )
        session.add(language)
        session.commit()
        session.refresh(language)
        return language

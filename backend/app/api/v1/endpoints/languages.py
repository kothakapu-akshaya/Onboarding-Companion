"""Language lookup and admin management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.language_utils import normalize_language_name
from app.core.rbac_fastapi import require_admin, require_any_role
from app.db.session import SessionDep
from app.models.user import User
from app.services.language_service import LanguageService

router = APIRouter()


class LanguageRead(BaseModel):
    """Language registry entry with its BCP47 code."""

    name: str
    code: str | None


@router.get("", response_model=list[LanguageRead])
def get_languages(
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> list[LanguageRead]:
    """Return all registered languages with their BCP47 codes."""
    languages = LanguageService.get_all_languages(session)
    return [LanguageRead(name=lang.name, code=lang.code) for lang in languages]


@router.post("", response_model=LanguageRead, status_code=201)
def create_language(
    name: Annotated[
        str,
        Query(
            ...,
            min_length=1,
            max_length=100,
            description="Language name",
        ),
    ],
    session: SessionDep,
    current_user: User = Depends(require_admin()),
    code: Annotated[
        str | None,
        Query(
            max_length=10,
            description="BCP47/ISO 639 language code, e.g. 'te', 'hi'",
        ),
    ] = None,
) -> LanguageRead:
    """Create a new language registry entry."""
    try:
        language = LanguageService.create_language(
            session,
            normalize_language_name(name),
            code=code,
            created_by=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LanguageRead(name=language.name, code=language.code)

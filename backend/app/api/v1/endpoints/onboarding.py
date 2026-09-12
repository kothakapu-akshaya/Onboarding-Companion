"""Onboarding progress and evidence API endpoints.

The onboarding service is a separate deployment that shares the corpus JWT
signing secret. All routes here derive the acting user strictly from the
verified token subject; no client-supplied identity is ever accepted.
"""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.onboarding_deps import get_current_onboarding_user
from app.db.session import SessionDep
from app.models.onboarding import OnboardingEvidence, OnboardingProgress
from app.schemas.onboarding import (
    OnboardingEvidenceRead,
    OnboardingEvidenceUrl,
    OnboardingProgressRead,
    OnboardingProgressUpdate,
)
from app.utils.hetzner_storage import get_storage_client

logger = logging.getLogger(__name__)

router = APIRouter()

# The 16 stable onboarding task keys defined by the application.
ONBOARDING_TASK_KEYS: frozenset[str] = frozenset(str(i) for i in range(1, 17))

MAX_EVIDENCE_FILE_SIZE: int = 5 * 1024 * 1024
MAX_EVIDENCE_PER_TASK: int = 6

EVIDENCE_EXPIRES_MINUTES_DEFAULT: int = 15
EVIDENCE_EXPIRES_MINUTES_MIN: int = 1
EVIDENCE_EXPIRES_MINUTES_MAX: int = 120

ALLOWED_IMAGE_MIME_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/gif"}
)

EVIDENCE_OBJECT_PREFIX = "onboarding/users"


def _validate_task_key(task_key: str) -> None:
    """Reject task keys outside the stable onboarding task set."""
    if task_key not in ONBOARDING_TASK_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown onboarding task key",
        )


def _validate_upload_file(file: UploadFile) -> None:
    """Reject files whose extension or media type is not an allowed image."""
    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()
    if extension not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image file type",
        )

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image media type",
        )


def _build_object_key(user_id: UUID, task_key: str, filename: str) -> str:
    """Build a server-generated object key for one evidence image."""
    extension = os.path.splitext(filename)[1].lower()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return (
        f"{EVIDENCE_OBJECT_PREFIX}/{user_id}/tasks/{task_key}/"
        f"{timestamp}_{unique_id}{extension}"
    )


def _get_owned_evidence(
    session: Session,
    user_id: UUID,
    task_key: str,
    evidence_id: UUID,
) -> OnboardingEvidence:
    """Fetch an evidence row scoped to a user and task, or raise 404."""
    row: OnboardingEvidence | None = session.exec(
        select(OnboardingEvidence).where(
            OnboardingEvidence.id == evidence_id,
            OnboardingEvidence.user_id == user_id,
            OnboardingEvidence.task_key == task_key,
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )
    return row


def _assert_evidence_slot(
    session: Session, user_id: UUID, task_key: str
) -> None:
    """Reject the upload when the per-task evidence limit is reached."""
    count = len(
        session.exec(
            select(OnboardingEvidence).where(
                OnboardingEvidence.user_id == user_id,
                OnboardingEvidence.task_key == task_key,
            )
        ).all()
    )
    if count >= MAX_EVIDENCE_PER_TASK:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Evidence limit of {MAX_EVIDENCE_PER_TASK} reached "
                "for this task"
            ),
        )


@router.get(
    "/progress",
    response_model=list[OnboardingProgressRead],
)
def list_progress(
    session: SessionDep,
    user_id: UUID = Depends(get_current_onboarding_user),
) -> list[OnboardingProgress]:
    """List the caller's progress across all onboarding tasks."""
    rows = session.exec(
        select(OnboardingProgress)
        .where(OnboardingProgress.user_id == user_id)
        .order_by(OnboardingProgress.task_key)
    ).all()
    return list(rows)


@router.put(
    "/progress/{task_key}",
    response_model=OnboardingProgressRead,
)
def upsert_progress(
    task_key: str,
    payload: OnboardingProgressUpdate,
    session: SessionDep,
    user_id: UUID = Depends(get_current_onboarding_user),
) -> OnboardingProgress:
    """Create or update progress for a single onboarding task."""
    _validate_task_key(task_key)

    progress: OnboardingProgress | None = session.exec(
        select(OnboardingProgress).where(
            OnboardingProgress.user_id == user_id,
            OnboardingProgress.task_key == task_key,
        )
    ).first()

    if progress is None:
        progress = OnboardingProgress(user_id=user_id, task_key=task_key)
        session.add(progress)

    progress.status = payload.status
    progress.notes = payload.notes
    progress.updated_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(progress)
    return progress


@router.post(
    "/tasks/{task_key}/evidence",
    response_model=OnboardingEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_evidence(
    task_key: str,
    session: SessionDep,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_onboarding_user),
) -> OnboardingEvidence:
    """Upload one evidence image for an onboarding task."""
    _validate_task_key(task_key)
    _validate_upload_file(file)

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )
    if len(content) > MAX_EVIDENCE_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Evidence file exceeds the 5 MB limit",
        )

    _assert_evidence_slot(session, user_id, task_key)

    filename = file.filename or "evidence"
    mime_type = (file.content_type or "").lower() or "application/octet-stream"
    object_key = _build_object_key(user_id, task_key, filename)
    metadata: dict[str, str] = {
        "onboarding_task_key": task_key,
        "onboarding_user_id": str(user_id),
    }

    try:
        get_storage_client().upload_file_data(
            BytesIO(content),
            object_key,
            file_size=len(content),
            content_type=mime_type,
            metadata=metadata,
        )
    except Exception:
        logger.exception("Failed to upload onboarding evidence to storage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload evidence to storage",
        )

    evidence = OnboardingEvidence(
        user_id=user_id,
        task_key=task_key,
        object_key=object_key,
        file_name=filename,
        mime_type=mime_type,
        file_size=len(content),
    )

    try:
        session.add(evidence)
        session.commit()
        session.refresh(evidence)
    except SQLAlchemyError:
        session.rollback()
        try:
            get_storage_client().delete_object(object_key)
        except Exception:
            logger.exception(
                "Failed to roll back uploaded evidence object %s", object_key
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save evidence metadata",
        )

    return evidence


@router.get(
    "/tasks/{task_key}/evidence",
    response_model=list[OnboardingEvidenceRead],
)
def list_evidence(
    task_key: str,
    session: SessionDep,
    user_id: UUID = Depends(get_current_onboarding_user),
) -> list[OnboardingEvidence]:
    """List the caller's evidence images for one onboarding task."""
    _validate_task_key(task_key)

    rows = session.exec(
        select(OnboardingEvidence)
        .where(
            OnboardingEvidence.user_id == user_id,
            OnboardingEvidence.task_key == task_key,
        )
        .order_by(text("created_at"))
    ).all()
    return list(rows)


@router.get(
    "/tasks/{task_key}/evidence/{evidence_id}/url",
    response_model=OnboardingEvidenceUrl,
)
def get_evidence_url(
    task_key: str,
    evidence_id: UUID,
    session: SessionDep,
    expires_minutes: int = Query(
        default=EVIDENCE_EXPIRES_MINUTES_DEFAULT,
        ge=EVIDENCE_EXPIRES_MINUTES_MIN,
        le=EVIDENCE_EXPIRES_MINUTES_MAX,
    ),
    user_id: UUID = Depends(get_current_onboarding_user),
) -> OnboardingEvidenceUrl:
    """Generate a bounded presigned read URL for one evidence image."""
    _validate_task_key(task_key)
    evidence = _get_owned_evidence(session, user_id, task_key, evidence_id)

    try:
        url = get_storage_client().get_presigned_url(
            evidence.object_key,
            expires=timedelta(minutes=expires_minutes),
        )
    except Exception:
        logger.exception("Failed to generate presigned URL for evidence")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate access URL",
        )

    return OnboardingEvidenceUrl(
        evidence_url=url, expires_minutes=expires_minutes
    )


@router.delete(
    "/tasks/{task_key}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_evidence(
    task_key: str,
    evidence_id: UUID,
    session: SessionDep,
    user_id: UUID = Depends(get_current_onboarding_user),
) -> Response:
    """Delete one evidence image and its stored metadata."""
    _validate_task_key(task_key)
    evidence = _get_owned_evidence(session, user_id, task_key, evidence_id)

    try:
        get_storage_client().delete_object(evidence.object_key)
    except Exception:
        logger.exception("Failed to delete evidence object from storage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete evidence",
        )

    session.delete(evidence)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

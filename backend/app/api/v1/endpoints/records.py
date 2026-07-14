import json
import logging
import os
import time
import uuid
from collections.abc import Sequence
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import magic
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.encoders import jsonable_encoder
from geoalchemy2.shape import to_shape
from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import col, select

from app.core.auth import get_current_active_user
from app.core.config import settings
from app.core.rbac_fastapi import (
    create_rbac_dependency,
    require_any_role,
)
from app.core.validation_utils import (
    ValidationContext,
    validate_with_enhanced_errors,
)
from app.db.session import SessionDep
from app.models.change_enums import ChangeSource
from app.models.extracted_text import ExtractedText as ExtractedTextModel
from app.models.record import MediaType, Record, ReleaseRights
from app.models.role import RoleEnum
from app.models.user import User
from app.schemas import (
    ExtractedTextCreate,
    ExtractedTextUpdate,
    ExtractedTextUpdateResponse,
    RecordCreate,
    RecordRead,
    RecordReviewFilters,
    RecordReviewRequest,
    RecordReviewResponse,
    RecordUpdate,
    RecordUrlResponse,
)
from app.schemas.geo_schemas import Coordinates
from app.schemas.rag import (
    KnowledgeResponse,
    KnowledgeUpdateRequest,
    KnowledgeUpdateResponse,
    RAGStatus,
    RetrievalRequest,
    RetrievalResponse,
    TextNormalizer,
)
from app.schemas.upload_validation import (
    ChunkedUploadRequest,
    RecordUpdateValidation,
    UploadFinalizationRequest,
)
from app.services.claim_service import ClaimService
from app.services.extracted_text_resolver import ExtractedTextResolver
from app.services.hybrid_retrieval import HybridRetrievalService
from app.services.language_service import LanguageService
from app.services.metadata_indexer import MetadataIndexer
from app.services.points_service import award_for_edit, award_for_record
from app.services.record_history_service import RecordHistoryService
from app.services.text_metrics_service import (
    update_extracted_text_metrics,
)
from app.utils.chunk_manager import ChunkManager
from app.utils.file_hashing import get_file_hash
from app.utils.hetzner_storage import (
    get_file_url,
    get_object_key_from_url,
    upload_file_to_hetzner,
)
from app.utils.media_duration import get_media_duration_with_remux
from app.utils.postgis_utils import (
    create_point_for_record,
    extract_coordinates_from_geometry,
)
from app.utils.record_file_generator import RecordFileGenerator
from app.utils.snr_frequency import calculate_snr_frequency

router = APIRouter()
logger = logging.getLogger(__name__)

REVIEW_ONLY_FIELDS = {"reviewed", "reviewed_by", "reviewed_at"}


def _serialize_extracted_text(
    et: ExtractedTextModel,
) -> dict:
    """Serialize a single ExtractedText ORM object to a plain dict."""
    return {
        "uid": et.uid,
        "record_id": et.record_id,
        "confidence": et.confidence,
        "language": et.language,
        "extraction_type": et.extraction_type,
        "quality_score": et.quality_score,
        "notes": et.notes,
        "summary": et.summary,
        "model_name": et.model_name,
        "processing_date": et.processing_date,
        "segments": et.segments,
        "named_entities": et.named_entities,
        "metadata": et.extraction_metadata,
        "dataset": et.dataset,
        "word_count": et.word_count,
        "sentence_count": et.sentence_count,
        "character_count": et.character_count,
        "skipped": et.skipped,
        "skip_reason": et.skip_reason,
        "edit": et.edit,
        "device_uid": et.device_uid,
        "created_at": et.created_at,
        "updated_at": et.updated_at,
    }


def _resolve_and_serialize(
    record: Record,
    session: SessionDep,
) -> tuple[dict | None, UUID | None]:
    """Resolve extracted text for *record* (own or sibling) and serialize.

    Returns ``(serialized_dict, source_record_uid)``.  When the text
    belongs to the record itself *source_record_uid* is ``None``.
    """
    et_entry, source_rid = ExtractedTextResolver.resolve(record, session)
    if et_entry is None:
        return None, None
    return _serialize_extracted_text(et_entry), source_rid


def _validate_record_tags(tags: list[str], session: SessionDep) -> None:
    """Validate record_tags are valid UUIDs referencing existing records."""
    from uuid import UUID

    for tag in tags:
        try:
            record_uid = UUID(tag)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid record_tag: '{tag}' is not a valid UUID.",
            )

        record = session.get(Record, record_uid)
        if not record:
            raise HTTPException(
                status_code=400,
                detail=f"Record not found for record_tag: '{tag}'.",
            )


def _validate_tagged_usernames(
    usernames: list[str], session: SessionDep
) -> None:
    """Validate tagged_usernames exist in the User table."""
    for username in usernames:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if not user:
            raise HTTPException(
                status_code=400,
                detail=f"User not found for tagged_username: '{username}'.",
            )


def resolve_device_uid(
    session: SessionDep, user_id: UUID, device_id: str | None
) -> UUID | None:
    """Resolve a client-supplied device_id to its registered Device uid.

    Returns None if no device_id is supplied. Raises a 400 if the device_id
    does not correspond to a device that this user has registered (via the
    devices endpoint).

    Also bumps the device's and the user-device link's `last_seen_at` so
    that activity from records/extractions counts toward device usage.
    """
    if not device_id:
        return None

    from app.models.device import Device
    from app.models.user_device import UserDevice

    result = session.exec(
        select(Device, UserDevice)
        .join(UserDevice, col(UserDevice.device_uid) == col(Device.uid))
        .where(Device.device_id == device_id, UserDevice.user_id == user_id)
    ).first()
    if not result:
        raise HTTPException(
            status_code=400,
            detail=f"Device not found: {device_id}",
        )
    device, link = result

    now = datetime.now(timezone.utc)
    device.last_seen_at = now
    device.updated_at = now
    link.last_seen_at = now
    session.add(device)
    session.add(link)

    return device.uid


def is_forbidden_filetype(path: str) -> bool:
    """Check if a file type is forbidden based on its MIME type."""
    mime = magic.from_file(path, mime=True)
    forbidden_mime_types = {
        "application/zip",
        "application/x-tar",
        "application/x-gzip",
        "application/x-7z-compressed",
        "application/x-rar-compressed",
    }
    return mime in forbidden_mime_types


@router.get("/", response_model=list[RecordRead])
def get_records(
    session: SessionDep,
    category_id: UUID | None = None,
    user_id: UUID | None = None,
    media_type: MediaType | None = None,
    hashtag: str | None = Query(
        None,
        min_length=1,
        max_length=100,
        description="Filter by hashtag (without # prefix)",
    ),
    tagged_username: str | None = Query(
        None,
        min_length=1,
        max_length=100,
        description="Filter by tagged username",
    ),
    current_user: User = Depends(require_any_role()),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of records to return"
    ),
) -> list[RecordRead]:
    """Get all records with optional filtering and pagination."""
    query = select(Record).offset(skip).limit(limit)

    if category_id:
        # Filter by records that have the specific category_id in their
        # category_ids array
        query = query.where(text("category_ids @> :category_id::jsonb")).params(
            category_id=json.dumps([str(category_id)])
        )
    if user_id:
        query = query.where(Record.user_id == user_id)
    if media_type:
        query = query.where(Record.media_type == media_type)
    if hashtag and isinstance(hashtag, str):
        query = query.where(text("hashtags @> :hashtag::jsonb")).params(
            hashtag=json.dumps([hashtag])
        )
    if tagged_username and isinstance(tagged_username, str):
        query = query.where(
            text("tagged_usernames @> :tagged_username::jsonb")
        ).params(tagged_username=json.dumps([tagged_username]))

    records = session.exec(query).all()

    # Batch-resolve fallback text for records without their own extraction
    fallback_map = ExtractedTextResolver.batch_resolve(records, session)

    result = []
    for record in records:
        record_dict = record.model_dump()

        own_text = getattr(record, "extracted_text", None)
        if own_text is not None:
            record_dict["extracted_text"] = _serialize_extracted_text(own_text)
            record_dict["extracted_text_source_record_id"] = None
        elif record.uid in fallback_map:
            et_entry, source_rid = fallback_map[record.uid]
            record_dict["extracted_text"] = _serialize_extracted_text(et_entry)
            record_dict["extracted_text_source_record_id"] = source_rid
        else:
            record_dict["extracted_text"] = None
            record_dict["extracted_text_source_record_id"] = None

        if record.location:
            coords = extract_coordinates_from_geometry(record.location)
            if coords:
                record_dict["location"] = Coordinates(
                    latitude=coords[1], longitude=coords[0]
                )

        # Add username from user
        user = session.get(User, record.user_id)
        if user:
            record_dict["username"] = user.username

        record_data = RecordRead.model_validate(record_dict)
        result.append(record_data)

    return jsonable_encoder(result)


@router.post("/for-review", response_model=RecordReviewResponse)
def get_next_records_for_review(
    request: RecordReviewRequest,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> RecordReviewResponse:
    """Get random records for review based on filters.

    Returns a list of record IDs that match the provided filters.
    The records are selected randomly and exclude the current user's
    own records.

    Request body (filters):
    - language: Filter by languages (multiple values allowed)
    - media_type: Filter by multiple media types
    - category_ids: Filter by category IDs (returns records with ANY of
      the specified categories)
    - source_label: Filter by source label (case-insensitive partial match)
    - release_rights: Filter by release rights type
    - published_date: Filter by published date
    - is_fully_proofread: Filter by fully proofread status (True=proofread,
      False=unproofread)
    - extraction_type: Filter by extraction type (ocr, asr, caption, manual)
    - model_name: Filter by model name
    - version: Filter by version - 'initial' (version 0) or 'latest'
      (current version)
    - limit: Number of records to return (max 100)

    Example usage:
    - Get 1 record for review: { "limit": 1 }
    - Get Hindi audio records: { "filters": { "language": ["hindi"],
      "media_type": ["audio"] }, "limit": 20 }
    - Get records needing proofreading: { "filters": {
      "is_fully_proofread": false }, "limit": 50 }
    - Get records with category A OR B: { "filters": {
      "category_ids": ["uuid-a", "uuid-b"] }, "limit": 20 }
    - Get ASR extracted records by model: { "filters": {
      "extraction_type": "asr", "model_name": "whisper" }, "limit": 20 }
    - Get initial version records: { "filters": { "version": "initial" },
      "limit": 20 }
    - Get latest version records: { "filters": { "version": "latest" },
      "limit": 20 }
    """
    from sqlalchemy import text
    from sqlalchemy.sql import func

    filters = request.filters or RecordReviewFilters()
    limit_count = request.limit
    claim_service = ClaimService()

    has_proofread_filter = filters.is_fully_proofread is not None
    has_validation_filter = filters.is_fully_validated is not None

    if filters.extration is not None and (
        has_proofread_filter or has_validation_filter
    ):
        claim_ttl = settings.CLAIM_TTL
    elif filters.extration is not None:
        claim_ttl = settings.CLAIM_TTL_EXTRACTION
    elif has_proofread_filter or has_validation_filter:
        claim_ttl = settings.CLAIM_TTL_DOCUMENT
    else:
        claim_ttl = settings.CLAIM_TTL

    et_filters = (
        filters.is_fully_proofread is not None
        or filters.is_fully_validated is not None
        or filters.extraction_type
        or filters.model_name
    )
    version_filter = filters.version

    if filters.extration:
        base_query = (
            select(Record.uid, Record.file_hash, Record.created_at)
            .outerjoin(
                ExtractedTextModel,
                ExtractedTextModel.record_id == Record.uid,  # type: ignore[bad-argument-type]
            )
            .where(
                Record.user_id != current_user.id,
                or_(
                    ExtractedTextModel.uid.is_(None),  # type: ignore[missing-attribute]
                    ExtractedTextModel.segments.is_(None),  # type: ignore[missing-attribute]
                ),
                # Audio/video records must not be flagged as invalid, must
                # have a valid SNR frequency, and must be at least 5 seconds
                # long to be eligible for transcription. Non-audio/video
                # records pass through unconditionally.
                or_(
                    col(Record.media_type).not_in(["audio", "video"]),
                    and_(
                        col(Record.speech_not_detected).is_(False),
                        col(Record.snr_frequency).is_not(None),
                    ),
                ),
            )
        )

        if filters.language:
            base_query = base_query.where(
                col(Record.language).in_(
                    [lang.strip() for lang in filters.language]
                )
            )

        if filters.media_type:
            base_query = base_query.where(
                col(Record.media_type).in_(filters.media_type)
            )

        if filters.category_ids:
            for cat_id in filters.category_ids:
                base_query = base_query.where(
                    text("category_ids @> :category_id::jsonb").bindparams(
                        category_id=str(cat_id)
                    )
                )

        if filters.source_label:
            base_query = base_query.where(
                col(Record.source_label).ilike(f"%{filters.source_label}%")
            )

        if filters.release_rights:
            base_query = base_query.where(
                Record.release_rights == filters.release_rights
            )

        if filters.published_date:
            base_query = base_query.where(
                Record.published_date == filters.published_date
            )

        def _dedup(rows: Sequence[Any]) -> list[str]:
            seen: dict[str, tuple[str, Any]] = {}
            for uid, file_hash, created_at in rows:
                key = file_hash or str(uid)
                suid = str(uid)
                if key not in seen or created_at < seen[key][1]:
                    seen[key] = (suid, created_at)
            return [uid for uid, _ in sorted(seen.values(), key=lambda x: x[1])]

        try:
            if filters.lock:
                candidate_uids = []
                seen_uids: set[str] = set()
                seen_hashes: set[str] = set()
                remaining = limit_count

                for _ in range(5):
                    if remaining <= 0:
                        break

                    iter_query = base_query
                    if seen_uids:
                        iter_query = iter_query.where(
                            col(Record.uid).not_in(list(seen_uids))
                        )
                    if seen_hashes:
                        iter_query = iter_query.where(
                            or_(
                                Record.file_hash.is_(None),  # type: ignore[missing-attribute]
                                col(Record.file_hash).not_in(list(seen_hashes)),
                            )
                        )

                    iter_query = iter_query.order_by(func.random()).limit(
                        remaining * 3
                    )

                    rows = session.exec(iter_query).all()
                    if not rows:
                        break

                    deduped = _dedup(rows)
                    to_claim = deduped[:remaining]
                    seen_uids.update(deduped)
                    for _, fh, _ in rows:
                        if fh:
                            seen_hashes.add(fh)

                    claimed = claim_service.claim(
                        str(current_user.id), to_claim, ttl=claim_ttl
                    )
                    candidate_uids.extend(claimed)
                    remaining = limit_count - len(candidate_uids)

                candidate_uids = candidate_uids[:limit_count]
            else:
                rows = session.exec(
                    base_query.order_by(func.random()).limit(limit_count * 5)
                ).all()
                candidate_uids = _dedup(rows)[:limit_count]

            if not candidate_uids:
                logger.info(
                    f"No records available for review for user "
                    f"{current_user.id}"
                )
                return RecordReviewResponse(record_ids=[])

            record_ids = [{"record_id": uid} for uid in candidate_uids]
            return RecordReviewResponse(record_ids=record_ids)

        except Exception as e:
            logger.error(
                f"Error getting next record for review for user "
                f"{current_user.id}: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve next record for review",
            )

    if et_filters or version_filter:
        base_query = """
        SELECT r.uid, 1 as priority_level
        FROM record r
        JOIN extractedtext et ON et.record_id = r.uid
        """

        if version_filter == "initial":
            base_query += """
            JOIN record_history_v2 rh ON rh.record_id = r.uid 
            AND rh.version_number = 0
            """

        base_query += """
        WHERE r.user_id != :user_id
        """

        query_filters = []
        params: dict[str, Any] = {"user_id": current_user.id}

        if filters.is_fully_proofread is not None:
            query_filters.append(
                "AND et.is_fully_proofread = :is_fully_proofread"
            )
            params["is_fully_proofread"] = filters.is_fully_proofread

        if filters.is_fully_validated is not None:
            query_filters.append(
                "AND et.is_fully_validated = :is_fully_validated"
            )
            params["is_fully_validated"] = filters.is_fully_validated

        if filters.extraction_type:
            query_filters.append("AND et.extraction_type = :extraction_type")
            params["extraction_type"] = filters.extraction_type.value

        if filters.model_name:
            query_filters.append("AND et.model_name = :model_name")
            params["model_name"] = filters.model_name

        if filters.language:
            query_filters.append("AND r.language::text = ANY(:languages)")
            params["languages"] = [
                language.strip() for language in filters.language
            ]

        if filters.media_type:
            query_filters.append("AND r.media_type::text = ANY(:media_types)")
            params["media_types"] = [mt.value for mt in filters.media_type]

        if filters.category_ids:
            query_filters.append("AND r.category_ids && :category_ids::jsonb")
            params["category_ids"] = json.dumps(
                [str(cat_id) for cat_id in filters.category_ids]
            )

        if filters.source_label:
            query_filters.append("AND r.source_label ILIKE :source_label")
            params["source_label"] = f"%{filters.source_label}%"

        if filters.release_rights:
            query_filters.append("AND r.release_rights = :release_rights")
            params["release_rights"] = filters.release_rights.value

        if filters.published_date:
            query_filters.append("AND r.published_date = :published_date")
            params["published_date"] = filters.published_date

        full_query = (
            base_query
            + " ".join(query_filters)
            + """
        ORDER BY
            RANDOM()
        LIMIT :limit
        """
        )

        try:
            if filters.lock:
                candidate_uids = []
                seen: set[str] = set()
                remaining = limit_count

                for _ in range(5):
                    if remaining <= 0:
                        break

                    iter_filters = list(query_filters)
                    iter_params = dict(params)
                    iter_params["limit"] = remaining
                    if seen:
                        iter_filters.append("AND r.uid != ALL(:exclude_uids)")
                        iter_params["exclude_uids"] = list(seen)

                    iter_query = (
                        base_query
                        + " ".join(iter_filters)
                        + " ORDER BY RANDOM() LIMIT :limit"
                    )
                    result = session.exec(  # type: ignore[no-matching-overload]
                        text(iter_query), params=iter_params
                    ).all()
                    if not result:
                        break

                    new_uids = [str(row.uid) for row in result]
                    seen.update(new_uids)
                    claimed = claim_service.claim(
                        str(current_user.id), new_uids, ttl=claim_ttl
                    )
                    candidate_uids.extend(claimed)
                    remaining = limit_count - len(candidate_uids)

                candidate_uids = candidate_uids[:limit_count]
            else:
                params["limit"] = limit_count
                result = session.exec(text(full_query), params=params).all()  # type: ignore[no-matching-overload]
                candidate_uids = [str(row.uid) for row in result]

            if not candidate_uids:
                logger.info(
                    f"No records available for review for user "
                    f"{current_user.id}"
                )
                return RecordReviewResponse(record_ids=[])

            record_ids = [{"record_id": uid} for uid in candidate_uids]
            return RecordReviewResponse(record_ids=record_ids)

        except Exception as e:
            logger.error(
                f"Error getting next record for review for user "
                f"{current_user.id}: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve next record for review",
            )
    else:
        if filters.version == "initial":
            base_query = """
            SELECT r.uid, 1 as priority_level
            FROM record r
            JOIN record_history_v2 rh ON rh.record_id = r.uid 
            AND rh.version_number = 0
            """

            base_query += """
            WHERE r.user_id != :user_id
            """

            try:
                if filters.lock:
                    candidate_uids = []
                    seen: set[str] = set()
                    remaining = limit_count

                    for _ in range(5):
                        if remaining <= 0:
                            break

                        iter_params: dict[str, Any] = {
                            "user_id": current_user.id,
                            "limit": remaining,
                        }
                        iter_query = base_query + (
                            " ORDER BY RANDOM() LIMIT :limit"
                        )
                        if seen:
                            iter_query = base_query + (
                                " AND r.uid != ALL(:exclude_uids)"
                                " ORDER BY RANDOM() LIMIT :limit"
                            )
                            iter_params["exclude_uids"] = list(seen)

                        result = session.exec(  # type: ignore[no-matching-overload]
                            text(iter_query), iter_params
                        ).all()
                        if not result:
                            break

                        new_uids = [str(row.uid) for row in result]
                        seen.update(new_uids)
                        claimed = claim_service.claim(
                            str(current_user.id), new_uids, ttl=claim_ttl
                        )
                        candidate_uids.extend(claimed)
                        remaining = limit_count - len(candidate_uids)

                    candidate_uids = candidate_uids[:limit_count]
                else:
                    params = {"user_id": current_user.id}
                    result = session.exec(text(base_query), params=params).all()  # type: ignore[no-matching-overload]
                    candidate_uids = [str(row.uid) for row in result]

                if not candidate_uids:
                    return RecordReviewResponse(record_ids=[])

                record_ids = [{"record_id": uid} for uid in candidate_uids]
                return RecordReviewResponse(record_ids=record_ids)

            except Exception as e:
                logger.error(
                    f"Error getting next record for review for user "
                    f"{current_user.id}: {e}"
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to retrieve next record for review",
                )

        base_orm_query = select(Record.uid).where(
            Record.user_id != current_user.id
        )

        if filters.language:
            base_orm_query = base_orm_query.where(
                col(Record.language).in_(
                    [lang.strip() for lang in filters.language]
                )
            )

        if filters.media_type:
            base_orm_query = base_orm_query.where(
                col(Record.media_type).in_(filters.media_type)
            )

        if filters.category_ids:
            for cat_id in filters.category_ids:
                base_orm_query = base_orm_query.where(
                    text("category_ids @> :category_id::jsonb").bindparams(
                        category_id=str(cat_id)
                    )
                )

        if filters.source_label:
            base_orm_query = base_orm_query.where(
                col(Record.source_label).ilike(f"%{filters.source_label}%")
            )

        if filters.release_rights:
            base_orm_query = base_orm_query.where(
                Record.release_rights == filters.release_rights
            )

        if filters.published_date:
            base_orm_query = base_orm_query.where(
                Record.published_date == filters.published_date
            )

        try:
            if filters.lock:
                candidate_uids = []
                seen: set[str] = set()
                remaining = limit_count

                for _ in range(5):
                    if remaining <= 0:
                        break

                    iter_query = base_orm_query
                    if seen:
                        iter_query = iter_query.where(
                            col(Record.uid).not_in(list(seen))
                        )
                    iter_query = iter_query.order_by(func.random()).limit(
                        remaining
                    )

                    result = session.exec(iter_query).all()
                    if not result:
                        break

                    new_uids = [str(uid) for uid in result]
                    seen.update(new_uids)
                    claimed = claim_service.claim(
                        str(current_user.id), new_uids, ttl=claim_ttl
                    )
                    candidate_uids.extend(claimed)
                    remaining = limit_count - len(candidate_uids)

                candidate_uids = candidate_uids[:limit_count]
            else:
                query = base_orm_query.order_by(func.random()).limit(
                    limit_count
                )
                result = session.exec(query).all()
                candidate_uids = [str(uid) for uid in result]

            if not candidate_uids:
                logger.info(
                    f"No records available for review for user "
                    f"{current_user.id}"
                )
                return RecordReviewResponse(record_ids=[])

            record_ids = [{"record_id": uid} for uid in candidate_uids]
            return RecordReviewResponse(record_ids=record_ids)

        except Exception as e:
            logger.error(
                f"Error getting next record for review for user "
                f"{current_user.id}: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve next record for review",
            )


@router.get("/search", response_model=list[dict])
def search_records(
    session: SessionDep,
    query: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Search query string for title/description",
    ),
    limit: int = Query(
        10, ge=1, le=100, description="Number of records to return (max 100)"
    ),
    current_user: User = Depends(require_any_role()),
    hashtag: str | None = Query(
        None,
        min_length=1,
        max_length=100,
        description="Filter by hashtag (without # prefix)",
    ),
    tagged_username: str | None = Query(
        None,
        min_length=1,
        max_length=100,
        description="Filter by tagged username",
    ),
) -> list[dict]:
    """Search records by similarity with title and description.

    Returns matching record IDs.
    Optionally filter by hashtag or tagged_username.
    """
    # Use SQLAlchemy functions to call PostgreSQL similarity function securely
    similarity_title = func.similarity(Record.title, query)
    similarity_description = func.similarity(Record.description, query)

    search_query = select(Record.uid).where(
        (similarity_title > 0.1) | (similarity_description > 0.1)
    )
    params: dict[str, Any] = {}

    if hashtag and isinstance(hashtag, str):
        search_query = search_query.where(
            text("hashtags @> :hashtag_search::jsonb")
        )
        params["hashtag_search"] = json.dumps([hashtag])

    if tagged_username and isinstance(tagged_username, str):
        search_query = search_query.where(
            text("tagged_usernames @> :tagged_username_search::jsonb")
        )
        params["tagged_username_search"] = json.dumps([tagged_username])

    search_query = search_query.order_by(
        func.greatest(similarity_title, similarity_description).desc()
    ).limit(limit)

    # Execute the query using SQLAlchemy ORM approach
    result = session.exec(search_query, params=params).all()

    # Process results and return record IDs
    record_ids = []
    for record_id in result:
        record_ids.append({"record_id": str(record_id)})

    return jsonable_encoder(record_ids)


@router.get("/tags/suggest", response_model=dict)
def suggest_tags(
    session: SessionDep,
    query: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Search query for tag/usernames",
    ),
    limit: int = Query(
        10, ge=1, le=100, description="Number of suggestions to return"
    ),
    current_user: User = Depends(require_any_role()),
) -> dict:
    """Suggest users, normal tags, and record tags based on search query.

    Returns matching users, hashtags, and record tags.
    """
    query_lower = query.lower()
    suggestions: dict[str, list[dict]] = {
        "users": [],
        "hashtags": [],
        "record_tags": [],
    }

    # Search users by username (case‑insensitive contains)
    user_results = session.exec(
        select(User.username)
        .where(col(User.username).ilike(f"%{query_lower}%"))
        .limit(limit)
    ).all()
    suggestions["users"] = [{"username": str(u)} for u in user_results if u]

    # Search existing hashtags across records (DB-side deduplication)
    hashtag_rows = session.exec(  # type: ignore[no-matching-overload]
        text(
            "SELECT DISTINCT jsonb_array_elements_text(hashtags) AS tag"
            " FROM record WHERE hashtags IS NOT NULL"
            " AND jsonb_array_elements_text(hashtags) ILIKE :q"
            " LIMIT :lim"
        ),
        params={"q": f"%{query_lower}%", "lim": limit},
    ).all()
    suggestions["hashtags"] = [{"tag": row[0]} for row in hashtag_rows]

    # Search record tags
    record_tag_rows = session.exec(  # type: ignore[no-matching-overload]
        text(
            "SELECT DISTINCT jsonb_array_elements_text(record_tags) AS tag"
            " FROM record WHERE record_tags IS NOT NULL"
            " AND jsonb_array_elements_text(record_tags) ILIKE :q"
            " LIMIT :lim"
        ),
        params={"q": f"%{query_lower}%", "lim": limit},
    ).all()
    suggestions["record_tags"] = [{"tag": row[0]} for row in record_tag_rows]

    return jsonable_encoder(suggestions)


@router.get("/{record_id}", response_model=RecordRead)
def get_record(
    record_id: str,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> RecordRead:
    """Get a specific record by ID."""
    try:
        record_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record ID format")

    record = session.get(Record, record_uuid)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Convert to read schema with coordinates
    record_dict = record.model_dump()
    et_dict, source_rid = _resolve_and_serialize(record, session)
    record_dict["extracted_text"] = et_dict
    record_dict["extracted_text_source_record_id"] = source_rid

    if record.location:
        coords = extract_coordinates_from_geometry(record.location)
        if coords:
            record_dict["location"] = Coordinates(
                latitude=coords[1], longitude=coords[0]
            )

    # Add username from user
    user = session.get(User, record.user_id)
    if user:
        record_dict["username"] = user.username

    result = RecordRead.model_validate(record_dict)

    return jsonable_encoder(result)


@router.post("/", response_model=RecordRead, status_code=201)
async def create_record(
    record_data: RecordCreate,
    session: SessionDep,
    generate_file: bool = Query(
        False, description="Generate a sample file for this record"
    ),
    file_size_kb: int = Query(
        10, ge=1, le=1000, description="Size of generated file in KB"
    ),
    current_user: User = Depends(require_any_role()),
) -> RecordRead:
    """Create a new record, optionally with a generated file."""
    # Validate foreign keys exist
    from app.models.category import Category
    from app.models.user import User

    # Validate all provided category IDs exist
    if record_data.category_ids:
        for cat_id in record_data.category_ids:
            category = session.get(Category, cat_id)
            if not category:
                raise HTTPException(
                    status_code=400, detail=f"Category not found: {cat_id}"
                )

    if record_data.user_id:
        user = session.get(User, record_data.user_id)
        if not user:
            raise HTTPException(status_code=400, detail="User not found")

    # Validate record_tags reference existing records
    if record_data.record_tags:
        _validate_record_tags(record_data.record_tags, session)

    # Validate tagged_usernames exist in the User table
    if record_data.tagged_usernames:
        _validate_tagged_usernames(record_data.tagged_usernames, session)

    # Set creator field based on release rights
    final_creator = None
    if record_data.release_rights == ReleaseRights.creator:
        # For own work, set creator to the uploader's name
        final_creator = user.name
    elif record_data.release_rights == ReleaseRights.others:
        # For others' work, use the provided creator name (validated by schema)
        final_creator = record_data.creator

    # Resolve the contributing device, if provided
    device_uid = resolve_device_uid(
        session, record_data.user_id, record_data.device_id
    )

    # Convert schema data to model data
    record_dict = record_data.model_dump(exclude={"location", "device_id"})
    record_dict["creator"] = final_creator
    record_dict["device_uid"] = device_uid

    # Convert HttpUrl to string for database storage
    if "source_url" in record_dict and record_dict["source_url"] is not None:
        record_dict["source_url"] = str(record_dict["source_url"])

    # Create new record - we'll handle category_ids separately
    record = Record.model_validate(record_dict)
    # Convert UUIDs to strings for proper JSONB storage
    record.category_ids = (
        [str(cat_id) for cat_id in record_data.category_ids]  # type: ignore[assignment]
        if record_data.category_ids
        else []
    )

    # Set initial status
    if generate_file:
        record.status = "generating"

    # Handle PostGIS location if provided using SQLAlchemy session
    if record_data.location:
        from sqlalchemy import text

        # Use raw SQL to set the geometry
        session.add(record)
        session.flush()  # Get the ID
        session.execute(
            text(
                "UPDATE record SET location = ST_GeomFromText(:wkt, 4326) "
                "WHERE uid = :uid"
            ),
            {
                "wkt": create_point_for_record(
                    record_data.location.latitude,
                    record_data.location.longitude,
                ),
                "uid": record.uid,
            },
        )
    else:
        session.add(record)

    session.flush()  # Ensure we have the record UID

    # Generate file if requested
    if generate_file:
        try:
            file_generator = RecordFileGenerator()

            # Ensure record UID is available
            if not record.uid:
                raise ValueError("Record UID is required for file generation")

            # Generate and upload file
            # Convert category IDs to JSON array string for metadata
            category_ids_json = (
                json.dumps([str(cat_id) for cat_id in record.category_ids])
                if record.category_ids
                else "[]"
            )
            upload_result = (
                await file_generator.create_and_upload_file_for_record(
                    record_uid=record.uid,
                    media_type=record.media_type,
                    file_size_kb=file_size_kb,
                    custom_metadata={
                        # "title": record.title,
                        "description": record.description or "",
                        "user_id": str(record.user_id),
                        # Store all categories as JSON array
                        "category_ids": category_ids_json,
                        "creation_type": "api_generated",
                    },
                )
            )

            # Update record with file information
            record.file_url = upload_result["object_url"]
            # Extract filename from object_key
            # (e.g., "text/uuid.txt" -> "uuid.txt")
            object_key = upload_result["object_key"]
            filename = (
                object_key.split("/")[-1] if "/" in object_key else object_key
            )
            record.file_name = filename
            record.file_size = upload_result["file_size"]
            record.status = "generated"

            logger.info(
                f"Generated file for record {record.uid}: "
                f"{upload_result['object_key']}"
            )

        except Exception as e:
            logger.error(
                f"Failed to generate file for record {record.uid}: {e}"
            )
            record.status = "generation_failed"
            # Don't raise the exception, still create the record without
            # the file

    # Create initial version (version 0) to capture the initial record state
    try:
        history_service = RecordHistoryService(session)
        history_service.initialize_record_history(
            record=record,
            created_by=record.user_id,
            change_source=ChangeSource.system_process,
            change_reason="Initial record creation (version 0)",
        )

        award_for_record(session, record)
        session.commit()
        session.refresh(record)

        logger.info(
            f"Created initial history version 0 for record {record.uid}"
        )
    except Exception as e:
        logger.error(
            f"Failed to create initial history version 0 for record "
            f"{record.uid}: {e}"
        )
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create initial history for record: {str(e)}",
        )

    # Convert to read schema with coordinates
    record_dict = record.model_dump()
    et_dict, source_rid = _resolve_and_serialize(record, session)
    record_dict["extracted_text"] = et_dict
    record_dict["extracted_text_source_record_id"] = source_rid

    if record.location:
        coords = extract_coordinates_from_geometry(record.location)
        if coords:
            record_dict["location"] = Coordinates(
                latitude=coords[1], longitude=coords[0]
            )

    result = RecordRead.model_validate(record_dict)

    return jsonable_encoder(result)


@router.post("/upload/chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
    filename: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    upload_uuid: str = Form(...),
    current_user: User = Depends(require_any_role()),
) -> dict:
    """Upload a single chunk of a file."""
    # Validate chunk file
    if not chunk.filename:
        raise HTTPException(status_code=400, detail="No chunk file provided")

    # Use enhanced Pydantic validation for chunk parameters
    chunk_request = validate_with_enhanced_errors(
        ChunkedUploadRequest,
        {
            "filename": filename,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "upload_uuid": upload_uuid,
        },
    )

    # Read chunk data
    try:
        chunk_data = await chunk.read()
    except Exception as e:
        logger.error(f"Failed to read chunk data: {e}")
        raise HTTPException(status_code=500, detail="Failed to read chunk data")

    # Enforce 50MB maximum chunk size limit
    CHUNK_SIZE_LIMIT = 50 * 1024 * 1024  # 10MB
    if len(chunk_data) > CHUNK_SIZE_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Chunk size {len(chunk_data)} bytes exceeds maximum limit "
                f"of {CHUNK_SIZE_LIMIT} bytes (10MB)"
            ),
        )

    # Save chunk using ChunkManager - use validated data
    chunk_manager = ChunkManager()
    success = chunk_manager.save_chunk(
        chunk_request.upload_uuid,
        chunk_request.chunk_index,
        chunk_request.total_chunks,
        chunk_data,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save chunk")

    logger.info(
        f"Successfully uploaded chunk {chunk_request.chunk_index}/"
        f"{chunk_request.total_chunks} for upload "
        f"{chunk_request.upload_uuid}"
    )

    return {
        "message": "Chunk uploaded successfully",
        "upload_uuid": chunk_request.upload_uuid,
        "chunk_index": chunk_request.chunk_index,
        "total_chunks": chunk_request.total_chunks,
        "chunk_size": len(chunk_data),
    }


@router.post("/upload", response_model=RecordRead, status_code=201)
async def upload_record(
    session: SessionDep,
    title: str = Form(...),
    description: str | None = Form(None),
    category_ids: str = Form(...),  # JSON string of category IDs array
    user_id: str = Form(...),
    media_type: MediaType = Form(...),
    upload_uuid: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    release_rights: ReleaseRights = Form(...),
    creator: str | None = Form(None),
    language: str = Form(...),
    published_date: date | None = Form(
        None, description="Published/event date of the record content"
    ),
    use_uid_filename: bool = Form(
        False,
        description="Use record UID as filename instead of original filename",
    ),
    source_label: str | None = Form(
        None, description="Label for the source of the record"
    ),
    source_url: str | None = Form(
        None, description="URL for the source of the record"
    ),
    tagged_usernames: str | None = Form(
        None,
        description="JSON array of username strings (e.g. ['alice', 'bob'])",
    ),
    hashtags: str | None = Form(
        None,
        description="JSON array of hashtag strings (e.g. ['music', 'python'])",
    ),
    record_tags: str | None = Form(
        None,
        description="JSON array of record tag UUIDs",
    ),
    device_id: str | None = Form(
        None,
        description=(
            "Client-generated device identifier of the contributing "
            "device, as registered via the devices endpoint"
        ),
    ),
    current_user: User = Depends(require_any_role()),
) -> RecordRead:
    """Finalize chunked upload and create a record."""
    import json

    # Validate and parse category IDs from JSON string
    try:
        category_ids_list = json.loads(category_ids)
        if not isinstance(category_ids_list, list):
            raise HTTPException(
                status_code=400, detail="category_ids must be a JSON array"
            )
        category_uuids = [uuid.UUID(cat_id) for cat_id in category_ids_list]
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="category_ids must be a valid JSON array of UUID strings",
        )

    # Use enhanced Pydantic validation for all upload parameters
    upload_request = validate_with_enhanced_errors(
        UploadFinalizationRequest,
        {
            "title": title,
            "description": description,
            # Pass the JSON string of category IDs
            "category_ids": category_ids,
            "user_id": user_id,
            "media_type": media_type,
            "upload_uuid": upload_uuid,
            "filename": filename,
            "total_chunks": total_chunks,
            "latitude": latitude,
            "longitude": longitude,
            "release_rights": release_rights,
            "creator": creator,
            "language": language,
            "published_date": published_date,
            "use_uid_filename": use_uid_filename,
            "source_label": source_label,
            "source_url": source_url,
            "tagged_usernames": tagged_usernames,
            "hashtags": hashtags,
            "record_tags": record_tags,
        },
    )

    user_uuid = uuid.UUID(upload_request.user_id)

    try:
        upload_request.language = LanguageService.validate_language_code(
            session, upload_request.language
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Validate foreign keys
    from app.models.category import Category
    from app.models.user import User

    # Validate all category UUIDs exist
    for cat_id in category_uuids:
        category = session.get(Category, cat_id)
        if not category:
            raise HTTPException(
                status_code=400, detail=f"Category not found: {cat_id}"
            )

    user = session.get(User, user_uuid)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    # Set creator field based on release rights
    final_creator = None
    if upload_request.release_rights == ReleaseRights.creator:
        # For own work, set creator to the uploader's name
        final_creator = user.name
    elif upload_request.release_rights == ReleaseRights.others:
        # For others' work, use the provided creator name (validated by schema)
        final_creator = upload_request.creator

    # Initialize ChunkManager and validate chunks
    chunk_manager = ChunkManager()

    if release_rights == ReleaseRights.downloaded:
        raise HTTPException(
            status_code=400,
            detail=(
                "Sorry! Please upload works created by you or your "
                "family/friends with their permission."
            ),
        )

    # Check if all chunks are present
    missing_chunks = chunk_manager.get_missing_chunks(upload_uuid, total_chunks)
    if missing_chunks:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Missing chunks: {missing_chunks}. Please upload all "
                f"chunks before finalizing."
            ),
        )

    # Combine chunks into final file
    combined_file_path = chunk_manager.combine_chunks(upload_uuid, filename)
    if not combined_file_path:
        raise HTTPException(status_code=500, detail="Failed to combine chunks")
    # Check actual file content (MIME type)
    if is_forbidden_filetype(combined_file_path):
        os.unlink(combined_file_path)  # Clean up
        raise HTTPException(
            status_code=400, detail="Archive file types are not allowed."
        )

    # Calculate file hash
    try:
        file_hash = get_file_hash(combined_file_path)
    except Exception as e:
        logger.error(f"Failed to calculate file hash for {filename}: {e}")
        file_hash = None

    # Calculate SNR frequency for audio/video files
    snr_frequency = None
    speech_not_detected = False
    if media_type in ["audio", "video"]:
        try:
            snr_frequency = calculate_snr_frequency(
                combined_file_path, media_type
            )
        except Exception as e:
            logger.error(
                f"Failed to calculate SNR frequency for {filename}: {e}"
            )
            snr_frequency = None
        if snr_frequency is None:
            speech_not_detected = True

    # Parse and validate tagged_usernames
    tagged_username_list: list[str] = []
    if upload_request.tagged_usernames:
        try:
            tagged_username_list = json.loads(upload_request.tagged_usernames)
            if not isinstance(tagged_username_list, list):
                tagged_username_list = []
        except (json.JSONDecodeError, TypeError):
            tagged_username_list = []
        if tagged_username_list:
            _validate_tagged_usernames(tagged_username_list, session)

    # Parse hashtags
    hashtags_list: list[str] = []
    if upload_request.hashtags:
        try:
            hashtags_list = json.loads(upload_request.hashtags)
            if not isinstance(hashtags_list, list):
                hashtags_list = []
        except (json.JSONDecodeError, TypeError):
            hashtags_list = []

    # Parse and validate record_tags
    record_tags_list: list[str] = []
    if upload_request.record_tags:
        try:
            record_tags_list = json.loads(upload_request.record_tags)
            if not isinstance(record_tags_list, list):
                record_tags_list = []
        except (json.JSONDecodeError, TypeError):
            record_tags_list = []
        if record_tags_list:
            _validate_record_tags(record_tags_list, session)

    # Resolve the contributing device, if provided
    device_uid = resolve_device_uid(session, user_uuid, device_id)

    # Create record first to get the UID
    record_data = Record(
        title=upload_request.title,
        description=upload_request.description,
        category_ids=[str(cat_id) for cat_id in category_uuids]
        if category_uuids
        else [],  # Convert UUIDs to strings for proper JSONB storage
        user_id=user_uuid,
        device_uid=device_uid,
        media_type=upload_request.media_type,
        release_rights=upload_request.release_rights,
        creator=final_creator,
        language=upload_request.language,
        published_date=upload_request.published_date,
        source_label=upload_request.source_label,
        source_url=str(upload_request.source_url)
        if upload_request.source_url
        else None,
        tagged_usernames=tagged_username_list,
        hashtags=hashtags_list,
        record_tags=record_tags_list,
        status="uploading",  # Temporary status during upload
    )

    session.add(record_data)
    session.flush()  # Get the UID for the record

    # Compute duration for audio/video files
    duration_seconds = None
    start_time = time.time()

    try:
        if media_type.value in ["audio", "video"]:
            try:
                duration_seconds = get_media_duration_with_remux(
                    combined_file_path, media_type.value
                )
                computation_time = time.time() - start_time
                logger.info(
                    f"Successfully computed duration for file '{filename}': "
                    f"{duration_seconds} seconds (took {computation_time:.2f}s)"
                )
            except Exception as e:
                computation_time = time.time() - start_time
                logger.warning(
                    f"Failed to compute duration for {filename}: {e} "
                    f"(took {computation_time:.2f}s)"
                )
                duration_seconds = None

            # Reject files we can't probe as audio/video — these are
            # typically corrupted uploads or files that aren't actually
            # decodable media (e.g. an HTML page saved with a media
            # extension), and would otherwise be stored as unusable
            # records that fail later during transcription.
            if duration_seconds is None:
                logger.warning(
                    f"Could not determine duration for {filename}; "
                    f"rejecting as invalid {media_type.value} upload"
                )
                session.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Could not read this file as valid "
                        f"{media_type.value}. Please ensure the file is "
                        "a valid, uncorrupted audio/video file."
                    ),
                )

            # Validate minimum duration for audio/video files
            if duration_seconds < 5:
                logger.warning(
                    f"File duration too small for {filename}: "
                    f"{duration_seconds} seconds minimum upload duration "
                    f"5 seconds"
                )
                session.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"File duration too small: "
                        f"{duration_seconds:.2f} seconds. Minimum "
                        f"required duration is 5 seconds."
                    ),
                )
            if duration_seconds > (60 * 60):
                logger.warning(
                    f"File duration too large for {filename}: "
                    f"{duration_seconds} seconds Maximum upload duration "
                    f"is 3600 seconds"
                )
                session.rollback()
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"File duration too long: "
                        f"{duration_seconds:.2f} seconds. Maximum "
                        f"upload duration is 3600 seconds."
                    ),
                )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to process combined file: {e}")
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"File processing failed: {str(e)}"
        )

    # Upload combined file to Hetzner Object Storage
    try:
        if use_uid_filename:
            # Use UID-based filename
            file_generator = RecordFileGenerator()
            extension = file_generator.get_file_extension(media_type)
            final_filename = f"{record_data.uid}{extension}"
        else:
            # Use original filename
            final_filename = filename

        # Determine prefix based on media type
        prefix = f"{media_type.value}/" if media_type else "misc/"
        # Convert category IDs to JSON array string for metadata
        category_ids_json = (
            json.dumps([str(cat_id) for cat_id in category_uuids])
            if category_uuids
            else "[]"
        )
        metadata = {
            "user_id": str(user_uuid),
            "title_punycode": title.encode("punycode").decode("ascii"),
            # Store all categories as JSON array
            "category_ids": category_ids_json,
            "media_type": media_type.value if media_type else "unknown",
            "record_uid": str(record_data.uid),
            "original_filename_punycode": filename.encode("punycode").decode(
                "utf-8"
            ),
            "upload_type": "chunked_upload",
        }

        logger.info(
            f"Uploading combined file to Hetzner storage: {combined_file_path}"
        )
        # Upload combined file to storage
        upload_result = upload_file_to_hetzner(
            combined_file_path, prefix=prefix, metadata=metadata
        )
        file_url = upload_result["object_url"]
        upload_result["object_key"]
        actual_file_size = upload_result["file_size"]

    except Exception as e:
        logger.error(f"Failed to upload combined file to Hetzner storage: {e}")
        # Clean up the record if upload failed
        session.rollback()
        raise HTTPException(
            status_code=500, detail=f"File upload failed: {str(e)}"
        )
    finally:
        # Clean up the combined temporary file
        try:
            os.unlink(combined_file_path)
            logger.info(
                f"Cleaned up temporary combined file: {combined_file_path}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to clean up temporary file {combined_file_path}: {e}"
            )

    # Update record with file information
    record_data.file_url = file_url
    record_data.file_name = final_filename
    record_data.file_size = actual_file_size
    record_data.duration_seconds = duration_seconds
    record_data.file_hash = file_hash
    record_data.snr_frequency = snr_frequency
    record_data.speech_not_detected = speech_not_detected
    record_data.status = (
        "uploaded"  # Mark as uploaded since file upload succeeded
    )

    # Handle PostGIS location if coordinates provided using raw SQL
    if latitude is not None and longitude is not None:
        from sqlalchemy import text

        session.execute(
            text(
                "UPDATE record SET location = ST_GeomFromText(:wkt, 4326) "
                "WHERE uid = :uid"
            ),
            {
                "wkt": create_point_for_record(latitude, longitude),
                "uid": record_data.uid,
            },
        )

    # Award +1 point for a successful upload (idempotent by record_uid)
    award_for_record(session, record_data)

    # Create initial version (version 0) to capture the initial record state
    try:
        history_service = RecordHistoryService(session)
        history_service.initialize_record_history(
            record=record_data,
            created_by=record_data.user_id,
            change_source=ChangeSource.system_process,
            change_reason=(
                "Initial record creation via chunked upload (version 0)"
            ),
        )
        logger.info(
            f"Created initial history version 0 for record {record_data.uid}"
        )
    except Exception as e:
        logger.error(
            f"Failed to create initial history for record "
            f"{record_data.uid}: {e}"
        )
        # We don't fail the whole upload if history fails, but we log it
        # Actually, for consistency with create_record, we might want to fail?
        # User said "i do not see version 0 being created", implying they want.
        # Given it's a critical part of the system now, let's make it robust.

    session.commit()
    session.refresh(record_data)

    # Clean up chunk files after successful upload
    chunk_manager.cleanup_chunks(upload_uuid)

    # Convert to read schema with coordinates
    record_dict = record_data.model_dump()
    et_dict, source_rid = _resolve_and_serialize(record_data, session)
    record_dict["extracted_text"] = et_dict
    record_dict["extracted_text_source_record_id"] = source_rid

    if record_data.location:
        coords = extract_coordinates_from_geometry(record_data.location)
        if coords:
            record_dict["location"] = Coordinates(
                latitude=coords[1], longitude=coords[0]
            )
    result = RecordRead.model_validate(record_dict)

    return jsonable_encoder(result)


@router.patch("/{record_id}", response_model=RecordRead)
def patch_record(
    record_id: UUID,
    record_data: RecordUpdate,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> Record:
    """Updates a record using Pydantic validation for centralized validation.

    Now includes complete history tracking of all changes.
    """
    record = session.get(Record, record_id)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Initialize history service
    history_service = RecordHistoryService(session)

    # Capture original state before changes
    original_values = {}
    for field in record.__fields__.keys():
        value = getattr(record, field, None)
        if value is not None:
            # Handle special field types
            if field == "location" and value:
                from app.utils.postgis_utils import (
                    extract_coordinates_from_geometry,
                )

                coords = extract_coordinates_from_geometry(value)
                if coords:
                    original_values[field] = {
                        "latitude": coords[1],
                        "longitude": coords[0],
                    }
            else:
                original_values[field] = value

    # Use enhanced Pydantic validation with context
    with ValidationContext("record_update", str(current_user.id)):
        # Convert RecordUpdate to update validation format
        update_data = record_data.model_dump(exclude_unset=True)

        forbidden_review_fields = sorted(
            REVIEW_ONLY_FIELDS.intersection(update_data)
        )
        if forbidden_review_fields:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Review state fields are server-managed and cannot be "
                    "updated directly. Remove fields: "
                    f"{', '.join(forbidden_review_fields)}."
                ),
            )

        # Convert location dict to Coordinates if present
        if "location" in update_data and update_data["location"]:
            location_dict = update_data["location"]
            update_data["location"] = Coordinates(
                latitude=location_dict["latitude"],
                longitude=location_dict["longitude"],
            )

        # Validate using enhanced validation utilities
        validated_update = validate_with_enhanced_errors(
            RecordUpdateValidation, update_data
        )

        # Apply validated changes to record
        update_dict = validated_update.model_dump(exclude_unset=True)

        if "language" in update_dict:
            try:
                update_dict["language"] = (
                    LanguageService.validate_language_code(
                        session, update_dict["language"]
                    )
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        # Validate record_tags reference existing records
        if "record_tags" in update_dict and update_dict["record_tags"]:
            _validate_record_tags(update_dict["record_tags"], session)

        # Validate tagged_usernames exist in the User table
        if (
            "tagged_usernames" in update_dict
            and update_dict["tagged_usernames"]
        ):
            _validate_tagged_usernames(update_dict["tagged_usernames"], session)

        # Handle creator based on release rights when that field is updated.
        if "release_rights" in update_dict:
            user = session.get(User, record.user_id)
            if update_dict["release_rights"] == ReleaseRights.creator:
                # For own work, set creator to the uploader's name
                update_dict["creator"] = user.name if user else None  # type: ignore[missing-attribute]
            elif update_dict["release_rights"] == ReleaseRights.others:
                # For others' work, ensure creator is provided
                # (validated by schema)
                update_dict["creator"] = validated_update.creator

        # Apply changes to record
        for field, value in update_dict.items():
            if field == "location" and value is not None:
                # Convert Coordinates to PostGIS POINT format
                setattr(
                    record,
                    field,
                    f"POINT({value['longitude']} {value['latitude']})",
                )
            elif field == "source_url" and value is not None:
                # Convert HttpUrl to string for database storage
                setattr(record, field, str(value) if value else None)
            elif field == "category_ids" and value is not None:
                # Convert UUIDs to strings for proper JSONB storage
                setattr(
                    record,
                    field,
                    [str(cat_id) for cat_id in value] if value else [],
                )
            else:
                setattr(record, field, value)

        # Update the updated_at timestamp
        record.updated_at = datetime.now(timezone.utc)

    # Capture new state after changes
    new_values = {}
    for field in record.__fields__.keys():
        value = getattr(record, field, None)
        if value is not None:
            # Handle special field types
            if field == "location" and value:
                from app.utils.postgis_utils import (
                    extract_coordinates_from_geometry,
                )

                coords = extract_coordinates_from_geometry(value)
                if coords:
                    new_values[field] = {
                        "latitude": coords[1],
                        "longitude": coords[0],
                    }
            else:
                new_values[field] = value

    # Create history entry for the changes
    try:
        history_entry = history_service.capture_record_changes(
            record_id=record.uid,  # type: ignore[bad-argument-type]
            old_values=original_values,
            new_values=new_values,
            changed_by=current_user.id,
            change_source=ChangeSource.user_edit,
            change_reason="User edit via PATCH endpoint",
        )

        if history_entry:
            logger.info(
                f"Created history entry {history_entry.uid} for record "
                f"{record.uid} (version {history_entry.version_number}) "
                f"by user {current_user.id}"
            )
    except Exception as e:
        logger.error(
            f"Failed to create history entry for record {record.uid}: {e}"
        )
        # Don't fail the update if history creation fails, but log the error

    session.add(record)

    # Award points for editing the record and update streaks
    award_for_edit(session, record, current_user.id)

    session.commit()
    session.refresh(record)

    record_dict = record.model_dump()
    et_dict, source_rid = _resolve_and_serialize(record, session)
    record_dict["extracted_text"] = et_dict
    record_dict["extracted_text_source_record_id"] = source_rid
    if record.location:
        shape = to_shape(record.location)
        record_dict["location"] = Coordinates(
            latitude=shape.y, longitude=shape.x
        )

    result = RecordRead.model_validate(record_dict)
    return jsonable_encoder(result)


# Location-based search endpoints


@router.get("/search/nearby", response_model=list[RecordRead])
def search_records_nearby(
    session: SessionDep,
    latitude: float = Query(
        ..., ge=-90, le=90, description="Latitude coordinate"
    ),
    longitude: float = Query(
        ..., ge=-180, le=180, description="Longitude coordinate"
    ),
    distance_meters: float = Query(
        ..., gt=0, le=50000, description="Search radius in meters (max 50km)"
    ),
    category_id: UUID | None = None,
    media_type: MediaType | None = None,
    current_user: User = Depends(
        create_rbac_dependency(roles=[RoleEnum.admin, RoleEnum.reviewer])
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[RecordRead]:
    """Search for records within a specified distance of a point."""
    from sqlalchemy import text

    # Build the base query with PostGIS distance calculation
    distance_condition = text(
        "ST_DWithin(location, ST_GeomFromText(:point_wkt, 4326), :distance) "
        "AND location IS NOT NULL"
    )

    query = (
        select(Record)
        .where(distance_condition)
        .params(
            point_wkt=create_point_for_record(latitude, longitude),
            distance=distance_meters,
        )
    )

    # Add additional filters
    if category_id:
        query = query.where(text("category_ids @> :category_id::jsonb")).params(
            category_id=json.dumps([str(category_id)])
        )
    if media_type:
        query = query.where(Record.media_type == media_type)

    # Add ordering by distance and pagination
    query = (
        query.order_by(
            text("ST_Distance(location, ST_GeomFromText(:point_wkt, 4326))")
        )
        .offset(skip)
        .limit(limit)
    )

    records = session.exec(query).all()

    fallback_map = ExtractedTextResolver.batch_resolve(records, session)

    # Convert to read schema with coordinates
    result = []
    for record in records:
        # Use the custom model_dump method that handles PostGIS geometry
        record_dict = record.model_dump()

        own_text = getattr(record, "extracted_text", None)
        if own_text is not None:
            record_dict["extracted_text"] = _serialize_extracted_text(own_text)
            record_dict["extracted_text_source_record_id"] = None
        elif record.uid in fallback_map:
            et_entry, source_rid = fallback_map[record.uid]
            record_dict["extracted_text"] = _serialize_extracted_text(et_entry)
            record_dict["extracted_text_source_record_id"] = source_rid
        else:
            record_dict["extracted_text"] = None
            record_dict["extracted_text_source_record_id"] = None

        # Add username from user
        user = session.get(User, record.user_id)
        if user:
            record_dict["username"] = user.username

        record_data = RecordRead.model_validate(record_dict)
        if record.location:
            coords = extract_coordinates_from_geometry(record.location)
            if coords:
                record_data.location = Coordinates(
                    latitude=coords[1], longitude=coords[0]
                )
        result.append(record_data)

    return jsonable_encoder(result)


@router.get("/search/bbox", response_model=list[RecordRead])
def search_records_in_bbox(
    session: SessionDep,
    min_lat: float = Query(..., ge=-90, le=90, description="Minimum latitude"),
    min_lng: float = Query(
        ..., ge=-180, le=180, description="Minimum longitude"
    ),
    max_lat: float = Query(..., ge=-90, le=90, description="Maximum latitude"),
    max_lng: float = Query(
        ..., ge=-180, le=180, description="Maximum longitude"
    ),
    category_id: UUID | None = None,
    media_type: MediaType | None = None,
    current_user: User = Depends(
        create_rbac_dependency(roles=[RoleEnum.admin, RoleEnum.reviewer])
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[RecordRead]:
    """Search for records within a bounding box (rectangular area)."""
    from sqlalchemy import text

    # Validate bounding box
    if min_lat >= max_lat or min_lng >= max_lng:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid bounding box: min coordinates must be less "
                "than max coordinates"
            ),
        )

    # Create bounding box polygon WKT
    bbox_wkt = (
        f"POLYGON(({min_lng} {min_lat}, {max_lng} {min_lat}, "
        f"{max_lng} {max_lat}, {min_lng} {max_lat}, {min_lng} {min_lat}))"
    )

    # Build query with PostGIS bounding box check
    bbox_condition = text(
        "ST_Within(location, ST_GeomFromText(:bbox_wkt, 4326)) "
        "AND location IS NOT NULL"
    )

    query = select(Record).where(bbox_condition).params(bbox_wkt=bbox_wkt)

    # Add additional filters
    if category_id:
        query = query.where(text("category_ids @> :category_id::jsonb")).params(
            category_id=json.dumps([str(category_id)])
        )
    if media_type:
        query = query.where(Record.media_type == media_type)

    # Add pagination
    query = query.offset(skip).limit(limit)

    records = session.exec(query).all()

    fallback_map = ExtractedTextResolver.batch_resolve(records, session)

    # Convert to read schema with coordinates
    result = []
    for record in records:
        # Use the custom model_dump method that handles PostGIS geometry
        record_dict = record.model_dump()

        own_text = getattr(record, "extracted_text", None)
        if own_text is not None:
            record_dict["extracted_text"] = _serialize_extracted_text(own_text)
            record_dict["extracted_text_source_record_id"] = None
        elif record.uid in fallback_map:
            et_entry, source_rid = fallback_map[record.uid]
            record_dict["extracted_text"] = _serialize_extracted_text(et_entry)
            record_dict["extracted_text_source_record_id"] = source_rid
        else:
            record_dict["extracted_text"] = None
            record_dict["extracted_text_source_record_id"] = None

        # Add username from user
        user = session.get(User, record.user_id)
        if user:
            record_dict["username"] = user.username

        record_data = RecordRead.model_validate(record_dict)
        if record.location:
            coords = extract_coordinates_from_geometry(record.location)
            if coords:
                record_data.location = Coordinates(
                    latitude=coords[1], longitude=coords[0]
                )
        result.append(record_data)

    return jsonable_encoder(result)


@router.get("/search/distance", response_model=list[dict])
def get_records_with_distances(
    session: SessionDep,
    latitude: float = Query(
        ..., ge=-90, le=90, description="Reference latitude"
    ),
    longitude: float = Query(
        ..., ge=-180, le=180, description="Reference longitude"
    ),
    max_distance_meters: float | None = Query(
        None, gt=0, le=100000, description="Maximum distance in meters"
    ),
    current_user: User = Depends(
        create_rbac_dependency(roles=[RoleEnum.admin, RoleEnum.reviewer])
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> list[dict]:
    """Get records with calculated distances from a reference point."""
    from sqlalchemy import text

    # Build query with distance calculation
    distance_expr = text(
        "ST_Distance(location, ST_GeomFromText(:point_wkt, 4326)) "
        "as distance_meters"
    )

    base_query = (
        select(Record, distance_expr)
        .where(text("location IS NOT NULL"))
        .params(point_wkt=create_point_for_record(latitude, longitude))
    )

    # Add distance filter if specified
    if max_distance_meters:
        distance_filter = text(
            "ST_DWithin(location, ST_GeomFromText(:point_wkt, 4326), "
            ":max_distance)"
        )
        base_query = base_query.where(distance_filter).params(
            max_distance=max_distance_meters
        )

    # Order by distance and add pagination
    query = (
        base_query.order_by(text("distance_meters")).offset(skip).limit(limit)
    )

    results = session.exec(query).all()

    # Separate records from distances for batch resolution
    records = [r for r, _ in results]
    fallback_map = ExtractedTextResolver.batch_resolve(records, session)

    # Convert to response format
    response = []
    for record, distance in results:
        # Use the custom model_dump method that handles PostGIS geometry
        record_dict = record.model_dump()

        own_text = getattr(record, "extracted_text", None)
        if own_text is not None:
            record_dict["extracted_text"] = _serialize_extracted_text(own_text)
            record_dict["extracted_text_source_record_id"] = None
        elif record.uid in fallback_map:
            et_entry, source_rid = fallback_map[record.uid]
            record_dict["extracted_text"] = _serialize_extracted_text(et_entry)
            record_dict["extracted_text_source_record_id"] = source_rid
        else:
            record_dict["extracted_text"] = None
            record_dict["extracted_text_source_record_id"] = None

        record_data = RecordRead.model_validate(record_dict)
        if record.location:
            coords = extract_coordinates_from_geometry(record.location)
            if coords:
                record_data.location = Coordinates(
                    latitude=coords[1], longitude=coords[0]
                )

        response.append(
            {
                "record": record_data.model_dump(),
                "distance_meters": float(distance),
                "distance_km": round(float(distance) / 1000, 2),
            }
        )

    return jsonable_encoder(response)


@router.get("/{record_id}/record-url", response_model=RecordUrlResponse)
def get_temporary_access_url(
    record_id: UUID,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
    expires_minutes: int = Query(
        15,
        ge=1,
        le=120,
        description="Duration for which the URL is valid, in minutes.",
    ),
) -> RecordUrlResponse:
    """Generates a secure (presigned) URL for a record's file and redirects.

    This allows controlled, time-limited access to the media file without
    making it public.
    """
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if not record.file_url:
        raise HTTPException(
            status_code=404, detail="No file is associated with this record."
        )

    object_key = get_object_key_from_url(record.file_url)
    if not object_key:
        logger.error(f"Failed to parse object key from {record.file_url}")
        raise HTTPException(
            status_code=500,
            detail="Could not determine the file key from the URL.",
        )

    try:
        expires_hours = expires_minutes / 60.0

        temporary_url = get_file_url(
            object_key=object_key,
            presigned=True,
            expires_hours=expires_hours,
        )
    except Exception as e:
        logger.error(
            f"Failed to generate presigned URL for object key {object_key}: {e}"
        )
        raise HTTPException(
            status_code=500, detail="Failed to generate a secure access URL."
        )

    return jsonable_encoder(RecordUrlResponse(record_url=temporary_url))


# Extracted text management endpoints


@router.post("/{record_id}/extracted_text")
def save_ai_extracted_text(
    record_id: UUID,
    extracted_text: ExtractedTextCreate,
    session: SessionDep,
    current_user: User = Depends(require_any_role()),
) -> dict:
    """Save AI-generated extracted text (OCR/ASR/Captioning) to a record.

    This creates an entry in the dedicated extractedtext table and logs
    the version in RecordHistory.
    """
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Check if AI extracted text already exists for this record
    existing_extraction = session.exec(
        select(ExtractedTextModel).where(
            ExtractedTextModel.record_id == record_id
        )
    ).first()

    if existing_extraction:
        raise HTTPException(
            status_code=409,
            detail=(
                "Extracted text already exists for this record and cannot "
                "be overwritten via POST. Use PATCH to update."
            ),
        )

    # Convert validated Pydantic model to dict for storage mapping
    validated_text_dict = extracted_text.model_dump(exclude_unset=True)

    # Resolve the device that performed this extraction, if provided
    device_uid = resolve_device_uid(
        session, current_user.id, validated_text_dict.get("device_id")
    )

    # Create new ExtractedText entry
    new_extracted_text = ExtractedTextModel(
        record_id=record_id,
        extraction_type=validated_text_dict.get("extraction_type", "manual"),
        confidence=validated_text_dict.get("confidence"),
        language=validated_text_dict.get("language"),
        quality_score=validated_text_dict.get("quality_score"),
        notes=validated_text_dict.get("notes"),
        summary=validated_text_dict.get("summary"),
        model_name=validated_text_dict.get("model_name"),
        processing_date=validated_text_dict.get("processing_date"),
        segments=validated_text_dict.get("segments"),
        named_entities=validated_text_dict.get("named_entities"),
        extraction_metadata=validated_text_dict.get("metadata"),
        device_uid=device_uid,
    )

    session.add(new_extracted_text)
    session.flush()

    update_extracted_text_metrics(
        new_extracted_text, validated_text_dict.get("segments")
    )
    record.updated_at = datetime.now(timezone.utc)
    session.add(record)

    # Award credits for audio/video extraction duration
    if (
        record.media_type in (MediaType.audio, MediaType.video)
        and record.duration_seconds
    ):
        user = session.get(User, current_user.id)
        if user:
            user.credits = (user.credits or 0) + record.duration_seconds
            session.add(user)

    # Record the change in history — service snapshots record +
    # extracted_text together
    history_service = RecordHistoryService(session)
    history_service.capture_extracted_text_change(
        record=record,
        changed_by=current_user.id,
        change_source=ChangeSource.ai_processing,
        change_reason="Initial AI text extraction",
    )

    session.commit()
    session.refresh(record)

    ClaimService().release(str(record_id))

    logger.info(
        f"Saved AI extracted text for record {record_id} by "
        f"user {current_user.id}"
    )

    version_info = history_service.get_version_summary(record_id)

    return {
        "message": "AI extracted text saved successfully",
        "record_id": str(record_id),
        "version": version_info["current_version"],
    }


@router.patch(
    "/{record_id}/extracted_text", response_model=ExtractedTextUpdateResponse
)
def update_extracted_text(
    record_id: UUID,
    corrected_text: ExtractedTextUpdate,
    session: SessionDep,
    expected_version: int | None = Query(
        None, description="Expected version for optimistic locking (optional)"
    ),
    current_user: User = Depends(require_any_role()),
) -> ExtractedTextUpdateResponse:
    """Update extracted text for a record (user corrections).

    Creates new version (2+) with change_source='user_edit'.
    Uses RecordHistory system for versioning and audit trail via Record table.
    """
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Optional optimistic locking check
    if expected_version is not None:
        current_version = (
            record.version_info.current_version if record.version_info else 0
        )
        if current_version != expected_version:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Version mismatch. Expected {expected_version}, got "
                    f"{current_version}. Please refresh and try again."
                ),
            )

    # Check if existing extracted_text entry exists
    et_entry = session.exec(
        select(ExtractedTextModel).where(
            ExtractedTextModel.record_id == record_id
        )
    ).first()

    if et_entry is None:
        # Copy-on-write: check for borrowed text from a sibling
        sibling_text, _ = ExtractedTextResolver.resolve(record, session)
        if sibling_text is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No extracted text exists for this record. AI text "
                    "must be saved first."
                ),
            )
        et_entry = ExtractedTextResolver.copy_to_record(sibling_text, record_id)
        session.add(et_entry)
        session.flush()

    # Convert validated Pydantic model to dict for storage
    validated_corrected_text = corrected_text.model_dump(exclude_unset=True)

    # Preserve proofread and validated status from original segments
    if (
        et_entry.segments
        and "segments" in validated_corrected_text
        and validated_corrected_text["segments"]
    ):
        original_segments = et_entry.segments
        incoming_segments = validated_corrected_text["segments"]

        num_original = len(original_segments)
        num_incoming = len(incoming_segments)

        for i in range(num_incoming):
            if i < num_original:
                original_segment = original_segments[i]
                incoming_segment = incoming_segments[i]
                if "proofread" not in incoming_segment:
                    incoming_segment["proofread"] = original_segment.get(
                        "proofread", False
                    )
                if "validated" not in incoming_segment:
                    incoming_segment["validated"] = original_segment.get(
                        "validated", False
                    )
            else:
                if "proofread" not in incoming_segments[i]:
                    incoming_segments[i]["proofread"] = False
                if "validated" not in incoming_segments[i]:
                    incoming_segments[i]["validated"] = False

    # Update the ExtractedText entry fields
    for key, value in validated_corrected_text.items():
        if key == "metadata":
            et_entry.extraction_metadata = value
        elif hasattr(et_entry, key):
            setattr(et_entry, key, value)

    # Maintain is_fully_proofread and is_fully_validated flags
    if validated_corrected_text.get("segments"):
        segments = validated_corrected_text["segments"]
    elif et_entry.segments:
        segments = et_entry.segments
    else:
        segments = []
    if segments:
        et_entry.is_fully_proofread = all(
            s.get("proofread", False) is True or s.get("skipped", False) is True
            for s in segments
        )
        et_entry.is_fully_validated = all(
            s.get("validated", False) is True for s in segments
        )
    else:
        et_entry.is_fully_proofread = False
        et_entry.is_fully_validated = False

    update_extracted_text_metrics(et_entry, et_entry.segments)

    et_entry.updated_at = datetime.now(timezone.utc)
    record.updated_at = datetime.now(timezone.utc)

    session.add(et_entry)
    session.add(record)

    # Record the change via history service
    history_service = RecordHistoryService(session)
    history_entry = history_service.capture_extracted_text_change(
        record=record,
        changed_by=current_user.id,
        change_source=ChangeSource.user_edit,
        change_reason="Text correction via collaborative editing",
    )

    # Award points for editing the extracted text and update streaks
    award_for_edit(session, record, current_user.id)

    # Award credits for audio/video extraction duration
    if (
        record.media_type in (MediaType.audio, MediaType.video)
        and record.duration_seconds
    ):
        user = session.get(User, current_user.id)
        if user:
            user.credits = (user.credits or 0) + record.duration_seconds
            session.add(user)

    session.commit()
    session.refresh(record)

    ClaimService().release(str(record_id))

    # Get updated version info
    version_info = history_service.get_version_summary(record_id)

    logger.info(
        f"Updated corrected text for record {record_id} by user "
        f"{current_user.id}, new version: "
        f"{version_info['current_version']}"
    )

    return ExtractedTextUpdateResponse(
        message="Corrected text updated successfully",
        record_id=str(record_id),
        new_version=version_info["current_version"],
        history_entry_id=str(history_entry.uid) if history_entry else None,
        version_info=version_info,
    )


# ── RAG Helpers ──────────────────────────────────────────


def get_adaptive_params(query: str) -> dict[str, int | float]:
    """Compute adaptive retrieval params based on query characteristics.

    Tunes top_k, context_window, and trigram_threshold dynamically based on
    query length, keywords (explain, describe, etc.), and entity presence.
    """
    query = query.strip()
    tokens = query.split()
    q_len = len(tokens)
    query_lower = query.lower()

    top_k: int = 8
    context_window: int = 1
    trigram_threshold: float = 0.2

    if q_len <= 2:
        top_k = 12
        context_window = 2
        trigram_threshold = 0.15
    elif 3 <= q_len <= 10:
        top_k = 8
        context_window = 1
        trigram_threshold = 0.2
    else:
        top_k = 6
        context_window = 1
        trigram_threshold = 0.25

    if any(
        word in query_lower
        for word in ["explain", "describe", "summary", "detail"]
    ):
        context_window = 2

    if any(word in query_lower for word in ["approx", "similar", "like"]):
        trigram_threshold = 0.1

    if q_len <= 5 and any(token and token[0].isupper() for token in tokens):
        top_k = max(top_k, 10)

    return {
        "top_k": top_k,
        "context_window": context_window,
        "trigram_threshold": trigram_threshold,
    }


def _get_extracted_text(
    session: SessionDep, record: Record
) -> tuple[Any, UUID | None]:
    """Resolve extracted text (own or sibling) for *record*.

    Returns ``(extracted_text_orm, source_record_uid)``.
    When the text belongs to the record itself *source_record_uid* is
    ``None``.
    """
    return ExtractedTextResolver.resolve(record, session)


def _assert_record_access(record: Record, current_user: User) -> None:
    """Enforce user ownership for RAG APIs."""
    if record.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Access denied for this record"
        )


def _is_cache_valid(extracted_text: Any | None, current_version: int) -> bool:
    """Check if semantic artifacts are cached and aligned with version."""
    if extracted_text is None:
        return False

    extraction_metadata = extracted_text.extraction_metadata or {}
    indexed_version = extraction_metadata.get("semantic_indexed_version")

    # Check if we have a summary and the version matches
    has_semantic_data = bool(extracted_text.summary or extraction_metadata)
    return has_semantic_data and indexed_version == current_version


def _derive_rag_status(
    extracted_text: Any | None, current_version: int
) -> RAGStatus:
    """Derive RAG status from semantic artifacts and version alignment."""
    if not TextNormalizer.has_meaningful_extracted_text(extracted_text):
        return RAGStatus.no_text

    if _is_cache_valid(extracted_text, current_version):
        return RAGStatus.indexed

    return RAGStatus.ready_for_indexing


def _has_semantic_index(extracted_text: Any | None) -> bool:
    """Check whether semantic index metadata exists on extracted text."""
    if extracted_text is None:
        return False

    extraction_metadata = extracted_text.extraction_metadata or {}
    return extraction_metadata.get("semantic_indexed_version") is not None


def _require_record_uid(record: Record) -> UUID:
    """Ensure record UID is present for response models."""
    if record.uid is None:
        raise HTTPException(status_code=500, detail="Record UID is missing")
    return record.uid


# ── RAG Endpoints ────────────────────────────────────────


@router.get("/{record_id}/knowledge", response_model=KnowledgeResponse)
async def get_knowledge(
    record_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
) -> KnowledgeResponse:
    """Get knowledge status and semantic metadata for a record."""
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    _assert_record_access(record, current_user)

    extracted_text, source_rid = _get_extracted_text(session, record)
    current_version = (
        record.version_info.current_version if record.version_info else 0
    )

    # When text is borrowed from a sibling, the version comparison is
    # meaningless across different records. Treat the text as indexed
    # only when the sibling actually has a semantic index marker.
    if source_rid is not None:
        if not TextNormalizer.has_meaningful_extracted_text(extracted_text):
            status = RAGStatus.no_text
            cache_valid = False
        else:
            cache_valid = _has_semantic_index(extracted_text)
            status = (
                RAGStatus.indexed
                if cache_valid
                else RAGStatus.ready_for_indexing
            )
    else:
        status = _derive_rag_status(extracted_text, current_version)
        cache_valid = _is_cache_valid(extracted_text, current_version)

    extraction_metadata = (
        extracted_text.extraction_metadata if extracted_text else None
    )
    indexed_version = (
        extraction_metadata.get("semantic_indexed_version")
        if extraction_metadata
        else None
    )

    return KnowledgeResponse(
        status=status,
        cache_valid=cache_valid,
        current_version=current_version,
        indexed_version=indexed_version,
        record_id=_require_record_uid(record),
        record_title=record.title,
        summary=extracted_text.summary if extracted_text else None,
        named_entities=extracted_text.named_entities
        if extracted_text
        else None,
        extraction_metadata=extraction_metadata,
        extracted_text_source_record_id=source_rid,
    )


@router.put("/{record_id}/knowledge", response_model=KnowledgeUpdateResponse)
async def upsert_knowledge(
    record_id: UUID,
    payload: KnowledgeUpdateRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
) -> KnowledgeUpdateResponse:
    """Save or update extracted text's semantic metadata."""
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    _assert_record_access(record, current_user)

    extracted_text, source_rid = _get_extracted_text(session, record)
    if not extracted_text:
        raise HTTPException(
            status_code=404,
            detail="Extracted text not found for this record.",
        )
    if not TextNormalizer.has_meaningful_extracted_text(extracted_text):
        raise HTTPException(
            status_code=409,
            detail="Record extracted_text is not ready. Cannot store index.",
        )

    if source_rid is not None:
        extracted_text = ExtractedTextResolver.copy_to_record(
            extracted_text, record_id
        )
        session.add(extracted_text)
        session.flush()

    current_version = (
        record.version_info.current_version if record.version_info else 0
    )

    # 1. Only write summary if not already present
    if not extracted_text.summary or not extracted_text.summary.strip():
        extracted_text.summary = payload.extracted_text.summary

    # 2. Update named_entities if non-empty
    if payload.extracted_text.named_entities:
        extracted_text.named_entities = payload.extracted_text.named_entities

    # 3. Handle constrained extraction_metadata (topics, concepts, themes)
    sanitized_meta = MetadataIndexer.validate_semantic_metadata(
        payload.extraction_metadata.model_dump()
    )

    sanitized_meta["semantic_indexed_version"] = current_version

    # Merge with existing metadata but keep it constrained
    existing_metadata = extracted_text.extraction_metadata or {}
    existing_metadata.update(sanitized_meta)

    # Reassign to trigger SQLAlchemy JSONB mutation tracking
    extracted_text.extraction_metadata = existing_metadata
    if isinstance(extracted_text, ExtractedTextModel):
        flag_modified(extracted_text, "extraction_metadata")

    extracted_text.updated_at = datetime.now(timezone.utc)

    session.add(extracted_text)
    session.commit()
    session.refresh(extracted_text)

    return KnowledgeUpdateResponse(
        status="indexed",
        record_id=_require_record_uid(record),
        indexed_version=current_version,
    )


@router.post("/{record_id}/retrievals", response_model=RetrievalResponse)
async def create_retrieval(
    record_id: UUID,
    payload: RetrievalRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
) -> RetrievalResponse:
    """Search within a record using hybrid semantic retrieval."""
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    _assert_record_access(record, current_user)

    extracted_text, source_rid = _get_extracted_text(session, record)
    if not TextNormalizer.has_meaningful_extracted_text(extracted_text):
        raise HTTPException(
            status_code=400,
            detail="Record extracted_text is not ready. Cannot run retrieval.",
        )

    params = get_adaptive_params(payload.query)

    # Use the source record's UID for DB queries when text is borrowed
    actual_record_id = (
        source_rid if source_rid is not None else _require_record_uid(record)
    )

    retrieval_result = HybridRetrievalService.retrieve(
        session=session,
        record_id=actual_record_id,
        extracted_text=extracted_text,
        query=payload.query,
        top_k=int(params["top_k"]),
        context_window=int(params["context_window"]),
        trigram_threshold=float(params["trigram_threshold"]),
        use_enhanced_retrieval=True,
    )

    return RetrievalResponse(
        record_id=_require_record_uid(record),
        query=payload.query,
        strategy=retrieval_result["strategy"],
        matched_segments=retrieval_result["matched_segments"],
        context_segments=retrieval_result["context_segments"],
        stats=retrieval_result["stats"],
        adaptive_params=params,
    )


# Note: Text extraction and correction history available through
# existing record history endpoints:
# - GET /api/v1/records/{record_id}/history?change_source=ai_processing
#   for AI extraction
# - GET /api/v1/records/{record_id}/history?change_source=user_edit
#   for text corrections
# - GET /api/v1/records/{record_id}/field/extracted_text/history
#   for field-specific history
# - GET /api/v1/records/{record_id}/version/{version} to get specific versions

import logging
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder

from app.api.deps import valid_record, valid_record_restore
from app.core.rbac_fastapi import create_rbac_dependency, require_any_role
from app.db.session import SessionDep
from app.models.change_enums import ChangeSource, ChangeType
from app.models.record import Record
from app.models.record_history import RecordRestore as RecordRestore
from app.models.role import RoleEnum
from app.models.user import User
from app.schemas.record_history import (
    RecordDiffRead,
    RecordFieldHistoryRead,
    RecordHistoryRead,
    RecordRestoreCreate,
    RecordRestoreRead,
    VersionSummaryRead,
)
from app.schemas.record_history_analytics import (
    ChangeActivityReport,
    FieldChangeReport,
)
from app.services.record_history_analytics_service import (
    RecordHistoryAnalyticsService,
)
from app.services.record_history_service import RecordHistoryService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/record/{record_id}/history", response_model=list[RecordHistoryRead]
)
def get_record_history(
    session: SessionDep,
    record: Record = Depends(valid_record),
    current_user: User = Depends(require_any_role()),
    limit: int = Query(
        50, ge=1, le=200, description="Number of history entries to return"
    ),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    change_type: ChangeType | None = Query(
        None, description="Filter by change type"
    ),
    change_source: ChangeSource | None = Query(
        None, description="Filter by change source"
    ),
) -> list[RecordHistoryRead]:
    """Get history entries for a record."""
    history_service = RecordHistoryService(session)
    record_id = cast(UUID, record.uid)
    history_entries = history_service.get_record_history(
        record_id=record_id,
        limit=limit,
        offset=offset,
        change_type=change_type,
        change_source=change_source,
    )

    return jsonable_encoder(history_entries)


@router.get(
    "/record/{record_id}/version/{version}", response_model=RecordHistoryRead
)
def get_record_version(
    session: SessionDep,
    version: int,
    record: Record = Depends(valid_record),
    current_user: User = Depends(require_any_role()),
) -> RecordHistoryRead:
    """Get a specific version of a record."""
    record_id = cast(UUID, record.uid)
    history_service = RecordHistoryService(session)
    version_entry = history_service.get_record_version(record_id, version)

    if not version_entry:
        raise HTTPException(
            status_code=404,
            detail=f"Version {version} not found for record {record.uid}",
        )

    return jsonable_encoder(version_entry)


@router.get("/record/{record_id}/diff", response_model=RecordDiffRead)
def compare_record_versions(
    session: SessionDep,
    record: Record = Depends(valid_record),
    from_version: int = Query(..., description="Starting version number"),
    to_version: int = Query(..., description="Ending version number"),
    current_user: User = Depends(require_any_role()),
) -> RecordDiffRead:
    """Compare two versions of a record."""
    if from_version >= to_version:
        raise HTTPException(
            status_code=400, detail="from_version must be less than to_version"
        )

    history_service = RecordHistoryService(session)

    try:
        diff = history_service.compare_versions(
            cast(UUID, record.uid), from_version, to_version
        )
        return jsonable_encoder(diff)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/record/{record_id}/field/{field_name}/history",
    response_model=list[RecordFieldHistoryRead],
)
def get_field_history(
    session: SessionDep,
    field_name: str,
    record: Record = Depends(valid_record),
    current_user: User = Depends(require_any_role()),
    limit: int = Query(
        20, ge=1, le=100, description="Number of entries to return"
    ),
) -> list[RecordFieldHistoryRead]:
    """Get history for a specific field."""
    # Validate field name against Record model columns
    valid_fields = set(Record.model_fields.keys()) | {
        "extracted_text",
        "location",
    }
    if field_name not in valid_fields:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid field name. Valid fields: {', '.join(valid_fields)}"
            ),
        )

    history_service = RecordHistoryService(session)
    field_history = history_service.get_field_history(
        cast(UUID, record.uid), field_name, limit
    )

    return jsonable_encoder(field_history)


@router.get(
    "/record/{record_id}/version-summary", response_model=VersionSummaryRead
)
def get_version_summary(
    session: SessionDep,
    record: Record = Depends(valid_record),
    current_user: User = Depends(require_any_role()),
) -> VersionSummaryRead:
    """Get version summary for a record."""
    history_service = RecordHistoryService(session)
    summary = history_service.get_version_summary(cast(UUID, record.uid))

    return jsonable_encoder(summary)


# Restore/Rollback endpoints (Admin/Moderator only)


@router.post("/record/{record_id}/restore", response_model=RecordRestoreRead)
def restore_record_version(
    session: SessionDep,
    restore_data: RecordRestoreCreate,
    record: Record = Depends(valid_record),
    current_user: User = Depends(
        create_rbac_dependency(roles=[RoleEnum.admin, RoleEnum.reviewer])
    ),
) -> RecordRestoreRead:
    """Restore a record to a previous version (Admin/Reviewer only)."""
    history_service = RecordHistoryService(session)

    try:
        restore_record = history_service.restore_record_version(
            record_id=cast(UUID, record.uid),
            target_version=restore_data.target_version,
            restored_by=current_user.id,
            restore_reason=restore_data.restore_reason,
            fields_to_restore=restore_data.fields_to_restore,
            requires_approval=restore_data.requires_approval,
        )

        session.commit()
        session.refresh(restore_record)

        logger.info(
            f"Record {record.uid} restore initiated by {current_user.id} "
            f"to version {restore_data.target_version}"
        )

        return jsonable_encoder(restore_record)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/restore/{restore_id}/approve", response_model=RecordRestoreRead)
def approve_restore(
    restore_id: UUID,
    session: SessionDep,
    current_user: User = Depends(
        create_rbac_dependency(roles=[RoleEnum.admin])
    ),
) -> RecordRestoreRead:
    """Approve a pending restore operation (Admin only)."""
    history_service = RecordHistoryService(session)

    try:
        restore_record = history_service.approve_restore(
            restore_id, current_user.id
        )
        session.commit()
        session.refresh(restore_record)

        logger.info(f"Restore {restore_id} approved by admin {current_user.id}")

        return jsonable_encoder(restore_record)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/restore/{restore_id}", response_model=RecordRestoreRead)
def get_restore_details(
    session: SessionDep,
    restore_record: RecordRestore = Depends(valid_record_restore),
    current_user: User = Depends(
        create_rbac_dependency(roles=[RoleEnum.admin, RoleEnum.reviewer])
    ),
) -> RecordRestoreRead:
    """Get details of a restore operation."""
    return jsonable_encoder(restore_record)


@router.get("/pending-restores", response_model=list[RecordRestoreRead])
def get_pending_restores(
    session: SessionDep,
    current_user: User = Depends(
        create_rbac_dependency(roles=[RoleEnum.admin])
    ),
    limit: int = Query(50, ge=1, le=200),
) -> list[RecordRestoreRead]:
    """Get pending restore operations requiring approval (Admin only)."""
    service = RecordHistoryService(session)
    pending = service.get_pending_restores(limit)
    return jsonable_encoder(pending)


# Analytics endpoints


@router.get("/analytics/change-activity", response_model=ChangeActivityReport)
def get_change_activity(
    session: SessionDep,
    current_user: User = Depends(
        create_rbac_dependency(roles=[RoleEnum.admin, RoleEnum.reviewer])
    ),
    days: int = Query(
        30, ge=1, le=365, description="Number of days to analyze"
    ),
) -> ChangeActivityReport:
    """Get change activity analytics."""
    analytics = RecordHistoryAnalyticsService(session)
    return analytics.get_change_activity(days)


@router.get("/analytics/field-changes", response_model=FieldChangeReport)
def get_field_change_analytics(
    session: SessionDep,
    current_user: User = Depends(
        create_rbac_dependency(roles=[RoleEnum.admin, RoleEnum.reviewer])
    ),
    days: int = Query(30, ge=1, le=365),
) -> FieldChangeReport:
    """Get field-level change analytics."""
    analytics = RecordHistoryAnalyticsService(session)
    return analytics.get_field_change_analytics(days)

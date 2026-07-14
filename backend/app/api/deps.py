"""Reusable FastAPI dependencies."""

from uuid import UUID

from fastapi import HTTPException

from app.db.session import SessionDep
from app.models.record import Record
from app.models.record_history import RecordRestore


def valid_record(
    record_id: UUID,
    session: SessionDep,
) -> Record:
    """Resolve a record from the path parameter, or 404."""
    record = session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


def valid_record_restore(
    restore_id: UUID,
    session: SessionDep,
) -> RecordRestore:
    """Resolve a RecordRestore from the path parameter, or 404."""
    restore = session.get(RecordRestore, restore_id)
    if not restore:
        raise HTTPException(status_code=404, detail="Restore record not found")
    return restore

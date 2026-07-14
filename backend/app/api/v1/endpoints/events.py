"""Event management endpoints."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlmodel import select

from app.core.rbac_fastapi import require_admin, require_any_role
from app.db.session import SessionDep
from app.models.event import Event
from app.models.user import User
from app.schemas import RecordReviewFilters
from app.schemas.event import (
    EventCreate,
    EventRead,
    EventUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _serialize_review_filters(
    filters: RecordReviewFilters | None,
) -> dict | None:
    """Serialize RecordReviewFilters into JSON-safe storage values."""
    if not filters:
        return None

    raw = filters.model_dump(exclude_none=True)

    if "category_ids" in raw:
        raw["category_ids"] = [str(cid) for cid in raw["category_ids"]]
    if "media_type" in raw:
        raw["media_type"] = [mt.value for mt in raw["media_type"]]
    if "release_rights" in raw and raw["release_rights"] is not None:
        release_rights = raw["release_rights"]
        raw["release_rights"] = (
            release_rights.value
            if hasattr(release_rights, "value")
            else release_rights
        )
    if "published_date" in raw and raw["published_date"] is not None:
        raw["published_date"] = raw["published_date"].isoformat()
    if "extraction_type" in raw and raw["extraction_type"] is not None:
        extraction_type = raw["extraction_type"]
        raw["extraction_type"] = (
            extraction_type.value
            if hasattr(extraction_type, "value")
            else extraction_type
        )

    return raw


# ---------------------------------------------------------------------------
# Event CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=EventRead, status_code=201)
def create_event(
    event_data: EventCreate,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
) -> EventRead:
    """Create a new event. Admin only."""
    filters_dict = _serialize_review_filters(event_data.filters)

    event = Event(
        name=event_data.name,
        description=event_data.description,
        page_context=event_data.page_context,
        filters=filters_dict,
        limit=event_data.limit,
        is_active=event_data.is_active,
        start_date=event_data.start_date,
        end_date=event_data.end_date,
        created_by=current_user.id,
    )

    session.add(event)
    session.commit()
    session.refresh(event)

    logger.info("Event '%s' created by admin %s", event.name, current_user.id)
    return jsonable_encoder(EventRead.model_validate(event))


@router.get("/current", response_model=Optional[EventRead])
def get_current_event(
    session: SessionDep,
    x_page_route: str | None = Header(
        None,
        description="Client page route (e.g. 'doc_digitization')",
    ),
    current_user: User = Depends(require_any_role()),
) -> EventRead | None:
    """Return the current active event for the supplied page route header.

    Returns null when no active event matches the route or the event falls
    outside its scheduled window. Returns 409 if multiple active events match.
    """
    if not x_page_route:
        return None

    now = datetime.now(timezone.utc)
    candidates = session.exec(
        select(Event).where(
            Event.page_context == x_page_route,
            Event.is_active == True,  # noqa: E712
        )
    ).all()
    active_events = [
        event
        for event in candidates
        if not (
            (event.start_date and event.start_date > now)
            or (event.end_date and event.end_date < now)
        )
    ]

    if not active_events:
        return None
    if len(active_events) > 1:
        raise HTTPException(
            status_code=409,
            detail="Multiple active events found for this page context",
        )

    return jsonable_encoder(EventRead.model_validate(active_events[0]))


@router.get("/", response_model=list[EventRead])
def list_events(
    session: SessionDep,
    page_context: str | None = Query(
        None,
        description="Filter by page context",
    ),
    is_active: bool | None = Query(
        None,
        description="Filter by active status",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin()),
) -> list[EventRead]:
    """List all events. Admin only."""
    query = select(Event)

    if page_context is not None:
        query = query.where(Event.page_context == page_context)
    if is_active is not None:
        query = query.where(Event.is_active == is_active)  # noqa: E712

    query = query.order_by(text("created_at DESC")).offset(skip).limit(limit)

    events = session.exec(query).all()
    return jsonable_encoder([EventRead.model_validate(e) for e in events])


@router.get("/{event_id}", response_model=EventRead)
def get_event(
    event_id: UUID,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
) -> EventRead:
    """Get a specific event by ID. Admin only."""
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return jsonable_encoder(EventRead.model_validate(event))


@router.put("/{event_id}", response_model=EventRead)
def update_event(
    event_id: UUID,
    event_data: EventUpdate,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
) -> EventRead:
    """Update an event. Admin only."""
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    update_dict = event_data.model_dump(exclude_unset=True)

    if "filters" in update_dict and update_dict["filters"] is not None:
        update_dict["filters"] = _serialize_review_filters(event_data.filters)

    for field, value in update_dict.items():
        setattr(event, field, value)

    event.updated_at = datetime.now(timezone.utc)

    session.add(event)
    session.commit()
    session.refresh(event)

    logger.info("Event %s updated by admin %s", event_id, current_user.id)
    return jsonable_encoder(EventRead.model_validate(event))


@router.delete("/{event_id}", status_code=204)
def deactivate_event(
    event_id: UUID,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
) -> None:
    """Deactivate an event (soft delete). Admin only."""
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.is_active = False
    event.updated_at = datetime.now(timezone.utc)

    session.add(event)
    session.commit()

    logger.info("Event %s deactivated by admin %s", event_id, current_user.id)

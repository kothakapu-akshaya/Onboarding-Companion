"""Points service for rewarding user activity."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.db.session import Session
from app.models.points import PointsEvent
from app.models.record import Record
from app.models.user import User


def award_for_record(
    session: Session, record: Record, base_points: int = 1
) -> None:
    """Award points for creating a record."""
    if not getattr(record, "user_id", None) or not getattr(record, "uid", None):
        return

    # Check if points have already been awarded for this record
    existing_event = session.exec(
        select(PointsEvent).where(PointsEvent.record_uid == record.uid)
    ).first()
    if existing_event:
        return  # Points already awarded, do nothing

    user = session.get(User, record.user_id)
    if not user:
        return

    # Determine current multiplier and if a streak is active
    now = datetime.now(timezone.utc)
    current_multiplier = 1.0
    is_streak_active = False
    if user.streak_expires_at:
        streak_expires_at_aware = user.streak_expires_at
        if streak_expires_at_aware.tzinfo is None:
            streak_expires_at_aware = streak_expires_at_aware.replace(
                tzinfo=timezone.utc
            )

        if streak_expires_at_aware > now:
            is_streak_active = True
            current_multiplier = user.streak_multiplier

    # Calculate points to award (using the multiplier *before* this upload)
    points_to_award = round(base_points * current_multiplier, 1)

    event = PointsEvent(
        user_id=record.user_id,
        record_uid=record.uid,
        points=points_to_award,
        reason="record_created",
    )
    session.add(event)
    try:
        session.flush()  # Check unique(record_uid) without full commit

        # Update the user's streak
        if is_streak_active:
            # If streak is active, just increment the multiplier
            user.streak_multiplier = round(user.streak_multiplier + 0.1, 1)
        else:
            # If no active streak, start a new one
            user.streak_multiplier = (
                1.1  # Start at 1.0, first upload makes it 1.1
            )
            user.streak_expires_at = now + timedelta(hours=24)

        session.add(user)

    except IntegrityError:
        session.rollback()  # already awarded; ignore


def award_for_edit(
    session: Session, record: Record, editor_id, base_points: int = 1
) -> None:
    """Award points for editing/patching a record.

    Unlike award_for_record, this can be called multiple times for the
    same record since edits are tracked separately.
    """
    if not getattr(record, "uid", None) or not editor_id:
        return

    user = session.get(User, editor_id)
    if not user:
        return

    # Determine current multiplier and if a streak is active
    now = datetime.now(timezone.utc)
    current_multiplier = 1.0
    is_streak_active = False
    if user.streak_expires_at:
        streak_expires_at_aware = user.streak_expires_at
        if streak_expires_at_aware.tzinfo is None:
            streak_expires_at_aware = streak_expires_at_aware.replace(
                tzinfo=timezone.utc
            )

        if streak_expires_at_aware > now:
            is_streak_active = True
            current_multiplier = user.streak_multiplier

    # Calculate points to award (using the multiplier *before* this edit)
    points_to_award = round(base_points * current_multiplier, 1)

    # Create points event without the unique record_uid constraint
    # record_uid is None so multiple events can be created for edits
    event = PointsEvent(
        user_id=editor_id,
        record_uid=None,  # Not tied to unique constraint for edits
        points=points_to_award,
        reason="record_edited",
    )
    session.add(event)
    try:
        session.flush()

        # Update the user's streak
        if is_streak_active:
            # If streak is active, just increment the multiplier
            user.streak_multiplier = round(user.streak_multiplier + 0.1, 1)
        else:
            # If no active streak, start a new one
            user.streak_multiplier = (
                1.1  # Start at 1.0, first upload makes it 1.1
            )
            user.streak_expires_at = now + timedelta(hours=24)

        session.add(user)

    except IntegrityError:
        session.rollback()  # should not happen for edits, but handle gracefully

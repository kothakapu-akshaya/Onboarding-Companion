import json
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from geoalchemy2.shape import to_shape
from sqlalchemy import func
from sqlmodel import col, select

from app.core.auth import get_password_hash, verify_password
from app.core.exceptions import DuplicateEntry, UserNotFound
from app.core.rbac_fastapi import (
    get_current_active_user,
    get_user_roles,
    require_admin,
    require_users_delete,
    require_users_read,
    require_users_update,
    require_users_write,
)
from app.core.validators import validate_phone
from app.db.session import SessionDep
from app.models.associations import UserRoleLink
from app.models.record import MediaType, Record
from app.models.record_history import RecordHistory
from app.models.role import Role
from app.models.user import User
from app.models.user_follow import UserFollow
from app.schemas import (
    ContirbutionMediaCountResponse,
    ContributionFilterRead,
    ContributionRead,
    ContributionResponse,
    FollowersList,
    FollowingList,
    MessageResponse,
    RoleRead,
    UserPasswordChangeRequest,
    UserRead,
    UserReadWithRole,
    UserStreaks,
    UserUpdate,
    filter_user_privacy,
)
from app.schemas.geo_schemas import Coordinates
from app.services.extracted_text_resolver import ExtractedTextResolver
from app.services.language_service import LanguageService
from app.services.record_history_service import RecordHistoryService
from app.services.streak_service import StreakService

router = APIRouter()


def _empty_compute_stats() -> dict[str, int]:
    return {
        "audio_duration": 0,
        "audio_count": 0,
        "video_duration": 0,
        "video_count": 0,
        "text_count": 0,
        "document_count": 0,
        "image_count": 0,
    }


def _empty_activity_counts(prefix: str) -> dict[str, int]:
    return {
        f"{prefix}_audio_count": 0,
        f"{prefix}_video_count": 0,
        f"{prefix}_text_count": 0,
        f"{prefix}_document_count": 0,
        f"{prefix}_image_count": 0,
    }


def _segments_have_content(segments: Any) -> bool:
    if not isinstance(segments, list):
        return False

    for segment in segments:
        if not isinstance(segment, dict):
            if segment not in (None, "", [], {}):
                return True
            continue

        if segment.get("text"):
            return True
        if segment.get("words"):
            return True

    return False


def _has_populated_extracted_text(serialized_value: Any) -> bool:
    if serialized_value in (None, "", "None", "null"):
        return False

    parsed_value = serialized_value
    if isinstance(serialized_value, str):
        stripped = serialized_value.strip()
        if stripped in ("", "None", "null"):
            return False
        if stripped.startswith(("{", "[")):
            try:
                parsed_value = json.loads(stripped)
            except json.JSONDecodeError:
                return bool(stripped)
        else:
            return bool(stripped)

    if isinstance(parsed_value, dict):
        if _segments_have_content(parsed_value.get("segments")):
            return True
        if parsed_value.get("summary"):
            return True
        if parsed_value.get("notes"):
            return True
        if parsed_value.get("named_entities"):
            return True
        return False

    if isinstance(parsed_value, list):
        return _segments_have_content(parsed_value)

    return bool(parsed_value)


def _bucket_name_for_media_type(media_type: MediaType | str) -> str | None:
    media_value = (
        media_type.value if hasattr(media_type, "value") else media_type
    )
    if media_value in {"audio", "video", "text", "document", "image"}:
        return str(media_value)
    return None


def _classify_history_activity(
    history_entry: RecordHistory,
) -> str | None:
    field_changes = history_entry.field_changes or {}
    if not field_changes:
        return None

    extracted_text_change = field_changes.get("extracted_text")
    if extracted_text_change is None:
        return "edit"

    old_value = extracted_text_change.get("old")
    if _has_populated_extracted_text(old_value):
        return "review"

    return None


def get_user_by_identifier(session: SessionDep, identifier: str) -> User:
    """Get user by UUID or username.

    Args:
        session: Database session
        identifier: Either a UUID string or username

    Returns:
        User object

    Raises:
        UserNotFound: If user is not found
    """
    # Try to parse as UUID first
    try:
        user_uuid = UUID(identifier)
        user = session.get(User, user_uuid)
        if user:
            return user
    except ValueError:
        # Not a valid UUID, try username
        pass

    # Try as username
    statement = select(User).where(User.username == identifier.lower())
    user = session.exec(statement).first()

    if not user:
        raise UserNotFound(identifier)

    return user


@router.get("/", response_model=list[UserRead])
async def get_users(
    session: SessionDep,
    current_user: User = Depends(require_admin()),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of users to return"
    ),
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    profession: str | None = Query(None, description="Filter by profession"),
    organisation: str | None = Query(
        None, description="Filter by organisation"
    ),
):
    """Get all users with pagination and optional filters."""
    statement = select(User)

    # Apply filters if provided
    if user_id:
        statement = statement.where(User.id == user_id)
    if profession:
        statement = statement.where(
            col(User.profession).ilike(f"%{profession}%")
        )
    if organisation:
        statement = statement.where(
            col(User.organisation).ilike(f"%{organisation}%")
        )

    # Note: Place-based filtering requires geographic queries and is not
    # implemented yet

    # Apply pagination
    statement = statement.offset(skip).limit(limit)
    users = session.exec(statement).all()

    # Check if current user is admin
    user_roles = get_user_roles(current_user.id)
    is_admin = "admin" in user_roles

    processed_users = []
    for user in users:
        user_dict = user.model_dump()

        if not user_dict.get("name") or user_dict["name"].strip() == "":
            user_dict["name"] = (
                f"User {user_dict['phone'][-4:]}"  # Use last 4 digits of phone
            )

        # Apply privacy filtering
        filtered_user_dict = filter_user_privacy(
            user_dict, current_user.id, is_admin
        )
        processed_users.append(UserRead.model_validate(filtered_user_dict))

    return processed_users


@router.get("/search", response_model=list[dict])
def search_users(
    session: SessionDep,
    query: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Search query string for username",
    ),
    limit: int = Query(
        10, ge=1, le=100, description="Number of users to return (max 100)"
    ),
    current_user: User = Depends(get_current_active_user),
) -> list[dict]:
    """Search users by similarity with username.

    Return usernames which match the query.
    """
    # Use SQLAlchemy functions to call PostgreSQL similarity function securely
    similarity_username = func.similarity(User.username, query)

    search_query = (
        select(User.username)
        .where(similarity_username > 0.1)
        .order_by(similarity_username.desc())
        .limit(limit)
    )

    # Execute the query using SQLAlchemy ORM approach
    result = session.exec(search_query).all()

    # Process results and return usernames
    usernames = []
    for username in result:
        usernames.append({"username": username})

    return usernames


@router.get("/{user_identifier}", response_model=UserReadWithRole)
async def get_user(
    session: SessionDep,
    user_identifier: str = Path(
        ..., description="User UUID, username, or phone number"
    ),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific user by ID, username, or phone number.

    - Any user can always get any user profile.
    - Phone and email are filtered based on privacy settings unless admin
      or self.
    - role/roles fields are only populated for the requesting user themselves
      or for admins, consistent with the dedicated roles endpoint.
    """
    # Try as phone number if it looks like one (starts with + or digits)
    user = None
    is_phone_format = user_identifier.startswith("+") or (
        user_identifier.replace("+", "").isdigit()
    )
    if is_phone_format:
        try:
            normalized_phone = validate_phone(user_identifier)
            statement = select(User).where(User.phone == normalized_phone)
            user = session.exec(statement).first()
        except ValueError:
            # Not a valid phone number format, will fallback to ID/username
            pass

    if not user:
        user = get_user_by_identifier(session, user_identifier)

    # Check if current user is admin
    user_roles = get_user_roles(current_user.id)
    is_admin = "admin" in user_roles
    is_self = current_user.id == user.id

    # Apply privacy filtering
    user_dict = user.model_dump()
    filtered_user_dict = filter_user_privacy(
        user_dict, current_user.id, is_admin
    )

    # Only expose role membership to the user themselves or admins,
    # matching the access level of the dedicated roles endpoint.
    if is_admin or is_self:
        roles = get_user_roles(user.id)
        filtered_user_dict["roles"] = roles
        filtered_user_dict["role"] = next(
            (r for r in ("admin", "reviewer", "user", "system") if r in roles),
            roles[0] if roles else None,
        )

    return UserReadWithRole.model_validate(filtered_user_dict)


@router.put("/{user_identifier}", response_model=UserRead)
async def update_user(
    session: SessionDep,
    user_identifier: str = Path(..., description="User UUID or username"),
    user_update: UserUpdate = Body(...),
    current_user: User = Depends(get_current_active_user),
):
    """Update a user."""
    user = get_user_by_identifier(session, user_identifier)

    # SECURITY FIX: Authorization check implemented
    user_roles = get_user_roles(current_user.id)
    is_admin = "admin" in user_roles
    is_updating_own_profile = current_user.id == user.id

    if not is_updating_own_profile and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Not authorized to update another user's profile. "
                "Only admins can update other users' profiles."
            ),
        )

    # Check email uniqueness if being updated
    if user_update.email and user_update.email != user.email:
        statement = select(User).where(User.email == user_update.email)
        existing_email = session.exec(statement).first()

        if existing_email:
            raise DuplicateEntry("Email", user_update.email)

    # Check username uniqueness if being updated
    if user_update.username and user_update.username != user.username:
        statement = select(User).where(User.username == user_update.username)
        existing_username = session.exec(statement).first()

        if existing_username:
            raise DuplicateEntry("Username", user_update.username)

    # Update user fields
    update_data = user_update.model_dump(exclude_unset=True)

    if update_data.get("language_proficiencies") is not None:
        try:
            LanguageService.validate_language_proficiencies(
                session, update_data["language_proficiencies"]
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Handle JSON field serialization for Pydantic models.
    from fastapi.encoders import jsonable_encoder

    for field, value in update_data.items():
        if field in [
            "places_lived",
            "from_place",
            "social_media_profiles",
            "language_proficiencies",
        ]:
            if value is not None:
                # Use jsonable_encoder to ensure proper serialization
                # to JSON-compatible format
                setattr(user, field, jsonable_encoder(value))
            else:
                setattr(user, field, value)
        else:
            setattr(user, field, value)

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# Role management endpoints
@router.get("/{user_identifier}/roles", response_model=list[RoleRead])
async def get_user_roles_endpoint(
    user_identifier: str,
    session: SessionDep,
    current_user: User = Depends(require_users_read()),
):
    """Get all roles assigned to a user."""
    user = get_user_by_identifier(session, user_identifier)
    if not user:
        raise UserNotFound(str(user_identifier))

    # Get roles through association table
    statement = (
        select(Role).join(UserRoleLink).where(UserRoleLink.user_id == user.id)
    )
    roles = session.exec(statement).all()
    return roles


@router.post("/{user_identifier}/roles", response_model=list[RoleRead])
async def assign_roles_to_user(
    user_identifier: str,
    role_ids: list[int],
    session: SessionDep,
    current_user: User = Depends(require_users_write()),
):
    """Assign roles to a user."""
    user = get_user_by_identifier(session, user_identifier)
    if not user:
        raise UserNotFound(str(user_identifier))

    # Verify all roles exist
    for role_id in role_ids:
        role = session.get(Role, role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role with id {role_id} not found",
            )

    # Clear existing roles for this user
    delete_statement = select(UserRoleLink).where(
        UserRoleLink.user_id == user.id
    )
    existing_links = session.exec(delete_statement).all()
    for link in existing_links:
        session.delete(link)

    # Add new role assignments
    for role_id in role_ids:
        user_role_link = UserRoleLink(user_id=user.id, role_id=role_id)
        session.add(user_role_link)

    session.commit()

    # Return the assigned roles
    statement = (
        select(Role).join(UserRoleLink).where(UserRoleLink.user_id == user.id)
    )
    roles = session.exec(statement).all()
    return roles


@router.put("/{user_identifier}/roles/add", response_model=list[RoleRead])
async def add_role_to_user(
    user_identifier: str,
    role_id: int,
    session: SessionDep,
    current_user: User = Depends(require_users_update()),
):
    """Add a single role to a user (keeping existing roles)."""
    user = get_user_by_identifier(session, user_identifier)
    if not user:
        raise UserNotFound(str(user_identifier))

    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role with id {role_id} not found",
        )

    # Check if user already has this role
    existing_link_statement = select(UserRoleLink).where(
        UserRoleLink.user_id == user.id, UserRoleLink.role_id == role_id
    )
    existing_link = session.exec(existing_link_statement).first()

    if not existing_link:
        # Add the role assignment
        user_role_link = UserRoleLink(user_id=user.id, role_id=role_id)
        session.add(user_role_link)
        session.commit()

    # Return all roles for this user
    statement = (
        select(Role).join(UserRoleLink).where(UserRoleLink.user_id == user.id)
    )
    roles = session.exec(statement).all()
    return roles


@router.delete(
    "/{user_identifier}/roles/{role_id}", response_model=list[RoleRead]
)
async def remove_role_from_user(
    user_identifier: str,
    role_id: int,
    session: SessionDep,
    current_user: User = Depends(require_users_delete()),
):
    """Remove a role from a user."""
    user = get_user_by_identifier(session, user_identifier)
    if not user:
        raise UserNotFound(str(user_identifier))

    role = session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role with id {role_id} not found",
        )

    # Find and remove the role assignment
    delete_statement = select(UserRoleLink).where(
        UserRoleLink.user_id == user.id, UserRoleLink.role_id == role_id
    )
    existing_link = session.exec(delete_statement).first()

    if existing_link:
        session.delete(existing_link)
        session.commit()

    # Return remaining roles for this user
    statement = (
        select(Role).join(UserRoleLink).where(UserRoleLink.user_id == user.id)
    )
    roles = session.exec(statement).all()
    return roles


# Contributions endpoints
@router.get("/{user_identifier}/contributions", response_model=ContributionRead)
async def get_user_contributions(
    user_identifier: str,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
):
    """Get all records submitted by a user.

    Allow all authenticated users to access.
    """
    user = get_user_by_identifier(session, user_identifier)
    if not user:
        raise UserNotFound(str(user_identifier))

    statement = select(Record).where(Record.user_id == user.id)
    records = session.scalars(statement).all()
    total_count = len(records)

    # Batch-resolve extracted text source IDs
    fallback_map = ExtractedTextResolver.batch_resolve(records, session)

    # Group counts by media_type
    counts_by_media = {
        "text": 0,
        "audio": 0,
        "image": 0,
        "video": 0,
        "document": 0,
    }
    audio_contributions = []
    video_contributions = []
    text_contributions = []
    image_contributions = []
    document_contributions = []

    audio_duration = 0
    video_duration = 0
    document_pages = 0

    for r in records:
        if r.uid is None:
            continue
        location = None
        if r.location:
            point = to_shape(r.location)  # shapely Point
            location = Coordinates(latitude=point.y, longitude=point.x)
        counts_by_media[r.media_type] += 1
        release_rights = None if r.release_rights == "NA" else r.release_rights
        language = None if r.language in ("NA", "und") else r.language

        extracted_text_source_record_id = None
        if getattr(r, "extracted_text", None) is None and r.uid in fallback_map:
            _, source_rid = fallback_map[r.uid]
            extracted_text_source_record_id = source_rid

        contribution = ContributionResponse(
            id=cast(UUID, r.uid),
            size=r.file_size or 0,
            category_ids=r.category_ids or [],
            reviewed=r.reviewed,
            title=r.title,
            description=r.description,
            duration=r.duration_seconds,
            timestamp=r.created_at,
            location=location,
            release_rights=release_rights,
            language=language,
            file_hash=r.file_hash,
            snr_frequency=r.snr_frequency,
            tagged_usernames=r.tagged_usernames,
            hashtags=r.hashtags,
            record_tags=r.record_tags,
            extracted_text_source_record_id=extracted_text_source_record_id,
        )
        if r.media_type == "audio":
            audio_contributions.append(contribution)
        elif r.media_type == "video":
            video_contributions.append(contribution)
        elif r.media_type == "text":
            text_contributions.append(contribution)
        elif r.media_type == "image":
            image_contributions.append(contribution)
        elif r.media_type == "document":
            document_contributions.append(contribution)

        if r.media_type == "audio":
            audio_duration += r.duration_seconds or 0
        elif r.media_type == "video":
            video_duration += r.duration_seconds or 0
        elif r.media_type == "document":
            document_pages += r.page_count or 0

    counts_obj = ContirbutionMediaCountResponse(
        text=counts_by_media["text"],
        audio=counts_by_media["audio"],
        image=counts_by_media["image"],
        video=counts_by_media["video"],
        document=counts_by_media["document"],
    )

    # Volunteer "compute" work: records this user submitted or corrected
    # extracted text for (transcription/OCR/captioning), regardless of who
    # originally uploaded the record. Identified via RecordHistory entries
    # the user authored that touched the `extracted_text` field.
    activity_history = session.exec(
        select(RecordHistory).where(RecordHistory.changed_by == user.id)
    ).all()
    history_record_ids = {entry.record_id for entry in activity_history}
    history_records_by_id = {}
    if history_record_ids:
        history_records = session.scalars(
            select(Record).where(col(Record.uid).in_(history_record_ids))
        ).all()
        history_records_by_id = {
            record.uid: record for record in history_records
        }

    compute_record_ids = {
        entry.record_id
        for entry in activity_history
        if "extracted_text" in (entry.field_changes or {})
    }
    compute_stats = _empty_compute_stats()
    for record_id in compute_record_ids:
        record = history_records_by_id.get(record_id)
        if record is None:
            continue
        media_bucket = _bucket_name_for_media_type(record.media_type)
        if media_bucket is None:
            continue
        compute_stats[f"{media_bucket}_count"] += 1
        if media_bucket == "audio":
            compute_stats["audio_duration"] += record.duration_seconds or 0
        elif media_bucket == "video":
            compute_stats["video_duration"] += record.duration_seconds or 0

    edit_stats = _empty_activity_counts("edit")
    review_stats = _empty_activity_counts("review")
    for history_entry in activity_history:
        activity_kind = _classify_history_activity(history_entry)
        if activity_kind is None:
            continue

        record = history_records_by_id.get(history_entry.record_id)
        if record is None:
            continue

        media_bucket = _bucket_name_for_media_type(record.media_type)
        if media_bucket is None:
            continue

        if activity_kind == "edit":
            edit_stats[f"edit_{media_bucket}_count"] += 1
        elif activity_kind == "review":
            review_stats[f"review_{media_bucket}_count"] += 1

    return ContributionRead(
        user_id=user.id,
        total_contributions=total_count,
        contributions_by_media_type=counts_obj,
        audio_contributions=audio_contributions or None,
        video_contributions=video_contributions or None,
        document_contributions=document_contributions or None,
        text_contributions=text_contributions or None,
        image_contributions=image_contributions or None,
        audio_duration=audio_duration,
        video_duration=video_duration,
        document_pages=document_pages,
        credits=user.credits,
        compute_audio_duration=compute_stats["audio_duration"],
        compute_audio_count=compute_stats["audio_count"],
        compute_video_duration=compute_stats["video_duration"],
        compute_video_count=compute_stats["video_count"],
        compute_text_count=compute_stats["text_count"],
        compute_document_count=compute_stats["document_count"],
        compute_image_count=compute_stats["image_count"],
        edit_audio_count=edit_stats["edit_audio_count"],
        edit_video_count=edit_stats["edit_video_count"],
        edit_text_count=edit_stats["edit_text_count"],
        edit_document_count=edit_stats["edit_document_count"],
        edit_image_count=edit_stats["edit_image_count"],
        review_audio_count=review_stats["review_audio_count"],
        review_video_count=review_stats["review_video_count"],
        review_text_count=review_stats["review_text_count"],
        review_document_count=review_stats["review_document_count"],
        review_image_count=review_stats["review_image_count"],
    )


@router.get(
    "/{user_identifier}/contributions/{media_type}",
    response_model=ContributionFilterRead,
)
async def get_user_contributions_by_media(
    user_identifier: str,
    session: SessionDep,
    media_type: MediaType,
    current_user: User = Depends(
        get_current_active_user
    ),  # Allow any authenticated user
):
    """Get records by media type. Allow all authenticated users to access."""
    user = get_user_by_identifier(session, user_identifier)
    if not user:
        raise UserNotFound(str(user_identifier))

    statement = select(Record).where(
        Record.user_id == user.id, Record.media_type == media_type
    )
    records = session.scalars(statement).all()
    total_count = len(records)

    # Batch-resolve extracted text source IDs
    fallback_map = ExtractedTextResolver.batch_resolve(records, session)

    contributions = []

    for r in records:
        if r.uid is None:
            continue
        location = None
        if r.location:
            point = to_shape(
                r.location
            )  # Convert WKTElement to a shapely Point
            location = Coordinates(latitude=point.y, longitude=point.x)

        release_rights = None if r.release_rights == "NA" else r.release_rights
        language = None if r.language in ("NA", "und") else r.language

        extracted_text_source_record_id = None
        if getattr(r, "extracted_text", None) is None and r.uid in fallback_map:
            _, source_rid = fallback_map[r.uid]
            extracted_text_source_record_id = source_rid

        contribution = ContributionResponse(
            id=cast(UUID, r.uid),
            size=r.file_size or 0,
            category_ids=r.category_ids or [],
            reviewed=r.reviewed,
            title=r.title,
            description=r.description,
            duration=r.duration_seconds,
            timestamp=r.created_at,
            location=location,
            release_rights=release_rights,
            language=language,
            file_hash=r.file_hash,
            snr_frequency=r.snr_frequency,
            extracted_text_source_record_id=extracted_text_source_record_id,
        )
        contributions.append(contribution)

    # Return the final response object containing the list of detailed
    # contributions
    return ContributionFilterRead(
        user_id=user.id,
        total_contributions=total_count,
        contributions=contributions or None,
    )


# Password change endpoint - SECURITY FIX APPLIED
@router.put(
    "/{user_identifier}/change-password", response_model=MessageResponse
)
async def change_user_password(
    user_identifier: str,
    password_data: UserPasswordChangeRequest,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
):
    """Change a user's password."""
    # SECURITY FIX: Authorization check implemented
    user = get_user_by_identifier(session, user_identifier)
    user_roles = get_user_roles(current_user.id)
    is_admin = "admin" in user_roles
    is_changing_own_password = current_user.id == user.id

    if not is_changing_own_password and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Not authorized to change another user's password. "
                "Only admins can change other users' passwords."
            ),
        )

    # Validate password confirmation
    if password_data.new_password != password_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match",
        )

    # Find target user
    if not user:
        raise UserNotFound(str(user_identifier))

    # Password verification logic:
    # - If user is changing their own password: verify their current password
    # - If admin is changing another user's password: no current password needed
    if is_changing_own_password:
        # Verify current password of the user changing their own password
        if not verify_password(
            password_data.current_password, user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password",
            )

        # Prevent using the same password as new password
        if verify_password(password_data.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be the same as current password",
            )
    else:
        # Admin changing another user's password - current_password
        # field ignored
        # Design choice: admins don't need to know the user's current password

        # Even for admin changes, prevent using the same password as
        # new password
        if verify_password(password_data.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be the same as current password",
            )

    # Update target user's password
    user.hashed_password = get_password_hash(password_data.new_password)
    session.add(user)
    session.commit()

    return MessageResponse(message="Password changed successfully")


# Follow/Unfollow endpoints
@router.post("/{user_identifier}/follow", response_model=MessageResponse)
async def follow_user(
    user_identifier: str,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
):
    """Follow a user."""
    # Get target user by identifier
    target_user = get_user_by_identifier(session, user_identifier)

    # Prevent self-following
    if current_user.id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot follow yourself",
        )

    # Check if target user exists
    if not target_user:
        raise UserNotFound(str(user_identifier))

    # Check if already following
    existing_follow = session.exec(
        select(UserFollow).where(
            UserFollow.follower_id == current_user.id,
            UserFollow.following_id == target_user.id,
        )
    ).first()

    if existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already following this user",
        )

    # Create follow relationship
    follow = UserFollow(
        follower_id=current_user.id, following_id=target_user.id
    )
    session.add(follow)
    session.commit()

    return MessageResponse(message="Successfully followed user")


@router.delete("/{user_identifier}/follow", response_model=MessageResponse)
async def unfollow_user(
    user_identifier: str,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
):
    """Unfollow a user."""
    # Get target user by identifier
    target_user = get_user_by_identifier(session, user_identifier)

    # Check if target user exists
    if not target_user:
        raise UserNotFound(str(user_identifier))

    # Find existing follow relationship
    existing_follow = session.exec(
        select(UserFollow).where(
            UserFollow.follower_id == current_user.id,
            UserFollow.following_id == target_user.id,
        )
    ).first()

    if not existing_follow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not following this user",
        )

    # Remove follow relationship
    session.delete(existing_follow)
    session.commit()

    return MessageResponse(message="Successfully unfollowed user")


@router.get("/{user_identifier}/followers", response_model=FollowersList)
async def get_user_followers(
    user_identifier: str,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of followers to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of followers to return"
    ),
):
    """Get users following a specific user."""
    # Get target user by identifier
    target_user = get_user_by_identifier(session, user_identifier)
    if not target_user:
        raise UserNotFound(str(user_identifier))

    # Get followers with pagination
    followers_query = (
        select(UserFollow, User)
        .join(User, col(UserFollow.follower_id) == col(User.id))
        .where(UserFollow.following_id == target_user.id)
        .offset(skip)
        .limit(limit)
    )

    followers_data = session.exec(followers_query).all()

    # Check if current user is admin
    user_roles = get_user_roles(current_user.id)
    is_admin = "admin" in user_roles

    followers = []
    for follow_rel, user in followers_data:
        user_dict = user.model_dump()
        filtered_user_dict = filter_user_privacy(
            user_dict, current_user.id, is_admin
        )
        followers.append(UserRead.model_validate(filtered_user_dict))

    # Get total count
    total_count = session.exec(
        select(UserFollow).where(UserFollow.following_id == target_user.id)
    ).all()

    return FollowersList(
        user_id=target_user.id,
        followers_count=len(total_count),
        followers=followers,
    )


@router.get("/{user_identifier}/following", response_model=FollowingList)
async def get_user_following(
    user_identifier: str,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    skip: int = Query(0, ge=0, description="Number of following to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Number of following to return"
    ),
):
    """Get users that a specific user is following."""
    # Get target user by identifier
    target_user = get_user_by_identifier(session, user_identifier)
    if not target_user:
        raise UserNotFound(str(user_identifier))

    # Get following with pagination
    following_query = (
        select(UserFollow, User)
        .join(User, col(UserFollow.following_id) == col(User.id))
        .where(UserFollow.follower_id == target_user.id)
        .offset(skip)
        .limit(limit)
    )

    following_data = session.exec(following_query).all()

    # Check if current user is admin
    user_roles = get_user_roles(current_user.id)
    is_admin = "admin" in user_roles

    following = []
    for follow_rel, user in following_data:
        user_dict = user.model_dump()
        filtered_user_dict = filter_user_privacy(
            user_dict, current_user.id, is_admin
        )
        following.append(UserRead.model_validate(filtered_user_dict))

    # Get total count
    total_count = session.exec(
        select(UserFollow).where(UserFollow.follower_id == target_user.id)
    ).all()

    return FollowingList(
        user_id=target_user.id,
        following_count=len(total_count),
        following=following,
    )


@router.get("/{user_identifier}/profile")
async def get_user_profile(
    session: SessionDep,
    user_identifier: str = Path(..., description="User UUID or username"),
    include: str | None = Query(
        None,
        description=(
            "Comma-separated list of data to include: streaks, "
            "timeline, summary"
        ),
    ),
    days: int = Query(
        30,
        ge=1,
        le=365,
        description=(
            "Number of days to include in timeline (only used when "
            "include=timeline)"
        ),
    ),
):
    """Get user profile data with optional includes.

    Supported includes: streaks, timeline, summary.
    """
    user = get_user_by_identifier(session, user_identifier)

    # Base user info
    response: dict[str, Any] = {
        "user_id": user.id,
        "user_name": user.name,
        "username": user.username,
    }

    # Parse include parameter
    includes = []
    if include:
        includes = [item.strip().lower() for item in include.split(",")]

    # Include streaks data
    if "streaks" in includes:
        streak_service = StreakService(session)
        try:
            streak_data = streak_service.get_user_streaks(user.id)
            streaks = UserStreaks(**streak_data)
            response["streaks"] = {
                "contributions_streak": {
                    "current": (streaks.contributions_streak.current_streak),
                    "longest": (streaks.contributions_streak.longest_streak),
                    "total_active_days": (
                        streaks.contributions_streak.total_active_days
                    ),
                    "last_activity": (
                        streaks.contributions_streak.last_activity_date
                    ),
                },
                "edits_streak": {
                    "current": streaks.edits_streak.current_streak,
                    "longest": streaks.edits_streak.longest_streak,
                    "total_active_days": streaks.edits_streak.total_active_days,
                    "last_activity": streaks.edits_streak.last_activity_date,
                },
                "combined_streak": {
                    "current": (streaks.combined_streak.current_streak),
                    "longest": (streaks.combined_streak.longest_streak),
                    "total_active_days": (
                        streaks.combined_streak.total_active_days
                    ),
                    "last_activity": streaks.combined_streak.last_activity_date,
                },
            }
        except Exception:
            # Return empty streaks if calculation fails
            response["streaks"] = {
                "contributions_streak": {
                    "current": 0,
                    "longest": 0,
                    "total_active_days": 0,
                    "last_activity": None,
                },
                "edits_streak": {
                    "current": 0,
                    "longest": 0,
                    "total_active_days": 0,
                    "last_activity": None,
                },
                "combined_streak": {
                    "current": 0,
                    "longest": 0,
                    "total_active_days": 0,
                    "last_activity": None,
                },
            }

    # Include timeline data
    if "timeline" in includes:
        streak_service = StreakService(session)
        try:
            activity_data = streak_service.get_daily_activity_counts(
                user.id, days=days
            )
            total_contributions = sum(
                cast(int, day["contributions_count"]) for day in activity_data
            )
            total_edits = sum(
                cast(int, day["edits_count"]) for day in activity_data
            )
            total_activities = sum(
                cast(int, day["combined_count"]) for day in activity_data
            )
            total_days_active = sum(
                1 for day in activity_data if cast(bool, day["has_activity"])
            )
            response["timeline"] = {
                "user_id": user.id,
                "user_name": user.name,
                "username": user.username,
                "days_requested": days,
                "activity_data": activity_data,
                "summary": {
                    "total_days_active": total_days_active,
                    "total_contributions": total_contributions,
                    "total_edits": total_edits,
                    "total_activities": total_activities,
                    "average_daily_activities": (
                        total_activities / days if days > 0 else 0.0
                    ),
                    "most_active_day": None,
                    "least_active_day": None,
                },
            }
        except Exception:
            response["timeline"] = {
                "user_id": user.id,
                "user_name": user.name,
                "username": user.username,
                "days_requested": days,
                "activity_data": [],
                "summary": {
                    "total_days_active": 0,
                    "total_contributions": 0,
                    "total_edits": 0,
                    "total_activities": 0,
                    "average_daily_activities": 0.0,
                    "most_active_day": None,
                    "least_active_day": None,
                },
            }

    # Include summary data
    if "summary" in includes:
        # Get contributions data
        statement = select(Record).where(Record.user_id == user.id)
        records = session.scalars(statement).all()

        total_contributions = len(records)
        contributions_by_media = {
            "text": 0,
            "audio": 0,
            "image": 0,
            "video": 0,
            "document": 0,
        }

        for r in records:
            contributions_by_media[r.media_type] += 1

        # Get edit activity data
        history_service = RecordHistoryService(session)
        try:
            edit_activity = history_service.get_user_edit_activity(user.id)
        except ValueError:
            edit_activity = {
                "user_id": user.id,
                "user_name": user.name,
                "username": user.username,
                "total_edits": 0,
                "recent_edits": 0,
                "records_edited": 0,
                "last_edit_date": None,
                "average_edits_per_record": 0.0,
            }

        response["summary"] = {
            "contributions": {
                "total_contributions": total_contributions,
                "contributions_by_media_type": contributions_by_media,
            },
            "edits": {
                "total_edits": edit_activity["total_edits"],
                "recent_edits": edit_activity["recent_edits"],
                "records_edited": edit_activity["records_edited"],
                "last_edit_date": edit_activity["last_edit_date"],
                "average_edits_per_record": edit_activity[
                    "average_edits_per_record"
                ],
            },
            "overall": {
                "total_activities": (
                    total_contributions
                    + cast(int, edit_activity["total_edits"])
                ),
                "activity_ratio": {
                    "contributions": total_contributions,
                    "edits": cast(int, edit_activity["total_edits"]),
                },
            },
        }

    return response

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.core.auth import get_current_active_user
from app.core.cache import cache_service
from app.core.rbac_fastapi import require_admin
from app.db.session import SessionDep
from app.models.course import Course
from app.models.institution import (
    CollegeType,
    District,
    Institution,
    ManagementType,
    Medium,
    Mode,
)
from app.models.user import User
from app.schemas import (
    CourseCreate,
    InstitutionCreate,
    InstitutionEnums,
    InstitutionRead,
    InstitutionRowRead,
)

router = APIRouter()

INSTITUTIONS_CACHE_PREFIX = "institutions"
INSTITUTIONS_CACHE_TTL = 300  # 5 minutes


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


def _build_courses(institution_in: InstitutionCreate) -> list[CourseCreate]:
    courses = list(institution_in.courses)
    if institution_in.course_name or institution_in.mode is not None:
        courses.append(
            CourseCreate(
                course_name=institution_in.course_name,
                option_a_bucket=institution_in.option_a_bucket,
                option_b_bucket=institution_in.option_b_bucket,
                option_c_bucket=institution_in.option_c_bucket,
                option_d_bucket=institution_in.option_d_bucket,
                mode=institution_in.mode,
                cbcs=institution_in.cbcs,
                revised_intake=institution_in.revised_intake,
            )
        )
    return courses


@router.post("", response_model=InstitutionRead)
def create_institution(
    *,
    session: SessionDep,
    current_user: User = Depends(require_admin()),
    institution_in: InstitutionCreate,
):
    """Create a new institution or add courses to an existing one."""
    normalized_university = _normalize_text(institution_in.university_name)
    normalized_college = _normalize_text(institution_in.college_name)

    if normalized_university is None or normalized_college is None:
        raise HTTPException(
            status_code=400, detail="University and college names are required"
        )

    university_name = normalized_university.upper()
    college_name = normalized_college.lower()

    existing = session.exec(
        select(Institution)
        .options(selectinload(Institution.courses))  # type: ignore[bad-argument-type]
        .where(
            col(Institution.university_name) == university_name,
            col(Institution.college_name) == college_name,
            Institution.district == institution_in.district,
        )
    ).first()

    if existing:
        for course_in in _build_courses(institution_in):
            normalized = _normalize_text(course_in.course_name)
            course_in.course_name = normalized.lower() if normalized else None
            existing_course = session.exec(
                select(Course).where(
                    Course.institution_id == existing.id,
                    col(Course.course_name) == course_in.course_name,
                )
            ).first()
            if not existing_course:
                course = Course(
                    **course_in.model_dump(exclude_unset=True),
                    institution_id=existing.id,
                )
                session.add(course)
        session.commit()
        cache_service.invalidate(f"cache:{INSTITUTIONS_CACHE_PREFIX}:*")
        institution = session.exec(
            select(Institution)
            .options(selectinload(Institution.courses))  # type: ignore[bad-argument-type]
            .where(Institution.id == existing.id)
        ).first()
        return institution

    normalized_academic_stream = _normalize_text(institution_in.academic_stream)
    institution = Institution(
        university_name=university_name,
        college_name=college_name,
        academic_stream=normalized_academic_stream.lower()
        if normalized_academic_stream
        else None,
        district=institution_in.district,
        address=_normalize_text(institution_in.address),
        code=institution_in.code,
        college_type=institution_in.college_type,
        management_type=institution_in.management_type,
        medium=institution_in.medium,
    )
    session.add(institution)
    session.flush()

    for course_in in _build_courses(institution_in):
        normalized = _normalize_text(course_in.course_name)
        course_in.course_name = normalized.lower() if normalized else None
        course = Course(
            **course_in.model_dump(exclude_unset=True),
            institution_id=institution.id,
        )
        session.add(course)

    session.commit()
    cache_service.invalidate(f"cache:{INSTITUTIONS_CACHE_PREFIX}:*")
    institution = session.exec(
        select(Institution)
        .options(selectinload(Institution.courses))  # type: ignore[bad-argument-type]
        .where(Institution.id == institution.id)
    ).first()
    return institution


@router.get("", response_model=list[InstitutionRowRead])
def list_institutions(
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    university_name: str | None = Query(None, max_length=200),
    college_name: str | None = Query(None, max_length=300),
    search: str | None = Query(None, max_length=200),
    district: District | None = Query(None),
    college_type: CollegeType | None = Query(None),
    management_type: ManagementType | None = Query(None),
    medium: Medium | None = Query(None),
    mode: Mode | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List institutions with optional filtering and pagination."""
    key_parts = []
    if university_name:
        key_parts.append(f"univ={university_name}")
    if college_name:
        key_parts.append(f"college={college_name}")
    if search:
        key_parts.append(f"search={search}")
    if district:
        key_parts.append(f"district={district}")
    if college_type:
        key_parts.append(f"ctype={college_type}")
    if management_type:
        key_parts.append(f"mtype={management_type}")
    if medium:
        key_parts.append(f"medium={medium}")
    if mode:
        key_parts.append(f"mode={mode}")
    key_parts.append(f"skip={skip}")
    key_parts.append(f"limit={limit}")
    key = cache_service._build_key(
        INSTITUTIONS_CACHE_PREFIX, "list", *key_parts
    )

    def fetch():
        query = select(Institution).options(selectinload(Institution.courses))

        course_filters = []
        if search:
            course_filters.append(col(Course.course_name).ilike(f"%{search}%"))
        if mode:
            course_filters.append(Course.mode == mode)
        if course_filters:
            query = query.join(Course).where(and_(*course_filters))

        if university_name:
            query = query.where(Institution.university_name == university_name)
        if college_name:
            query = query.where(Institution.college_name == college_name)
        if district:
            query = query.where(Institution.district == district)
        if college_type:
            query = query.where(Institution.college_type == college_type)
        if management_type:
            query = query.where(Institution.management_type == management_type)
        if medium:
            query = query.where(Institution.medium == medium)

        query = query.distinct().offset(skip).limit(limit)
        results = session.exec(query).all()
        return [r.model_dump(mode="json") for r in results]

    return cache_service.get_or_set(key, fetch, INSTITUTIONS_CACHE_TTL)


@router.get("/university-names", response_model=list[str])
def list_university_names(
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    search: str | None = Query(None, max_length=200),
    academic_stream: str | None = Query(None, max_length=100),
):
    """List distinct university names with optional search filtering."""
    key_parts = []
    if search:
        key_parts.append(f"search={search}")
    if academic_stream:
        key_parts.append(f"stream={academic_stream}")
    key = cache_service._build_key(
        INSTITUTIONS_CACHE_PREFIX, "university-names", *key_parts
    )

    def fetch():
        query = select(Institution.university_name).distinct()
        if academic_stream:
            query = query.where(Institution.academic_stream == academic_stream)
        if search:
            query = query.where(
                col(Institution.university_name).ilike(f"%{search}%")
            )
        query = query.order_by(Institution.university_name)
        rows = session.exec(query).all()
        return list(rows)

    return cache_service.get_or_set(key, fetch, INSTITUTIONS_CACHE_TTL)


@router.get("/college-names", response_model=list[str])
def list_college_names(
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    university_name: str | None = Query(None, max_length=200),
    search: str | None = Query(None, max_length=300),
):
    """List distinct college names with optional filtering."""
    key_parts = []
    if university_name:
        key_parts.append(f"univ={university_name}")
    if search:
        key_parts.append(f"search={search}")
    key = cache_service._build_key(
        INSTITUTIONS_CACHE_PREFIX, "college-names", *key_parts
    )

    def fetch():
        query = select(Institution.college_name).distinct()
        if university_name:
            query = query.where(Institution.university_name == university_name)
        if search:
            query = query.where(
                col(Institution.college_name).ilike(f"%{search}%")
            )
        query = query.order_by(Institution.college_name)
        rows = session.exec(query).all()
        return list(rows)

    return cache_service.get_or_set(key, fetch, INSTITUTIONS_CACHE_TTL)


@router.get("/enums", response_model=InstitutionEnums)
def get_institution_enums(
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    enum_type: str | None = Query(
        None,
        description=(
            "Filter to a specific enum type: districts, college_types, "
            "management_types, mediums, modes, academic_streams"
        ),
    ),
):
    """Get available enum values for institution filtering."""
    key_parts = []
    if enum_type:
        key_parts.append(f"type={enum_type}")
    key = cache_service._build_key(
        INSTITUTIONS_CACHE_PREFIX, "enums", *key_parts
    )

    def fetch():
        return _fetch_enums(session, enum_type)

    return cache_service.get_or_set(key, fetch, INSTITUTIONS_CACHE_TTL)


def _fetch_enums(
    session: SessionDep,
    enum_type: str | None,
) -> InstitutionEnums:
    """Fetch enum values for institution filtering."""
    if enum_type == "districts":
        return InstitutionEnums(
            districts=[d.value for d in District],
            college_types=[],
            management_types=[],
            mediums=[],
            modes=[],
            academic_streams=[],
        )
    if enum_type == "college_types":
        return InstitutionEnums(
            districts=[],
            college_types=[c.value for c in CollegeType],
            management_types=[],
            mediums=[],
            modes=[],
            academic_streams=[],
        )
    if enum_type == "management_types":
        return InstitutionEnums(
            districts=[],
            college_types=[],
            management_types=[m.value for m in ManagementType],
            mediums=[],
            modes=[],
            academic_streams=[],
        )
    if enum_type == "mediums":
        return InstitutionEnums(
            districts=[],
            college_types=[],
            management_types=[],
            mediums=[m.value for m in Medium],
            modes=[],
            academic_streams=[],
        )
    if enum_type == "modes":
        return InstitutionEnums(
            districts=[],
            college_types=[],
            management_types=[],
            mediums=[],
            modes=[m.value for m in Mode],
            academic_streams=[],
        )
    if enum_type == "academic_streams":
        academic_streams_result = session.exec(
            select(Institution.academic_stream)
            .distinct()
            .where(col(Institution.academic_stream).isnot(None))
            .order_by(Institution.academic_stream)
        ).all()
        academic_streams = [str(s) for s in academic_streams_result if s]
        return InstitutionEnums(
            districts=[],
            college_types=[],
            management_types=[],
            mediums=[],
            modes=[],
            academic_streams=academic_streams,
        )

    academic_streams_result = session.exec(
        select(Institution.academic_stream)
        .distinct()
        .where(col(Institution.academic_stream).isnot(None))
        .order_by(Institution.academic_stream)
    ).all()
    academic_streams = [str(s) for s in academic_streams_result if s]
    return InstitutionEnums(
        districts=[d.value for d in District],
        college_types=[c.value for c in CollegeType],
        management_types=[m.value for m in ManagementType],
        mediums=[m.value for m in Medium],
        modes=[m.value for m in Mode],
        academic_streams=academic_streams,
    )


@router.get("/{id}", response_model=InstitutionRead)
def get_institution(
    id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific institution by ID."""
    key = cache_service._build_key(INSTITUTIONS_CACHE_PREFIX, "id", str(id))

    def fetch():
        institution = session.exec(
            select(Institution)
            .options(selectinload(Institution.courses))
            .where(Institution.id == id)
        ).first()
        if not institution:
            raise HTTPException(status_code=404, detail="Institution not found")
        return institution.model_dump(mode="json")

    return cache_service.get_or_set(key, fetch, INSTITUTIONS_CACHE_TTL)

# app/models/institution.py
import uuid as uuid_pkg
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .course import Course
    from .user import User


class District(str, Enum):
    """District enum."""

    adilabad = "adilabad"
    bhadradri_kothagudem = "bhadradri_kothagudem"
    hyderabad = "hyderabad"
    jagtial = "jagtial"
    jangaon = "jangaon"
    jayashankar_bhupalpally = "jayashankar_bhupalpally"
    jogulamba_gadwal = "jogulamba_gadwal"
    kamareddy = "kamareddy"
    karimnagar = "karimnagar"
    khammam = "khammam"
    komaram_bheem_asifabad = "komaram_bheem_asifabad"
    mahabubabad = "mahabubabad"
    mahabubnagar = "mahabubnagar"
    mancherial = "mancherial"
    medak = "medak"
    medchal_malkajgiri = "medchal_malkajgiri"
    mulugu = "mulugu"
    nagarkurnool = "nagarkurnool"
    nalgonda = "nalgonda"
    narayanpet = "narayanpet"
    nirmal = "nirmal"
    nizamabad = "nizamabad"
    peddapalli = "peddapalli"
    rajanna_sircilla = "rajanna_sircilla"
    ranga_reddy = "ranga_reddy"
    sangareddy = "sangareddy"
    siddipet = "siddipet"
    suryapet = "suryapet"
    vikarabad = "vikarabad"
    wanaparthy = "wanaparthy"
    warangal_rural = "warangal_rural"
    warangal_urban = "warangal_urban"
    yadadri_bhuvanagiri = "yadadri_bhuvanagiri"


class CollegeType(str, Enum):
    """College type enum."""

    co_ed = "co-ed"
    women = "women"


class ManagementType(str, Enum):
    """Management type enum."""

    government = "government"
    government_autonomous = "government (autonomous)"
    private_aided = "private aided"
    private_aided_autonomous = "private aided (autonomous)"
    private_unaided = "private unaided"
    private_unaided_autonomous = "private unaided (autonomous)"
    railway_department = "railway department"
    university_autonomous = "university (autonomous)"
    university_college = "university college"


class Medium(str, Enum):
    """Medium of instruction enum."""

    arabic = "arabic"
    english = "english"
    telugu = "telugu"
    urdu = "urdu"


class Mode(str, Enum):
    """Course mode enum."""

    regular = "regular"
    restructured = "restructured"
    self_financed = "self-financed"


class Institution(SQLModel, table=True):
    """Institution model."""

    id: UUID = Field(default_factory=uuid_pkg.uuid4, primary_key=True)
    university_name: str = Field(max_length=200, nullable=False)
    college_name: str = Field(max_length=300, nullable=False)
    academic_stream: str | None = Field(
        default=None, max_length=100, nullable=True
    )
    district: District | None = Field(default=None, nullable=True)
    address: str | None = Field(default=None, max_length=500)
    code: int | None = Field(default=None)
    college_type: CollegeType | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Enum(
                CollegeType, values_callable=lambda obj: [e.value for e in obj]
            ),
            nullable=True,
        ),
    )
    management_type: ManagementType | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Enum(
                ManagementType,
                values_callable=lambda obj: [e.value for e in obj],
            ),
            nullable=True,
        ),
    )
    medium: Medium | None = Field(
        default=None,
        sa_column=sa.Column(
            sa.Enum(Medium, values_callable=lambda obj: [e.value for e in obj]),
            nullable=True,
        ),
    )

    users: list["User"] = Relationship(back_populates="institution")
    courses: list["Course"] = Relationship(back_populates="institution")

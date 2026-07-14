"""move organisation type to institution academic stream

Revision ID: 9b2c4d6e8f10
Revises: cb1c30b3af47
Create Date: 2026-05-06 11:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b2c4d6e8f10"
down_revision: Union[str, None] = "cb1c30b3af47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


district_enum = sa.Enum(
    "adilabad",
    "bhadradri_kothagudem",
    "hyderabad",
    "jagtial",
    "jangaon",
    "jayashankar_bhupalpally",
    "jogulamba_gadwal",
    "kamareddy",
    "karimnagar",
    "khammam",
    "komaram_bheem_asifabad",
    "mahabubabad",
    "mahabubnagar",
    "mancherial",
    "medak",
    "medchal_malkajgiri",
    "mulugu",
    "nagarkurnool",
    "nalgonda",
    "narayanpet",
    "nirmal",
    "nizamabad",
    "peddapalli",
    "rajanna_sircilla",
    "ranga_reddy",
    "sangareddy",
    "siddipet",
    "suryapet",
    "vikarabad",
    "wanaparthy",
    "warangal_rural",
    "warangal_urban",
    "yadadri_bhuvanagiri",
    name="district",
)
college_type_enum = sa.Enum("co-ed", "women", name="collegetype")
management_type_enum = sa.Enum(
    "government",
    "government (autonomous)",
    "private aided",
    "private aided (autonomous)",
    "private unaided",
    "private unaided (autonomous)",
    "railway department",
    "university (autonomous)",
    "university college",
    name="managementtype",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "institution",
        sa.Column("academic_stream", sa.String(length=100), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE institution "
            "SET academic_stream = :academic_stream "
            "WHERE academic_stream IS NULL"
        ).bindparams(academic_stream="Life Science & Humanities")
    )

    op.alter_column(
        "institution",
        "district",
        existing_type=district_enum,
        nullable=True,
    )
    op.alter_column(
        "institution",
        "college_type",
        existing_type=college_type_enum,
        nullable=True,
    )
    op.alter_column(
        "institution",
        "management_type",
        existing_type=management_type_enum,
        nullable=True,
    )
    op.alter_column(
        "institution",
        "cbcs",
        existing_type=sa.Boolean(),
        nullable=True,
    )

    op.drop_column("user", "organisation_type")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "user", sa.Column("organisation_type", sa.String(length=100), nullable=True)
    )

    op.execute("UPDATE institution SET district = 'adilabad' WHERE district IS NULL")
    op.execute(
        "UPDATE institution SET college_type = 'co-ed' WHERE college_type IS NULL"
    )
    op.execute(
        "UPDATE institution SET management_type = 'government' "
        "WHERE management_type IS NULL"
    )
    op.execute("UPDATE institution SET cbcs = false WHERE cbcs IS NULL")

    op.alter_column(
        "institution",
        "cbcs",
        existing_type=sa.Boolean(),
        nullable=False,
    )
    op.alter_column(
        "institution",
        "management_type",
        existing_type=management_type_enum,
        nullable=False,
    )
    op.alter_column(
        "institution",
        "college_type",
        existing_type=college_type_enum,
        nullable=False,
    )
    op.alter_column(
        "institution",
        "district",
        existing_type=district_enum,
        nullable=False,
    )

    op.drop_column("institution", "academic_stream")

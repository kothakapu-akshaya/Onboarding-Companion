"""create_institutions_table

Revision ID: cb1c30b3af47
Revises: 3d0c5e60c256
Create Date: 2026-04-25 15:23:56.542255

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cb1c30b3af47"
down_revision: Union[str, None] = "3d0c5e60c256"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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

    op.create_table(
        "institution",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("university_name", sa.String(length=200), nullable=False),
        sa.Column("college_name", sa.String(length=300), nullable=False),
        sa.Column("course_name", sa.String(length=200), nullable=True),
        sa.Column("option_a_bucket", sa.String(length=200), nullable=True),
        sa.Column("option_b_bucket", sa.String(length=200), nullable=True),
        sa.Column("option_c_bucket", sa.String(length=200), nullable=True),
        sa.Column("option_d_bucket", sa.String(length=200), nullable=True),
        sa.Column("district", district_enum, nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("code", sa.Integer(), nullable=True),
        sa.Column(
            "college_type",
            sa.Enum("co-ed", "women", name="collegetype"),
            nullable=False,
        ),
        sa.Column(
            "management_type",
            sa.Enum(
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
            ),
            nullable=False,
        ),
        sa.Column(
            "medium",
            sa.Enum("arabic", "english", "telugu", "urdu", name="medium"),
            nullable=True,
        ),
        sa.Column(
            "mode",
            sa.Enum("regular", "restructured", "self-financed", name="mode"),
            nullable=True,
        ),
        sa.Column("cbcs", sa.Boolean(), nullable=False),
        sa.Column("revised_intake", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("user", sa.Column("institution_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_user_institution_id", "user", "institution", ["institution_id"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_user_institution_id", "user", type_="foreignkey")
    op.drop_column("user", "institution_id")
    op.drop_table("institution")
    op.execute("DROP TYPE IF EXISTS mode")
    op.execute("DROP TYPE IF EXISTS medium")
    op.execute("DROP TYPE IF EXISTS managementtype")
    op.execute("DROP TYPE IF EXISTS collegetype")
    op.execute("DROP TYPE IF EXISTS district")

"""split courses into separate table

Revision ID: 6ef27a1b53e7
Revises: 77cae534757f
Create Date: 2026-05-11 10:00:00.000000

"""

from typing import Union
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6ef27a1b53e7"
down_revision: str | None = "77cae534757f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.execute("UPDATE institution SET university_name = UPPER(university_name)")

    op.create_table(
        "course",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("course_name", sa.String(length=200), nullable=True),
        sa.Column("option_a_bucket", sa.String(length=200), nullable=True),
        sa.Column("option_b_bucket", sa.String(length=200), nullable=True),
        sa.Column("option_c_bucket", sa.String(length=200), nullable=True),
        sa.Column("option_d_bucket", sa.String(length=200), nullable=True),
        sa.Column("cbcs", sa.Boolean(), nullable=True),
        sa.Column("revised_intake", sa.Integer(), nullable=True),
        sa.Column(
            "mode",
            postgresql.ENUM("regular", "restructured", "self-financed", name="mode", create_type=False),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institution.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        INSERT INTO course (
            id, institution_id, course_name,
            option_a_bucket, option_b_bucket, option_c_bucket, option_d_bucket,
            cbcs, revised_intake, mode
        )
        SELECT
            gen_random_uuid(), id, course_name,
            option_a_bucket, option_b_bucket, option_c_bucket, option_d_bucket,
            cbcs, revised_intake, mode
        FROM institution
        WHERE course_name IS NOT NULL
           OR option_a_bucket IS NOT NULL
           OR option_b_bucket IS NOT NULL
           OR option_c_bucket IS NOT NULL
           OR option_d_bucket IS NOT NULL
           OR cbcs IS NOT NULL
           OR revised_intake IS NOT NULL
           OR mode IS NOT NULL
        """
    )

    op.drop_column("institution", "course_name")
    op.drop_column("institution", "option_a_bucket")
    op.drop_column("institution", "option_b_bucket")
    op.drop_column("institution", "option_c_bucket")
    op.drop_column("institution", "option_d_bucket")
    op.drop_column("institution", "cbcs")
    op.drop_column("institution", "revised_intake")
    op.drop_column("institution", "mode")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE institution SET university_name = INITCAP(university_name)")

    op.add_column(
        "institution",
        sa.Column("mode", postgresql.ENUM("regular", "restructured", "self-financed", name="mode", create_type=False), nullable=True),
    )
    op.add_column(
        "institution",
        sa.Column("revised_intake", sa.Integer(), nullable=True),
    )
    op.add_column(
        "institution",
        sa.Column("cbcs", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "institution",
        sa.Column("option_d_bucket", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "institution",
        sa.Column("option_c_bucket", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "institution",
        sa.Column("option_b_bucket", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "institution",
        sa.Column("option_a_bucket", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "institution",
        sa.Column("course_name", sa.String(length=200), nullable=True),
    )

    # Restore data from course table (simplified: takes first course per institution)
    op.execute(
        """
        UPDATE institution SET
            course_name = sub.course_name,
            option_a_bucket = sub.option_a_bucket,
            option_b_bucket = sub.option_b_bucket,
            option_c_bucket = sub.option_c_bucket,
            option_d_bucket = sub.option_d_bucket,
            cbcs = sub.cbcs,
            revised_intake = sub.revised_intake,
            mode = sub.mode
        FROM (
            SELECT DISTINCT ON (institution_id) *
            FROM course
            ORDER BY institution_id, course_name
        ) sub
        WHERE institution.id = sub.institution_id
        """
    )

    op.drop_table("course")

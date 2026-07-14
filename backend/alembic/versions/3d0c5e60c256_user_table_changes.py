"""user_table_changes

Revision ID: 3d0c5e60c256
Revises: 5cf2996eef43
Create Date: 2026-04-25 15:23:26.046812

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d0c5e60c256"
down_revision: Union[str, None] = "5cf2996eef43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new profile/internship columns
    op.add_column(
        "user", sa.Column("organisation_type", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "user", sa.Column("rural_area_access", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column("permanent_postal_address", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "user", sa.Column("current_year_of_study", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "user", sa.Column("college_roll_number", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "user", sa.Column("task_registered_id", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column("has_completed_ai_courses", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "user", sa.Column("ai_courses_list", sa.String(length=1000), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column("is_intern", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("user", sa.Column("resume_record_id", sa.Uuid(), nullable=True))
    op.add_column("user", sa.Column("hardware_details", JSONB(), nullable=True))

    # Add FK for resume_record_id
    op.create_foreign_key(
        "fk_user_resume_record", "user", "record", ["resume_record_id"], ["uid"]
    )

    # Revert columns to nullable (they were made NOT NULL by centralized_validation_updates)
    op.alter_column("user", "gender", nullable=True)
    op.alter_column("user", "date_of_birth", nullable=True)
    op.alter_column("user", "current_place", nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("user", "gender", nullable=False)
    op.alter_column("user", "date_of_birth", nullable=False)
    op.alter_column("user", "current_place", nullable=False)

    op.drop_constraint("fk_user_resume_record", "user", type_="foreignkey")
    op.drop_column("user", "hardware_details")
    op.drop_column("user", "is_intern")
    op.drop_column("user", "resume_record_id")
    op.drop_column("user", "ai_courses_list")
    op.drop_column("user", "has_completed_ai_courses")
    op.drop_column("user", "task_registered_id")
    op.drop_column("user", "college_roll_number")
    op.drop_column("user", "current_year_of_study")
    op.drop_column("user", "permanent_postal_address")
    op.drop_column("user", "rural_area_access")
    op.drop_column("user", "organisation_type")

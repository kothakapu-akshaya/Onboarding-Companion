"""remove extracted text validation upper bound

Revision ID: 47182ecc8f0d
Revises: d6f6852cffb6
Create Date: 2025-10-21 18:15:00.111757

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "47182ecc8f0d"
down_revision = "d6f6852cffb6"
branch_labels = None
depends_on = None


def upgrade():
    """Remove max length constraint on old_value and new_value columns."""
    op.alter_column(
        "recordfieldhistory",
        "old_value",
        type_=sa.Text(),
        existing_type=sa.String(length=100000),
        existing_nullable=True,
    )
    op.alter_column(
        "recordfieldhistory",
        "new_value",
        type_=sa.Text(),
        existing_type=sa.String(length=100000),
        existing_nullable=True,
    )


def downgrade():
    """Re-add max length constraint on old_value and new_value columns."""
    op.alter_column(
        "recordfieldhistory",
        "old_value",
        type_=sa.String(length=100000),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "recordfieldhistory",
        "new_value",
        type_=sa.String(length=100000),
        existing_type=sa.Text(),
        existing_nullable=True,
    )

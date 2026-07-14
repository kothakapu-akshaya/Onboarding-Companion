"""add category approval fields

Revision ID: 1765958726
Revises: 59f2c3d4e5f8
Create Date: 2025-12-16 11:52:00.000000

"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "1765958726"
down_revision: Union[str, None] = "59f2c3d4e5f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add approval fields to category table."""
    # Add nullable columns first to avoid constraint violations
    op.add_column("category", sa.Column("approved", sa.Boolean(), nullable=True))
    op.add_column("category", sa.Column("suggested_by", sa.UUID(), nullable=True))
    op.add_column("category", sa.Column("approved_by", sa.UUID(), nullable=True))

    # Update all existing categories to be approved (since they were already admin-created)
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE category SET approved = TRUE WHERE approved IS NULL"))

    # Set approved column to not null with default false for new records
    op.alter_column("category", "approved", nullable=False)
    op.execute("ALTER TABLE category ALTER COLUMN approved SET DEFAULT FALSE")

    # Add foreign key constraints for the new columns
    op.create_foreign_key(
        "fk_category_suggested_by_user", "category", "user", ["suggested_by"], ["id"]
    )
    op.create_foreign_key(
        "fk_category_approved_by_user", "category", "user", ["approved_by"], ["id"]
    )


def downgrade() -> None:
    """Remove approval fields from category table."""
    # Drop foreign key constraints first
    op.drop_constraint("fk_category_approved_by_user", "category", type_="foreignkey")
    op.drop_constraint("fk_category_suggested_by_user", "category", type_="foreignkey")

    # Drop the columns
    op.drop_column("category", "approved_by")
    op.drop_column("category", "suggested_by")
    op.drop_column("category", "approved")

"""update records table to support many-to-many categories

Revision ID: 59f2c3d4e5f8
Revises: 27f88463054c
Create Date: 2025-12-15 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid import UUID


# revision identifiers, used by Alembic.
revision: str = "59f2c3d4e5f8"
down_revision: Union[str, None] = "27f88463054c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update records table to support many-to-many categories with JSONB array."""
    # Add category_ids column as JSONB array to store multiple category UUIDs
    op.add_column(
        "record", sa.Column("category_ids", postgresql.JSONB(), nullable=True)
    )

    # Temporarily populate category_ids with existing category_id values
    # This ensures existing data isn't lost during transition
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE record
            SET category_ids = JSONB_BUILD_ARRAY(category_id::TEXT)
            WHERE category_id IS NOT NULL
        """)
    )

    # Drop the old category_id column
    op.drop_constraint("record_category_id_fkey", "record", type_="foreignkey")
    op.drop_column("record", "category_id")


def downgrade() -> None:
    """Revert records table changes for many-to-many categories."""
    # Add back the old category_id column
    op.add_column("record", sa.Column("category_id", sa.UUID(), nullable=True))

    # Temporarily populate category_id with first element from category_ids array
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE record
            SET category_id = (category_ids->>0)::UUID
            WHERE category_ids IS NOT NULL AND JSONB_ARRAY_LENGTH(category_ids) > 0
        """)
    )

    # Recreate the foreign key constraint
    op.create_foreign_key(
        "record_category_id_fkey", "record", "category", ["category_id"], ["id"]
    )

    # Drop the category_ids column
    op.drop_column("record", "category_ids")

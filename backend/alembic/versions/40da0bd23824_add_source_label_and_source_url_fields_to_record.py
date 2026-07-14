"""add_source_label_and_source_url_fields_to_record

Revision ID: 40da0bd23824
Revises: 47182ecc8f0d
Create Date: 2025-11-20 16:24:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "40da0bd23824"
down_revision: Union[str, None] = "47182ecc8f0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add source_label and source_url fields to record table"""

    # Add source_label column
    op.add_column(
        "record", sa.Column("source_label", sa.String(length=200), nullable=True)
    )

    # Add source_url column
    op.add_column(
        "record", sa.Column("source_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    """Remove source_label and source_url fields from record table"""

    # Remove source_url column
    op.drop_column("record", "source_url")

    # Remove source_label column
    op.drop_column("record", "source_label")

"""add extracted text field to records table

Revision ID: d6f6852cffb6
Revises: a1b2c3d4e5f6
Create Date: 2025-09-25 18:32:22.699637

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d6f6852cffb6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add extracted text field to records table."""
    # Add single extracted_text field for all extracted text versions
    # Version 1 = AI extracted (change_source='ai_processing')
    # Version 2+ = User corrections (change_source='user_edit')
    op.add_column(
        "record", sa.Column("extracted_text", postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    """Remove extracted text field from records table."""
    # Remove extracted text field
    op.drop_column("record", "extracted_text")

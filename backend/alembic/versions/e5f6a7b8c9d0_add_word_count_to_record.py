"""add word_count to record

Revision ID: e5f6a7b8c9d0
Revises: c4f1a2b3d4e5
Create Date: 2026-06-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "c4f1a2b3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "record",
        sa.Column("word_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("record", "word_count")

"""move text metrics from record to extractedtext table

Moves word_count, sentence_count, and character_count from the record
table to the extractedtext table so they only exist for records that
have extracted text.

Revision ID: b0c1d2e3f4a5
Revises: a9b8c7d6e5f4
Create Date: 2026-06-25 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b0c1d2e3f4a5"
down_revision: str | None = "a9b8c7d6e5f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add columns to extractedtext table
    op.add_column(
        "extractedtext",
        sa.Column("word_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "extractedtext",
        sa.Column("sentence_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "extractedtext",
        sa.Column("character_count", sa.Integer(), nullable=True),
    )

    # Drop columns from record table
    op.drop_column("record", "word_count")


def downgrade() -> None:
    # Add columns back to record table
    op.add_column(
        "record",
        sa.Column("word_count", sa.Integer(), nullable=True),
    )

    # Drop columns from extractedtext table
    op.drop_column("extractedtext", "character_count")
    op.drop_column("extractedtext", "sentence_count")
    op.drop_column("extractedtext", "word_count")

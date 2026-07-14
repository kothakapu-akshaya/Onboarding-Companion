"""add dataset column to extractedtext table

Revision ID: e3f4a5b6c7d8
Revises: d5e6f7a8b9c0
Create Date: 2026-05-29

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "extractedtext",
        sa.Column("dataset", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("extractedtext", "dataset")

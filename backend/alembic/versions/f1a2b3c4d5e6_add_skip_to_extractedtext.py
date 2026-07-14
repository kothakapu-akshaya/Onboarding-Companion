"""add skipped and skip_reason columns to extractedtext

Revision ID: f1a2b3c4d5e6
Revises: e3f4a5b6c7d8
Create Date: 2026-06-04

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "818f3d16e026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "extractedtext",
        sa.Column("skipped", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column(
        "extractedtext",
        sa.Column("skip_reason", sa.String(50), nullable=True),
    )
    op.add_column(
        "extractedtext",
        sa.Column("edit", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("extractedtext", "edit")
    op.drop_column("extractedtext", "skip_reason")
    op.drop_column("extractedtext", "skipped")

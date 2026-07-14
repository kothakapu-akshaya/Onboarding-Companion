"""add_is_fully_validated_to_extracted_text

Revision ID: 545adb32c37a
Revises: 643713e8ddab
Create Date: 2026-07-07 22:12:23.094342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '545adb32c37a'
down_revision: Union[str, None] = '643713e8ddab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "extractedtext",
        sa.Column(
            "is_fully_validated",
            sa.Boolean(),
            nullable=True,
            server_default="false",
        ),
    )

    op.create_index(
        "ix_extractedtext_is_fully_validated",
        "extractedtext",
        ["is_fully_validated"],
    )


def downgrade() -> None:
    op.drop_index("ix_extractedtext_is_fully_validated", table_name="extractedtext")
    op.drop_column("extractedtext", "is_fully_validated")

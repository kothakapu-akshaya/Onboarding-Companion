"""add tag fields to record

Revision ID: d6e7f8a9b0c1
Revises: e1f2a3b4c5d6
Create Date: 2026-05-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d6e7f8a9b0c1"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {
        column["name"] for column in inspector.get_columns("record")
    }

    if "tagged_usernames" not in existing_columns:
        op.add_column(
            "record",
            sa.Column("tagged_usernames", postgresql.JSONB(), nullable=True),
        )

    if "hashtags" not in existing_columns:
        op.add_column(
            "record",
            sa.Column("hashtags", postgresql.JSONB(), nullable=True),
        )

    if "record_tags" not in existing_columns:
        op.add_column(
            "record",
            sa.Column("record_tags", postgresql.JSONB(), nullable=True),
        )

    op.create_index(
        "ix_record_hashtags", "record", ["hashtags"], postgresql_using="gin"
    )
    op.create_index(
        "ix_record_tagged_usernames",
        "record",
        ["tagged_usernames"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_record_record_tags", "record", ["record_tags"], postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_index("ix_record_hashtags", table_name="record")
    op.drop_index("ix_record_tagged_usernames", table_name="record")
    op.drop_index("ix_record_record_tags", table_name="record")
    op.drop_column("record", "record_tags")
    op.drop_column("record", "hashtags")
    op.drop_column("record", "tagged_usernames")

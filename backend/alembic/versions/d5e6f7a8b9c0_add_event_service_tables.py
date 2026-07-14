"""add event service tables

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-05-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d5e6f7a8b9c0"
down_revision: str | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "event" not in existing_tables:
        op.create_table(
            "event",
            sa.Column("uid", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.String(length=1000), nullable=True),
            sa.Column("page_context", sa.String(length=100), nullable=False),
            sa.Column("filters", postgresql.JSONB(), nullable=True),
            sa.Column("limit", sa.Integer(), nullable=False, server_default="20"),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default="true"
            ),
            sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
            sa.PrimaryKeyConstraint("uid"),
        )

    existing_indexes = {
        index["name"] for index in inspector.get_indexes("event")
    }
    existing_columns = {column["name"] for column in inspector.get_columns("event")}
    if "limit" not in existing_columns:
        op.add_column(
            "event",
            sa.Column("limit", sa.Integer(), nullable=False, server_default="20"),
        )
    if "ix_event_name" not in existing_indexes:
        op.create_index("ix_event_name", "event", ["name"])
    if "ix_event_page_context" not in existing_indexes:
        op.create_index("ix_event_page_context", "event", ["page_context"])
    if "ix_event_is_active" not in existing_indexes:
        op.create_index("ix_event_is_active", "event", ["is_active"])


def downgrade() -> None:
    op.drop_column("event", "limit")
    op.drop_index("ix_event_is_active", table_name="event")
    op.drop_index("ix_event_page_context", table_name="event")
    op.drop_index("ix_event_name", table_name="event")
    op.drop_table("event")

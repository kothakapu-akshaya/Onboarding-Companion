"""create points events

Revision ID: 2506798be9fa
Revises: 1765958726
Create Date: 2025-08-28 00:00:00
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2506798be9fa"
down_revision: Union[str, None] = "1765958726"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pointsevent",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_uid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "reason",
            sa.String(length=50),
            nullable=False,
            server_default="record_created",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["record_uid"], ["record.uid"]),
        sa.UniqueConstraint("record_uid", name="uq_points_record_once"),
    )
    op.create_index("ix_pointsevent_user_id", "pointsevent", ["user_id"])
    op.create_index("ix_pointsevent_created_at", "pointsevent", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_pointsevent_created_at", table_name="pointsevent")
    op.drop_index("ix_pointsevent_user_id", table_name="pointsevent")
    op.drop_table("pointsevent")

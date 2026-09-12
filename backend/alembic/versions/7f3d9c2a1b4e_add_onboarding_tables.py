"""add onboarding tables

Revision ID: 7f3d9c2a1b4e
Revises: 545adb32c37a
Create Date: 2026-09-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f3d9c2a1b4e"
down_revision: Union[str, None] = "545adb32c37a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "onboarding_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("task_key", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "task_key",
            name="uq_onboarding_progress_user_id_task_key",
        ),
    )
    op.create_index(
        op.f("ix_onboarding_progress_user_id"),
        "onboarding_progress",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "onboarding_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("task_key", sa.String(length=16), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "object_key", name="uq_onboarding_evidence_object_key"
        ),
    )
    op.create_index(
        op.f("ix_onboarding_evidence_user_id"),
        "onboarding_evidence",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_onboarding_evidence_task_key"),
        "onboarding_evidence",
        ["task_key"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_onboarding_evidence_task_key"),
        table_name="onboarding_evidence",
    )
    op.drop_index(
        op.f("ix_onboarding_evidence_user_id"),
        table_name="onboarding_evidence",
    )
    op.drop_table("onboarding_evidence")

    op.drop_index(
        op.f("ix_onboarding_progress_user_id"),
        table_name="onboarding_progress",
    )
    op.drop_table("onboarding_progress")
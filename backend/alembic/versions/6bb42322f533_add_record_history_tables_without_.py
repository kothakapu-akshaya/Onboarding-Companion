"""add record edit history management tables

Revision ID: 6bb42322f533
Revises: 9f903085c7e9
Create Date: 2025-09-24 12:23:49.157043

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = "6bb42322f533"
down_revision: Union[str, None] = "9f903085c7e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create record history table
    op.create_table(
        "recordhistory",
        sa.Column("uid", postgresql.UUID(), default=uuid.uuid4, nullable=False),
        sa.Column("record_id", postgresql.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=20), nullable=False),
        sa.Column("change_source", sa.String(length=20), nullable=False),
        sa.Column("changed_by", postgresql.UUID(), nullable=False),
        sa.Column("record_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("field_changes", postgresql.JSONB(), nullable=False),
        sa.Column("change_reason", sa.String(length=500), nullable=True),
        sa.Column("change_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["record.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["changed_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_recordhistory_record_id", "recordhistory", ["record_id"])
    op.create_index("ix_recordhistory_changed_by", "recordhistory", ["changed_by"])
    op.create_index("ix_recordhistory_change_type", "recordhistory", ["change_type"])
    op.create_index(
        "ix_recordhistory_change_source", "recordhistory", ["change_source"]
    )
    op.create_index("ix_recordhistory_created_at", "recordhistory", ["created_at"])
    op.create_index(
        "ix_recordhistory_version_number", "recordhistory", ["version_number"]
    )

    # Create record field history table
    op.create_table(
        "recordfieldhistory",
        sa.Column("uid", postgresql.UUID(), default=uuid.uuid4, nullable=False),
        sa.Column("record_history_id", postgresql.UUID(), nullable=False),
        sa.Column("record_id", postgresql.UUID(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("old_value", sa.String(length=100000), nullable=True),
        sa.Column("new_value", sa.String(length=100000), nullable=True),
        sa.Column("change_reason", sa.String(length=300), nullable=True),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=True),
        sa.Column("validation_warnings", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_history_id"],
            ["recordhistory.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["record.uid"],
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "ix_recordfieldhistory_record_id", "recordfieldhistory", ["record_id"]
    )
    op.create_index(
        "ix_recordfieldhistory_field_name", "recordfieldhistory", ["field_name"]
    )
    op.create_index(
        "ix_recordfieldhistory_created_at", "recordfieldhistory", ["created_at"]
    )

    # Create record version table
    op.create_table(
        "recordversion",
        sa.Column("uid", postgresql.UUID(), default=uuid.uuid4, nullable=False),
        sa.Column("record_id", postgresql.UUID(), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, default=1),
        sa.Column("total_changes", sa.Integer(), nullable=False, default=0),
        sa.Column("last_changed_by", postgresql.UUID(), nullable=True),
        sa.Column("last_change_type", sa.String(length=20), nullable=True),
        sa.Column("last_change_source", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_edit_changes", sa.Integer(), nullable=False, default=0),
        sa.Column("admin_changes", sa.Integer(), nullable=False, default=0),
        sa.Column("system_changes", sa.Integer(), nullable=False, default=0),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["record.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["last_changed_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("record_id", name="unique_version_per_record"),
    )
    op.create_index("ix_recordversion_record_id", "recordversion", ["record_id"])
    op.create_index(
        "ix_recordversion_current_version", "recordversion", ["current_version"]
    )
    op.create_index("ix_recordversion_last_updated", "recordversion", ["last_updated"])

    # Create record snapshot table
    op.create_table(
        "recordsnapshot",
        sa.Column("uid", postgresql.UUID(), default=uuid.uuid4, nullable=False),
        sa.Column("record_id", postgresql.UUID(), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("full_record_data", postgresql.JSONB(), nullable=False),
        sa.Column("snapshot_type", sa.String(length=50), nullable=False),
        sa.Column("created_by", postgresql.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["record.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_recordsnapshot_record_id", "recordsnapshot", ["record_id"])
    op.create_index(
        "ix_recordsnapshot_snapshot_version", "recordsnapshot", ["snapshot_version"]
    )
    op.create_index("ix_recordsnapshot_created_at", "recordsnapshot", ["created_at"])

    # Create record restore table
    op.create_table(
        "recordrestore",
        sa.Column("uid", postgresql.UUID(), default=uuid.uuid4, nullable=False),
        sa.Column("record_id", postgresql.UUID(), nullable=False),
        sa.Column("restored_from_version", sa.Integer(), nullable=False),
        sa.Column("restored_to_version", sa.Integer(), nullable=False),
        sa.Column("restored_by", postgresql.UUID(), nullable=False),
        sa.Column("restore_reason", sa.String(length=500), nullable=False),
        sa.Column("restored_fields", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("partial_restore", sa.Boolean(), nullable=False, default=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, default=False),
        sa.Column("approved_by", postgresql.UUID(), nullable=True),
        sa.Column(
            "approval_status", sa.String(length=20), nullable=False, default="pending"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["record.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["restored_by"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index("ix_recordrestore_record_id", "recordrestore", ["record_id"])
    op.create_index(
        "ix_recordrestore_approval_status", "recordrestore", ["approval_status"]
    )
    op.create_index("ix_recordrestore_created_at", "recordrestore", ["created_at"])

    # Add constraints for version numbers
    op.create_check_constraint(
        "check_version_positive", "recordhistory", "version_number >= 1"
    )
    op.create_check_constraint(
        "check_current_version_positive", "recordversion", "current_version >= 1"
    )
    op.create_check_constraint(
        "check_total_changes_non_negative", "recordversion", "total_changes >= 0"
    )
    op.create_check_constraint(
        "check_restore_versions_positive",
        "recordrestore",
        "restored_from_version >= 1 AND restored_to_version >= 1",
    )

    # Create composite indexes for common queries
    op.create_index(
        "ix_recordhistory_record_version",
        "recordhistory",
        ["record_id", "version_number"],
        unique=True,
    )
    op.create_index(
        "ix_recordfieldhistory_record_field",
        "recordfieldhistory",
        ["record_id", "field_name", "created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order to handle dependencies
    op.drop_table("recordrestore")
    op.drop_table("recordsnapshot")
    op.drop_table("recordversion")
    op.drop_table("recordfieldhistory")
    op.drop_table("recordhistory")

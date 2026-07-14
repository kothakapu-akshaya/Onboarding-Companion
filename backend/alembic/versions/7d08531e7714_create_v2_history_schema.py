"""create v2 history tables, partitioned archives, indexes, views, and migrate V1 data

Revision ID: 7d08531e7714
Revises: b0c1d2e3f4a5
Create Date: 2026-06-21 12:00:00.000000

Creates the V2 history schema and migrates existing V1 data:
- record_history_v2, record_version_v2, record_major_snapshot, record_restore_v2
- history_table_stats monitoring view
- Data migration: copies all V1 records into V2 tables with format conversion
"""

import json
import logging
from typing import Any, Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

logger = logging.getLogger(__name__)
BATCH_SIZE = 500


revision: str = "7d08531e7714"
down_revision: Union[str, None] = "b0c1d2e3f4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # record_history_v2 - unified history table
    # ============================================================
    op.create_table(
        "record_history_v2",
        sa.Column("uid", postgresql.UUID(), default=uuid.uuid4, nullable=False),
        sa.Column("record_id", postgresql.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=20), nullable=False),
        sa.Column("change_source", sa.String(length=20), nullable=False),
        sa.Column("changed_by", postgresql.UUID(), nullable=False),
        sa.Column(
            "field_changes",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("full_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("change_reason", sa.String(length=500), nullable=True),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=True),
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
    op.create_index(
        "ix_record_history_v2_record_id", "record_history_v2", ["record_id"]
    )
    op.create_index(
        "ix_record_history_v2_version_number",
        "record_history_v2",
        ["version_number"],
    )
    op.create_index(
        "ix_record_history_v2_change_type", "record_history_v2", ["change_type"]
    )
    op.create_index(
        "ix_record_history_v2_change_source",
        "record_history_v2",
        ["change_source"],
    )
    op.create_index(
        "ix_record_history_v2_changed_by", "record_history_v2", ["changed_by"]
    )
    op.create_index(
        "ix_record_history_v2_created_at", "record_history_v2", ["created_at"]
    )
    op.create_index(
        "ix_record_history_v2_record_version",
        "record_history_v2",
        ["record_id", "version_number"],
        unique=True,
    )
    op.create_index(
        "ix_record_history_v2_record_created",
        "record_history_v2",
        ["record_id", "created_at"],
    )
    op.create_index(
        "ix_record_history_v2_user_created",
        "record_history_v2",
        ["changed_by", "created_at"],
    )
    op.create_index(
        "ix_record_history_v2_change_source_created",
        "record_history_v2",
        ["change_source", "created_at"],
    )
    op.create_index(
        "ix_record_history_v2_field_changes",
        "record_history_v2",
        ["field_changes"],
        postgresql_using="gin",
    )

    # ============================================================
    # record_version_v2 - version counters per record
    # ============================================================
    op.create_table(
        "record_version_v2",
        sa.Column("uid", postgresql.UUID(), nullable=False),
        sa.Column("record_id", postgresql.UUID(), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, default=0),
        sa.Column("total_changes", sa.Integer(), nullable=False, default=0),
        sa.Column("last_changed_by", postgresql.UUID(), nullable=True),
        sa.Column("last_change_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_edits", sa.Integer(), nullable=False, default=0),
        sa.Column("admin_edits", sa.Integer(), nullable=False, default=0),
        sa.Column("system_updates", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "last_major_version", sa.Integer(), nullable=False, default=1
        ),
        sa.Column(
            "last_snapshot_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["record.uid"],
        ),
        sa.ForeignKeyConstraint(
            ["last_changed_by"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("record_id"),
    )
    op.create_index(
        "ix_record_version_v2_record_id", "record_version_v2", ["record_id"]
    )

    # ============================================================
    # record_major_snapshot - periodic snapshots
    # ============================================================
    op.create_table(
        "record_major_snapshot",
        sa.Column("uid", postgresql.UUID(), default=uuid.uuid4, nullable=False),
        sa.Column("record_id", postgresql.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("full_data", postgresql.JSONB(), nullable=False),
        sa.Column("snapshot_type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["record.uid"],
        ),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(
        "ix_record_major_snapshot_record_id",
        "record_major_snapshot",
        ["record_id"],
    )
    op.create_index(
        "ix_record_major_snapshot_record_version",
        "record_major_snapshot",
        ["record_id", "version_number"],
        unique=True,
    )

    # ============================================================
    # record_restore_v2 - restore tracking
    # ============================================================
    op.create_table(
        "record_restore_v2",
        sa.Column("uid", postgresql.UUID(), default=uuid.uuid4, nullable=False),
        sa.Column("record_id", postgresql.UUID(), nullable=False),
        sa.Column("restored_from_version", sa.Integer(), nullable=False),
        sa.Column("restored_to_version", sa.Integer(), nullable=False),
        sa.Column("restored_by", postgresql.UUID(), nullable=False),
        sa.Column("restore_reason", sa.String(length=500), nullable=False),
        sa.Column(
            "restored_fields",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "partial_restore", sa.Boolean(), nullable=False, default=False
        ),
        sa.Column(
            "requires_approval", sa.Boolean(), nullable=False, default=False
        ),
        sa.Column("approved_by", postgresql.UUID(), nullable=True),
        sa.Column(
            "approval_status",
            sa.String(length=20),
            nullable=False,
            default="pending",
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
    op.create_index(
        "ix_record_restore_v2_record_id", "record_restore_v2", ["record_id"]
    )
    op.create_index(
        "ix_record_restore_v2_approval_status",
        "record_restore_v2",
        ["approval_status"],
    )

    # ============================================================
    # Monitoring View
    # ============================================================
    op.execute("""
        CREATE OR REPLACE VIEW history_table_stats AS
        SELECT schemaname, tablename,
            pg_size_pretty(pg_total_relation_size(
                schemaname || '.' || tablename
            )) AS size,
            pg_total_relation_size(
                schemaname || '.' || tablename
            ) AS size_bytes
        FROM pg_tables
        WHERE tablename LIKE 'record_history%'
           OR tablename LIKE 'record_version%'
           OR tablename LIKE 'record_major_snapshot%'
           OR tablename LIKE 'record_restore%'
    """)

    # ============================================================
    # Data Migration: V1 → V2
    # ============================================================
    _migrate_data()


def _migrate_data() -> None:
    """Migrate existing V1 data into the new V2 tables."""
    conn = op.get_bind()

    v1_tables_exist = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'recordhistory')"
        )
    ).scalar()
    if not v1_tables_exist:
        logger.info("No V1 tables found, skipping data migration")
        return

    _migrate_versions(conn)
    _migrate_restores(conn)
    _migrate_snapshots(conn)
    _migrate_history(conn)

    # V1 tables are preserved to allow safe downgrade.
    # They can be manually dropped after confirming the migration
    # is stable and no rollback is needed.


def _migrate_versions(conn: sa.Connection) -> None:
    """Migrate recordversion → record_version_v2."""
    count = conn.execute(sa.text("SELECT COUNT(*) FROM recordversion")).scalar()
    if count == 0:
        return

    existing = (
        conn.execute(sa.text("SELECT COUNT(*) FROM record_version_v2")).scalar()
        or 0
    )
    if existing > 0:
        logger.info(
            "record_version_v2 already has data, skipping version migration"
        )
        return

    conn.execute(
        sa.text("""
        INSERT INTO record_version_v2 (
            uid, record_id, current_version, total_changes,
            last_changed_by, created_at, last_change_at,
            user_edits, admin_edits, system_updates,
            last_major_version
        )
        SELECT
            gen_random_uuid(),
            record_id, current_version, total_changes,
            last_changed_by, created_at, last_updated,
            COALESCE(user_edit_changes, 0),
            COALESCE(admin_changes, 0),
            COALESCE(system_changes, 0),
            (COALESCE(current_version, 0) / 10) * 10
        FROM recordversion
        ON CONFLICT DO NOTHING
    """)
    )
    logger.info(f"Migrated {count} version records")


def _migrate_restores(conn: sa.Connection) -> None:
    """Migrate recordrestore → record_restore_v2."""
    count = conn.execute(sa.text("SELECT COUNT(*) FROM recordrestore")).scalar()
    if count == 0:
        return

    existing = (
        conn.execute(sa.text("SELECT COUNT(*) FROM record_restore_v2")).scalar()
        or 0
    )
    if existing > 0:
        logger.info(
            "record_restore_v2 already has data, skipping restore migration"
        )
        return

    conn.execute(
        sa.text("""
        INSERT INTO record_restore_v2 (
            uid, record_id, restored_from_version, restored_to_version,
            restored_by, restore_reason, restored_fields,
            partial_restore, requires_approval, approved_by,
            approval_status, created_at, approved_at
        )
        SELECT
            uid, record_id, restored_from_version, restored_to_version,
            restored_by, restore_reason, restored_fields,
            partial_restore, requires_approval, approved_by,
            approval_status, created_at, approved_at
        FROM recordrestore
        ON CONFLICT DO NOTHING
    """)
    )
    logger.info(f"Migrated {count} restore records")


def _migrate_snapshots(conn: sa.Connection) -> None:
    """Migrate recordsnapshot → record_major_snapshot."""
    count = conn.execute(
        sa.text("SELECT COUNT(*) FROM recordsnapshot")
    ).scalar()
    if count == 0:
        return

    existing = (
        conn.execute(
            sa.text("SELECT COUNT(*) FROM record_major_snapshot")
        ).scalar()
        or 0
    )
    if existing > 0:
        logger.info(
            "record_major_snapshot already has data, skipping snapshot migration"
        )
        return

    conn.execute(
        sa.text("""
        INSERT INTO record_major_snapshot (
            uid, record_id, version_number, full_data,
            snapshot_type, created_at
        )
        SELECT
            uid, record_id, snapshot_version, full_record_data,
            snapshot_type, created_at
        FROM recordsnapshot
        ON CONFLICT DO NOTHING
    """)
    )
    logger.info(f"Migrated {count} snapshot records")


def _migrate_history(conn: sa.Connection) -> None:
    """Migrate recordhistory + recordfieldhistory → record_history_v2.

    This is the most complex migration: it merges the field-level changes
    from recordfieldhistory into the field_changes JSONB column, and
    transforms the V1 {old_value, new_value, change_type} format into
    the V2 {old, new, reason} format.
    """
    existing = (
        conn.execute(sa.text("SELECT COUNT(*) FROM record_history_v2")).scalar()
        or 0
    )
    if existing > 0:
        logger.info(
            "record_history_v2 already has data, skipping history migration"
        )
        return

    total = conn.execute(sa.text("SELECT COUNT(*) FROM recordhistory")).scalar()
    if total == 0:
        return

    offset = 0
    migrated = 0
    while True:
        rows = conn.execute(
            sa.text("""
                SELECT uid, record_id, version_number, change_type,
                       change_source, changed_by, record_snapshot,
                       field_changes, change_reason, change_metadata,
                       created_at
                FROM recordhistory
                ORDER BY record_id, version_number
                LIMIT :limit OFFSET :offset
            """),
            {"limit": BATCH_SIZE, "offset": offset},
        ).fetchall()

        if not rows:
            break

        batch_uids = [r.uid for r in rows]

        field_hist_rows = conn.execute(
            sa.text("""
                SELECT record_history_id, field_name,
                       old_value, new_value, change_reason
                FROM recordfieldhistory
                WHERE record_history_id = ANY(:uids)
            """),
            {"uids": batch_uids},
        ).fetchall()

        field_by_history: dict[Any, list[Any]] = {}
        for fh in field_hist_rows:
            field_by_history.setdefault(fh.record_history_id, []).append(fh)

        batch_params: list[dict[str, Any]] = []
        for row in rows:
            old_field_changes = row.field_changes or {}

            new_field_changes: dict[str, dict[str, Any]] = {}
            if isinstance(old_field_changes, dict):
                for field, change_data in old_field_changes.items():
                    if isinstance(change_data, dict):
                        new_field_changes[field] = {
                            "old": change_data.get("old_value"),
                            "new": change_data.get("new_value"),
                            "type": change_data.get("change_type"),
                            "reason": change_data.get("change_reason"),
                        }
                    else:
                        new_field_changes[field] = {
                            "old": str(change_data) if change_data else None,
                            "new": None,
                            "type": None,
                            "reason": None,
                        }

            for fh in field_by_history.get(row.uid, []):
                if fh.field_name not in new_field_changes:
                    new_field_changes[fh.field_name] = {
                        "old": fh.old_value,
                        "new": fh.new_value,
                        "type": None,
                        "reason": fh.change_reason,
                    }
                else:
                    new_field_changes[fh.field_name]["reason"] = (
                        fh.change_reason
                    )

            batch_params.append(
                {
                    "uid": row.uid,
                    "record_id": row.record_id,
                    "version_number": row.version_number,
                    "change_type": row.change_type,
                    "change_source": row.change_source,
                    "changed_by": row.changed_by,
                    "field_changes": json.dumps(new_field_changes),
                    "full_snapshot": json.dumps(row.record_snapshot)
                    if row.record_snapshot
                    else None,
                    "change_reason": row.change_reason,
                    "change_metadata": json.dumps(row.change_metadata)
                    if row.change_metadata
                    else None,
                    "created_at": row.created_at,
                }
            )

        if batch_params:
            conn.execute(
                sa.text("""
                    INSERT INTO record_history_v2 (
                        uid, record_id, version_number, change_type,
                        change_source, changed_by, field_changes,
                        full_snapshot, change_reason, change_metadata,
                        created_at
                    ) VALUES (
                        :uid, :record_id, :version_number, :change_type,
                        :change_source, :changed_by,
                        CAST(:field_changes AS jsonb),
                        CAST(:full_snapshot AS jsonb), :change_reason,
                        CAST(:change_metadata AS jsonb), :created_at
                    )
                    ON CONFLICT DO NOTHING
                """),
                batch_params,
            )
            migrated += len(batch_params)

        offset += BATCH_SIZE
        logger.info(f"  Migrated {migrated}/{total} history entries")

    logger.info(f"Migrated {migrated} history entries")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS history_table_stats")
    op.drop_table("record_restore_v2")
    op.drop_table("record_major_snapshot")
    op.drop_table("record_version_v2")
    op.drop_table("record_history_v2")

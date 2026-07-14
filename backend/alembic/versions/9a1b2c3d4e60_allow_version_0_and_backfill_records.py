"""Allow version 0 in recordhistory and recordversion tables and backfill records without history

Revision ID: 9a1b2c3d4e60
Revises: 846gk81c4s44
Create Date: 2026-04-07 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a1b2c3d4e60"
down_revision: Union[str, None] = "846gk81c4s44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow version 0 in recordhistory and recordversion tables and backfill records without history."""
    op.drop_constraint(
        constraint_name="check_version_positive", table_name="recordhistory"
    )

    op.drop_constraint(
        constraint_name="check_current_version_positive", table_name="recordversion"
    )

    op.drop_constraint(
        constraint_name="check_restore_versions_positive", table_name="recordrestore"
    )

    op.create_check_constraint(
        constraint_name="check_version_non_negative",
        table_name="recordhistory",
        condition="version_number >= 0",
    )

    op.create_check_constraint(
        constraint_name="check_current_version_non_negative",
        table_name="recordversion",
        condition="current_version >= 0",
    )

    op.create_check_constraint(
        constraint_name="check_restore_versions_non_negative",
        table_name="recordrestore",
        condition="restored_from_version >= 0 AND restored_to_version >= 0",
    )

    conn = op.get_bind()

    conn.execute(
        sa.text("""
        INSERT INTO recordhistory (
            uid,
            record_id,
            version_number,
            change_type,
            change_source,
            changed_by,
            record_snapshot,
            field_changes,
            change_reason,
            change_metadata,
            created_at
        )
        SELECT
            gen_random_uuid(),
            r.uid as record_id,
            0 as version_number,
            'created' as change_type,
            'system_process' as change_source,
            r.user_id as changed_by,
            json_build_object(
                'uid', r.uid,
                'title', r.title,
                'description', r.description,
                'media_type', r.media_type,
                'file_url', r.file_url,
                'file_name', r.file_name,
                'file_size', r.file_size,
                'file_hash', r.file_hash,
                'snr_frequency', r.snr_frequency,
                'status', r.status,
                'release_rights', r.release_rights,
                'creator', r.creator,
                'published_date', r.published_date,
                'language', r.language,
                'location', CASE WHEN r.location IS NOT NULL THEN ST_AsText(r.location) ELSE NULL END,
                'user_id', r.user_id,
                'reviewed', r.reviewed,
                'reviewed_by', r.reviewed_by,
                'category_ids', r.category_ids,
                'created_at', r.created_at,
                'updated_at', r.updated_at,
                'reviewed_at', r.reviewed_at,
                'duration_seconds', r.duration_seconds,
                'source_label', r.source_label,
                'source_url', r.source_url,
                'extracted_text', r.extracted_text
            ) as record_snapshot,
            '{}'::jsonb as field_changes,
            'Backfilled initial record creation (version 0)' as change_reason,
            json_build_object(
                'creation_type', 'backfilled_current_state',
                'backfilled_as_initial_state', true
            ) as change_metadata,
            COALESCE(r.created_at, CURRENT_TIMESTAMP) as created_at
        FROM record r
        WHERE NOT EXISTS (
            SELECT 1
            FROM recordhistory rh
            WHERE rh.record_id = r.uid
        );
    """)
    )

    conn.execute(
        sa.text("""
        INSERT INTO recordversion (
            uid,
            record_id,
            current_version,
            total_changes,
            last_changed_by,
            last_change_type,
            last_change_source,
            user_edit_changes,
            admin_changes,
            system_changes,
            created_at,
            last_updated
        )
        SELECT
            gen_random_uuid(),
            rh.record_id,
            0 as current_version,
            1 as total_changes,
            rh.changed_by as last_changed_by,
            rh.change_type as last_change_type,
            rh.change_source as last_change_source,
            0 as user_edit_changes,
            0 as admin_changes,
            1 as system_changes,
            rh.created_at as created_at,
            rh.created_at as last_updated
        FROM recordhistory rh
        WHERE rh.version_number = 0
        AND NOT EXISTS (
            SELECT 1
            FROM recordversion rv
            WHERE rv.record_id = rh.record_id
        );
    """)
    )


def downgrade() -> None:
    """Revert to original constraints requiring positive versions only."""
    op.drop_constraint(
        constraint_name="check_version_non_negative", table_name="recordhistory"
    )

    op.drop_constraint(
        constraint_name="check_current_version_non_negative", table_name="recordversion"
    )

    op.drop_constraint(
        constraint_name="check_restore_versions_non_negative",
        table_name="recordrestore",
    )

    op.create_check_constraint(
        constraint_name="check_version_positive",
        table_name="recordhistory",
        condition="version_number >= 1",
    )

    op.create_check_constraint(
        constraint_name="check_current_version_positive",
        table_name="recordversion",
        condition="current_version >= 1",
    )

    op.create_check_constraint(
        constraint_name="check_restore_versions_positive",
        table_name="recordrestore",
        condition="restored_from_version >= 1 AND restored_to_version >= 1",
    )

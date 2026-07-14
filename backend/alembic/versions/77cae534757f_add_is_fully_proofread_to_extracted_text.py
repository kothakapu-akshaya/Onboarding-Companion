"""Add is_fully_proofread to extractedtext table

Revision ID: 77cae534757f
Revises: 8a8182e5648f
Create Date: 2026-04-19

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "77cae534757f"
down_revision = "8a8182e5648f"
branch_labels = None
depends_on = None


def upgrade():
    # Add is_fully_proofread column
    op.add_column(
        "extractedtext",
        sa.Column(
            "is_fully_proofread",
            sa.Boolean(),
            nullable=True,
            server_default="false",
        ),
    )

    # Add index for fast filtering
    op.create_index(
        "ix_extractedtext_is_fully_proofread",
        "extractedtext",
        ["is_fully_proofread"],
    )

    # Backfill: set is_fully_proofread=true where all segments are proofread
    op.execute(
        """
        UPDATE extractedtext
        SET is_fully_proofread = true
        WHERE CASE
          WHEN segments IS NOT NULL AND jsonb_typeof(segments) = 'array'
            THEN jsonb_array_length(segments) > 0
              AND (
                SELECT count(*) = 0
                FROM jsonb_array_elements(segments) AS seg
                WHERE coalesce((seg ->> 'proofread')::boolean, false) = false
              )
          ELSE false
        END
        """
    )


def downgrade():
    op.drop_index("ix_extractedtext_is_fully_proofread", table_name="extractedtext")
    op.drop_column("extractedtext", "is_fully_proofread")

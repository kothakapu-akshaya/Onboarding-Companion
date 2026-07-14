"""Add release_rights to record table

Revision ID: ed5b5ea7def8
Revises: 118966d219d7
Create Date: 2025-08-10 15:58:53.398862

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "ed5b5ea7def8"
down_revision: Union[str, None] = "118966d219d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Add the column as nullable so it can be populated for existing rows
    op.add_column("record", sa.Column("release_rights", sa.Text(), nullable=True))

    # 2. Set NA for existing rows
    op.execute("UPDATE record SET release_rights = 'NA' WHERE release_rights IS NULL")

    # 3. Add CHECK constraint to only allow specific values
    op.create_check_constraint(
        "ck_release_rights_allowed_values",
        "record",
        "release_rights IN ('creator', 'family_or_friend', 'downloaded', 'NA')",
    )

    # 4. Make column non-nullable with default
    op.alter_column(
        "record",
        "release_rights",
        existing_type=sa.Text(),
        nullable=False,
        server_default="NA",
    )


def downgrade():
    op.drop_constraint("ck_release_rights_allowed_values", "record", type_="check")
    op.drop_column("record", "release_rights")

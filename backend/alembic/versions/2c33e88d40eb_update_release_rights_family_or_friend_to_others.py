"""add_creator_field_and_update_release_rights_to_others

Revision ID: 2c33e88d40eb
Revises: 6c29a2005614
Create Date: 2025-09-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "2c33e88d40eb"
down_revision: Union[str, None] = "6c29a2005614"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add creator field to record table and update release_rights enum from family_or_friend to others"""

    # 1. Add the creator column as nullable
    op.add_column("record", sa.Column("creator", sa.String(length=200), nullable=True))

    # Drop existing check constraint
    op.drop_constraint("ck_release_rights_allowed_values", "record", type_="check")

    # Create new check constraint to allow others
    op.create_check_constraint(
        "ck_release_rights_allowed_values",
        "record",
        "release_rights IN ('creator', 'others', 'family_or_friend', 'downloaded', 'NA')",
    )

    # 2. Update existing data from 'family_or_friend' to 'others'
    op.execute(
        "UPDATE record SET release_rights = 'others' WHERE release_rights = 'family_or_friend'"
    )

    # 3. Populate creator field for existing records with release_rights = 'creator'
    op.execute("""
        UPDATE record
        SET creator = (
            SELECT "user".name
            FROM "user"
            WHERE "user".id = record.user_id
        )
        WHERE release_rights = 'creator'
    """)

    # 4. Drop existing check constraint
    op.drop_constraint("ck_release_rights_allowed_values", "record", type_="check")

    # 5. Create new check constraint with updated values
    op.create_check_constraint(
        "ck_release_rights_allowed_values",
        "record",
        "release_rights IN ('creator', 'others', 'downloaded', 'NA')",
    )


def downgrade() -> None:
    """Remove creator field and revert release_rights enum from others to family_or_friend"""

    # 1. Update existing data from 'others' to 'family_or_friend'
    op.execute(
        "UPDATE record SET release_rights = 'family_or_friend' WHERE release_rights = 'others'"
    )

    # 2. Clear creator field (will be dropped anyway, but good practice)
    op.execute("UPDATE record SET creator = NULL")

    # 3. Drop new check constraint
    op.drop_constraint("ck_release_rights_allowed_values", "record", type_="check")

    # 4. Restore original check constraint
    op.create_check_constraint(
        "ck_release_rights_allowed_values",
        "record",
        "release_rights IN ('creator', 'family_or_friend', 'downloaded', 'NA')",
    )

    # 5. Remove the creator column
    op.drop_column("record", "creator")

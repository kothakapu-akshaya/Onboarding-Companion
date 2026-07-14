"""add_user_consent_fields

Revision ID: aafaf157ff08
Revises: a3086f39bb0c
Create Date: 2025-06-07 12:45:33.364399

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aafaf157ff08"
down_revision: Union[str, None] = "a3086f39bb0c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add consent fields to user table
    op.add_column(
        "user",
        sa.Column(
            "has_given_consent", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column("user", sa.Column("consent_given_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove consent fields from user table
    op.drop_column("user", "consent_given_at")
    op.drop_column("user", "has_given_consent")

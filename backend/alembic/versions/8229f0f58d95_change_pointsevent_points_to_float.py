"""Change PointsEvent.points to float

Revision ID: 8229f0f58d95
Revises: 76ee24a75499
Create Date: 2025-10-04 13:22:45.221029

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "8229f0f58d95"
down_revision: Union[str, None] = "76ee24a75499"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # This is the only required change for this migration.
    op.alter_column(
        "pointsevent",
        "points",
        existing_type=sa.INTEGER(),
        type_=sa.Float(),
        existing_nullable=False,
        existing_server_default=sa.text("1"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # This reverts the change.
    op.alter_column(
        "pointsevent",
        "points",
        existing_type=sa.Float(),
        type_=sa.INTEGER(),
        existing_nullable=False,
        existing_server_default=sa.text("1"),
    )

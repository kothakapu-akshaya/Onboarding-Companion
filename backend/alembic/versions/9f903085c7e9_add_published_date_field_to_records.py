"""Add published_date field to records

Revision ID: 9f903085c7e9
Revises: 2c33e88d40eb
Create Date: 2025-09-20 16:38:25.788332

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f903085c7e9"
down_revision: Union[str, None] = "2c33e88d40eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add published_date field to record table."""
    op.add_column("record", sa.Column("published_date", sa.Date(), nullable=True))


def downgrade() -> None:
    """Remove published_date field from record table."""
    op.drop_column("record", "published_date")

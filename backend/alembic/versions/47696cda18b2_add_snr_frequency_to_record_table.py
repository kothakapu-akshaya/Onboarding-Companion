"""add snr_frequency to record table

Revision ID: 47696cda18b2
Revises: 2ed7a8955b7a
Create Date: 2025-08-16 18:52:43.576545

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "47696cda18b2"
down_revision: Union[str, None] = "2ed7a8955b7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("record", sa.Column("snr_frequency", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("record", "snr_frequency")

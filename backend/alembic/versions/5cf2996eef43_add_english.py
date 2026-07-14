"""add_english

Revision ID: 5cf2996eef43
Revises: 77cae534757f
Create Date: 2026-04-25 15:23:12.198290

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5cf2996eef43"
down_revision: Union[str, None] = "9a1b2c3d4e60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("ck_language_allowed_values", "record", type_="check")
    op.create_check_constraint(
        "ck_language_allowed_values",
        "record",
        "language IN ('assamese', 'bengali', 'bodo', 'dogri', 'english', 'gujarati', 'hindi', 'kannada', 'kashmiri', 'konkani', 'maithili', 'malayalam', 'marathi', 'meitei', 'nepali', 'odia', 'punjabi', 'sanskrit', 'santali', 'sindhi', 'tamil', 'telugu', 'urdu', 'NA')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_language_allowed_values", "record", type_="check")
    op.create_check_constraint(
        "ck_language_allowed_values",
        "record",
        "language IN ('assamese', 'bengali', 'bodo', 'dogri', 'gujarati', 'hindi', 'kannada', 'kashmiri', 'konkani', 'maithili', 'malayalam', 'marathi', 'meitei', 'nepali', 'odia', 'punjabi', 'sanskrit', 'santali', 'sindhi', 'tamil', 'telugu', 'urdu', 'NA')",
    )

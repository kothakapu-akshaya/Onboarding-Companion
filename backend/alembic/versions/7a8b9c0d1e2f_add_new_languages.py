"""add new languages

Revision ID: 7a8b9c0d1e2f
Revises: 6ef27a1b53e7
Create Date: 2026-05-16 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a8b9c0d1e2f"
down_revision: Union[str, None] = "6ef27a1b53e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("ck_language_allowed_values", "record", type_="check")
    op.create_check_constraint(
        "ck_language_allowed_values",
        "record",
        "language IN ('assamese', 'bengali', 'bhili', 'bodo', 'dogri', 'english', 'garo', 'gujarati', 'gondi', 'hindi', 'ho', 'kannada', 'khandeshi', 'kashmiri', 'khasi', 'konkani', 'kurukh', 'maithili', 'malayalam', 'marathi', 'mundari', 'meitei', 'nepali', 'odia', 'punjabi', 'sanskrit', 'santali', 'sindhi', 'tamil', 'telugu', 'tulu', 'urdu', 'NA')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_language_allowed_values", "record", type_="check")
    op.create_check_constraint(
        "ck_language_allowed_values",
        "record",
        "language IN ('assamese', 'bengali', 'bodo', 'dogri', 'english', 'gujarati', 'hindi', 'kannada', 'kashmiri', 'konkani', 'maithili', 'malayalam', 'marathi', 'meitei', 'nepali', 'odia', 'punjabi', 'sanskrit', 'santali', 'sindhi', 'tamil', 'telugu', 'urdu', 'NA')",
    )

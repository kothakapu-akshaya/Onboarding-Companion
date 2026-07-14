"""add language column to record

Revision ID: 8f79c133a37c
Revises: 47696cda18b2
Create Date: 2025-08-17 18:36:36.880986

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f79c133a37c"
down_revision: Union[str, None] = "47696cda18b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("record", sa.Column("language", sa.Text(), nullable=True))

    op.execute("UPDATE record SET language = 'NA' WHERE language IS NULL")

    allowed_languages = (
        "'assamese', 'bengali', 'bodo', 'dogri', 'gujarati', 'hindi', 'kannada', 'kashmiri', "
        "'konkani', 'maithili', 'malayalam', 'marathi', 'meitei', 'nepali', 'odia', "
        "'punjabi', 'sanskrit', 'santali', 'sindhi', 'tamil', 'telugu', 'urdu', 'NA'"
    )
    op.create_check_constraint(
        "ck_language_allowed_values", "record", f"language IN ({allowed_languages})"
    )

    op.alter_column(
        "record",
        "language",
        existing_type=sa.Text(),
        nullable=False,
        server_default="NA",
    )


def downgrade():
    op.drop_constraint("ck_language_allowed_values", "record", type_="check")
    op.drop_column("record", "language")

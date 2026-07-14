"""add BCP47 code column to language table

Revision ID: 7dace91d953b
Revises: 7d08531e7714
Create Date: 2026-06-29

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7dace91d953b"
down_revision: str | None = "7d08531e7714"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# name → BCP47 code for every default language
_LANGUAGE_CODES: dict[str, str] = {
    "assamese": "as",
    "bengali": "bn",
    "bhili": "bhb",
    "bodo": "brx",
    "dogri": "doi",
    "english": "en",
    "garo": "grt",
    "gondi": "gon",
    "gujarati": "gu",
    "ho": "hoc",
    "hindi": "hi",
    "kannada": "kn",
    "khandeshi": "khn",
    "kashmiri": "ks",
    "khasi": "kha",
    "konkani": "kok",
    "kurukh": "kru",
    "maithili": "mai",
    "malayalam": "ml",
    "marathi": "mr",
    "mundari": "unr",
    "meitei": "mni",
    "nepali": "ne",
    "odia": "or",
    "punjabi": "pa",
    "sanskrit": "sa",
    "santali": "sat",
    "sindhi": "sd",
    "tamil": "ta",
    "telugu": "te",
    "tulu": "tcy",
    "urdu": "ur",
    "NA": "und",
}


def upgrade() -> None:
    op.add_column(
        "language",
        sa.Column("code", sa.String(10), nullable=True),
    )
    op.create_index("ix_language_code", "language", ["code"], unique=True)

    conn = op.get_bind()
    for name, code in _LANGUAGE_CODES.items():
        conn.execute(
            sa.text("UPDATE language SET code = :code WHERE name = :name"),
            {"code": code, "name": name},
        )


def downgrade() -> None:
    op.drop_index("ix_language_code", table_name="language")
    op.drop_column("language", "code")

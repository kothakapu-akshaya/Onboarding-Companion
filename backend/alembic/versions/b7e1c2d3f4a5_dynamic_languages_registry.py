"""add dynamic languages registry

Revision ID: b7e1c2d3f4a5
Revises: 5cf2996eef43
Create Date: 2026-05-16 12:00:00.000000

"""

from typing import Union
from collections.abc import Sequence
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlmodel.sql.sqltypes import AutoString


revision: str = "b7e1c2d3f4a5"
down_revision: str | None = "7a8b9c0d1e2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DEFAULT_LANGUAGE_NAMES = [
    "assamese",
    "bengali",
    "bhili",
    "bodo",
    "dogri",
    "english",
    "garo",
    "gondi",
    "gujarati",
    "ho",
    "hindi",
    "kannada",
    "khandeshi",
    "kashmiri",
    "khasi",
    "konkani",
    "kurukh",
    "maithili",
    "malayalam",
    "marathi",
    "mundari",
    "meitei",
    "nepali",
    "odia",
    "punjabi",
    "sanskrit",
    "santali",
    "sindhi",
    "tamil",
    "telugu",
    "tulu",
    "urdu",
    "NA",
]


def upgrade() -> None:
    op.execute("DROP TYPE IF EXISTS language CASCADE")
    op.create_table(
        "language",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", AutoString(length=100), nullable=False),
        sa.Column("spoken_population", sa.Integer(), nullable=True),
        sa.Column("geo_area", AutoString(length=500), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_language_name"), "language", ["name"], unique=True)

    language_table = sa.table(
        "language",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String(length=100)),
        sa.column("spoken_population", sa.Integer()),
        sa.column("geo_area", sa.String(length=500)),
        sa.column("created_by", sa.Uuid()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )

    op.bulk_insert(
        language_table,
        [
            {
                "id": uuid.uuid4(),
                "name": language,
                "spoken_population": None,
                "geo_area": None,
                "created_by": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            for language in DEFAULT_LANGUAGE_NAMES
        ],
    )

    op.drop_constraint("ck_language_allowed_values", "record", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "ck_language_allowed_values",
        "record",
        "language IN ('assamese', 'bengali', 'bhili', 'bodo', 'dogri', 'english', 'garo', 'gujarati', 'gondi', 'hindi', 'ho', 'kannada', 'khandeshi', 'kashmiri', 'khasi', 'konkani', 'kurukh', 'maithili', 'malayalam', 'marathi', 'mundari', 'meitei', 'nepali', 'odia', 'punjabi', 'sanskrit', 'santali', 'sindhi', 'tamil', 'telugu', 'tulu', 'urdu', 'NA')",
    )
    op.drop_index(op.f("ix_language_name"), table_name="language")
    op.drop_table("language")

"""normalize Record.language from names to BCP47 codes

Revision ID: 643713e8ddab
Revises: 7dace91d953b
Create Date: 2026-06-29

Converts every Record.language value from a LanguageEntry name (e.g. "telugu")
to the corresponding BCP47 code (e.g. "te").  Records whose language cannot
be resolved are set to "und" (BCP47 undetermined).  A backup column preserves
the original value so the downgrade can restore exact string values.

Run ONLY after 7dace91d953b (add BCP47 code to language) has been applied and
scripts/seed_language_codes.py has been run (or ensure_default_languages() has
seeded all codes).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "643713e8ddab"
down_revision: str | None = "7dace91d953b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # Preserve original values for reversibility.
    op.add_column(
        "record",
        sa.Column("language_name_backup", sa.String(100), nullable=True),
    )
    conn.execute(
        sa.text("UPDATE record SET language_name_backup = language")
    )

    # Convert name → BCP47 code for all rows that match a LanguageEntry.
    conn.execute(
        sa.text(
            """
            UPDATE record
            SET language = l.code
            FROM language l
            WHERE record.language = l.name
              AND l.code IS NOT NULL
            """
        )
    )

    # Any record whose language is not yet a registered code → "und".
    conn.execute(
        sa.text(
            """
            UPDATE record
            SET language = 'und'
            WHERE language NOT IN (
                SELECT code FROM language WHERE code IS NOT NULL
            )
            """
        )
    )

    # Log how many records were set to 'und' for visibility.
    result = conn.execute(
        sa.text("SELECT count(*) FROM record WHERE language = 'und'")
    )
    count = result.scalar()
    if count:
        print(
            f"  {count} record(s) had unresolvable language values "
            "and were set to 'und'."
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Restore original language values from backup.
    conn.execute(
        sa.text(
            """
            UPDATE record
            SET language = language_name_backup
            WHERE language_name_backup IS NOT NULL
            """
        )
    )

    op.drop_column("record", "language_name_backup")

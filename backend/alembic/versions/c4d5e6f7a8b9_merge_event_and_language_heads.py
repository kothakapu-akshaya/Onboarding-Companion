"""compatibility bridge for old local event-service revision

Revision ID: c4d5e6f7a8b9
Revises: b7e1c2d3f4a5
Create Date: 2026-05-21 00:00:00.000000

"""

from collections.abc import Sequence

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b7e1c2d3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Bridge old local databases to the cleaned event-service chain."""


def downgrade() -> None:
    """No-op downgrade for compatibility bridge."""

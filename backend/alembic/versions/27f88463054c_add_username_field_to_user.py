"""add_username_field_to_user

Revision ID: 27f88463054c
Revises: 47182ecc8f0d
Create Date: 2025-12-01 22:37:22.119846

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "27f88463054c"
down_revision: Union[str, None] = "40da0bd23824"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add username column to user table (nullable first for backfill)
    op.add_column("user", sa.Column("username", sa.String(length=50), nullable=True))

    # Backfill existing users with generated usernames
    # Format: firstname_lastname_XXXX or firstname_XXXX (if no lastname)
    connection = op.get_bind()

    # Get all users and generate usernames
    result = connection.execute(text('SELECT id, name FROM "user"'))
    users = result.fetchall()

    for user_id, name in users:
        # Clean the name and create username base
        name_parts = name.strip().lower().split()

        if len(name_parts) >= 2:
            # Use first and last name
            username_base = f"{name_parts[0]}_{name_parts[-1]}"
        elif len(name_parts) == 1:
            # Use only first name
            username_base = name_parts[0]
        else:
            # Fallback to "user" if name is empty
            username_base = "user"

        # Remove non-alphanumeric characters (except underscore)
        username_base = "".join(c for c in username_base if c.isalnum() or c == "_")

        # Ensure username is not empty after cleaning
        if not username_base:
            username_base = "user"

        # Generate unique username with random suffix
        import random

        unique_found = False
        max_attempts = 100

        for attempt in range(max_attempts):
            random_suffix = random.randint(1000, 9999)
            username = f"{username_base}_{random_suffix}"

            # Check if username already exists
            check_result = connection.execute(
                text('SELECT COUNT(*) FROM "user" WHERE username = :username'),
                {"username": username},
            )
            count = check_result.scalar()

            if count == 0:
                # Update user with unique username
                connection.execute(
                    text('UPDATE "user" SET username = :username WHERE id = :user_id'),
                    {"username": username, "user_id": user_id},
                )
                unique_found = True
                break

        if not unique_found:
            raise Exception(
                f"Could not generate unique username for user {user_id} after {max_attempts} attempts"
            )

    # Now make username NOT NULL and add unique constraint
    op.alter_column("user", "username", nullable=False)
    op.create_index(op.f("ix_user_username"), "user", ["username"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index and column
    op.drop_index(op.f("ix_user_username"), table_name="user")
    op.drop_column("user", "username")

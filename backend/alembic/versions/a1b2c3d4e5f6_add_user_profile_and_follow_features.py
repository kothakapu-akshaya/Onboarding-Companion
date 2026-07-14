"""Add user profile and follow features

Revision ID: a1b2c3d4e5f6
Revises: 6bb42322f533
Create Date: 2025-09-25 02:10:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "6bb42322f533"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user profile fields and follow system."""
    # Add NEW profile fields to user table (skip profile_picture_path - already exists)
    op.add_column("user", sa.Column("short_bio", sa.String(length=500), nullable=True))
    op.add_column("user", sa.Column("profession", sa.String(length=200), nullable=True))
    op.add_column(
        "user", sa.Column("organisation", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "user", sa.Column("places_lived", sa.String(length=5000), nullable=True)
    )
    op.add_column(
        "user", sa.Column("from_place", sa.String(length=2000), nullable=True)
    )
    op.add_column(
        "user",
        sa.Column("social_media_profiles", sa.String(length=2000), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("language_proficiencies", sa.String(length=2000), nullable=True),
    )

    # Add privacy settings with default values (using TEXT with check constraints like language field)
    op.add_column(
        "user",
        sa.Column("phone_privacy", sa.Text(), nullable=False, server_default="private"),
    )
    op.add_column(
        "user",
        sa.Column("email_privacy", sa.Text(), nullable=False, server_default="private"),
    )

    # Add check constraints for privacy field values
    privacy_values = "'public', 'private'"
    op.create_check_constraint(
        "ck_phone_privacy_allowed_values",
        "user",
        f"phone_privacy IN ({privacy_values})",
    )
    op.create_check_constraint(
        "ck_email_privacy_allowed_values",
        "user",
        f"email_privacy IN ({privacy_values})",
    )

    # Rename place to current_place
    op.alter_column("user", "place", new_column_name="current_place")

    # Create user_follows table for follow system
    op.create_table(
        "user_follows",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("follower_id", postgresql.UUID(), nullable=False),
        sa.Column("following_id", postgresql.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["follower_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["following_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add indexes for user_follows table
    op.create_index("ix_user_follows_follower_id", "user_follows", ["follower_id"])
    op.create_index("ix_user_follows_following_id", "user_follows", ["following_id"])

    # Add unique constraint to prevent duplicate follows
    op.create_unique_constraint(
        "uq_user_follows_follower_following",
        "user_follows",
        ["follower_id", "following_id"],
    )


def downgrade() -> None:
    """Remove user profile fields and follow system."""
    # Drop user_follows table
    op.drop_table("user_follows")

    # Rename current_place back to place
    op.alter_column("user", "current_place", new_column_name="place")

    # Drop privacy settings and their constraints
    op.drop_constraint("ck_email_privacy_allowed_values", "user", type_="check")
    op.drop_constraint("ck_phone_privacy_allowed_values", "user", type_="check")
    op.drop_column("user", "email_privacy")
    op.drop_column("user", "phone_privacy")

    # Drop profile fields (skip profile_picture_path - was pre-existing)
    op.drop_column("user", "language_proficiencies")
    op.drop_column("user", "social_media_profiles")
    op.drop_column("user", "from_place")
    op.drop_column("user", "places_lived")
    op.drop_column("user", "organisation")
    op.drop_column("user", "profession")
    op.drop_column("user", "short_bio")

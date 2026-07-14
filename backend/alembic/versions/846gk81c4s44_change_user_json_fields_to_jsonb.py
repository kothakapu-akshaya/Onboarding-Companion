"""change user json fields to jsonb

Revision ID: 846gk81c4s44
Revises: 8229f0f58d95
Create Date: 2026-01-22 10:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "846gk81c4s44"
down_revision: Union[str, None] = "8229f0f58d95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a temporary function to safely convert text to JSONB
    op.execute("""
        CREATE OR REPLACE FUNCTION safe_text_to_jsonb(input_text TEXT)
        RETURNS JSONB AS $$
        BEGIN
            IF input_text IS NULL OR input_text = '' OR input_text = 'null' THEN
                RETURN NULL;
            END IF;

            BEGIN
                RETURN input_text::JSONB;
            EXCEPTION
                WHEN OTHERS THEN
                    RETURN NULL;
            END;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Use the function to convert the columns safely
    op.execute(
        'ALTER TABLE "user" ALTER COLUMN places_lived TYPE JSONB USING safe_text_to_jsonb(places_lived)'
    )
    op.execute(
        'ALTER TABLE "user" ALTER COLUMN from_place TYPE JSONB USING safe_text_to_jsonb(from_place)'
    )
    op.execute(
        'ALTER TABLE "user" ALTER COLUMN social_media_profiles TYPE JSONB USING safe_text_to_jsonb(social_media_profiles)'
    )
    op.execute(
        'ALTER TABLE "user" ALTER COLUMN language_proficiencies TYPE JSONB USING safe_text_to_jsonb(language_proficiencies)'
    )

    # Drop the temporary function
    op.execute("DROP FUNCTION IF EXISTS safe_text_to_jsonb(TEXT);")


def downgrade() -> None:
    # Convert JSONB back to VARCHAR using explicit casting
    op.execute(
        'ALTER TABLE "user" ALTER COLUMN language_proficiencies TYPE VARCHAR(2000) USING CASE WHEN language_proficiencies IS NULL THEN NULL ELSE language_proficiencies::TEXT END'
    )
    op.execute(
        'ALTER TABLE "user" ALTER COLUMN social_media_profiles TYPE VARCHAR(2000) USING CASE WHEN social_media_profiles IS NULL THEN NULL ELSE social_media_profiles::TEXT END'
    )
    op.execute(
        'ALTER TABLE "user" ALTER COLUMN from_place TYPE VARCHAR(2000) USING CASE WHEN from_place IS NULL THEN NULL ELSE from_place::TEXT END'
    )
    op.execute(
        'ALTER TABLE "user" ALTER COLUMN places_lived TYPE VARCHAR(5000) USING CASE WHEN places_lived IS NULL THEN NULL ELSE places_lived::TEXT END'
    )

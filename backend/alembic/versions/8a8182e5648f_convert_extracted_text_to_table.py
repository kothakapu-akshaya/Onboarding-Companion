"""convert extracted text to table

Revision ID: 8a8182e5648f
Revises: 9a1b2c3d4e60
Create Date: 2026-04-07 12:00:00.000000

"""

from typing import Sequence, Union
from uuid import uuid4
from datetime import datetime, timezone
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column, select, insert


# revision identifiers, used by Alembic.
revision: str = "8a8182e5648f"
down_revision: Union[str, None] = "9b2c4d6e8f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the new extracted_text table
    op.create_table(
        "extractedtext",
        sa.Column("uid", sa.UUID(), nullable=False),
        sa.Column("record_id", sa.UUID(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("extraction_type", sa.String(length=20), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("processing_date", sa.String(length=100), nullable=True),
        sa.Column("segments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "named_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "extraction_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("record_id"),
    )
    op.create_index(
        op.f("ix_extractedtext_extraction_type"),
        "extractedtext",
        ["extraction_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_extractedtext_record_id"), "extractedtext", ["record_id"], unique=True
    )
    op.create_foreign_key(None, "extractedtext", "record", ["record_id"], ["uid"])

    # 2. Migrate data from record.extracted_text to the new table
    connection = op.get_bind()

    # Define the record table for selecting data
    record_table = sa.table(
        "record",
        sa.column("uid", sa.UUID()),
        sa.column("extracted_text", postgresql.JSONB()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )

    # Select all records with extracted text
    results = connection.execute(
        sa.select(
            record_table.c.uid,
            record_table.c.extracted_text,
            record_table.c.created_at,
            record_table.c.updated_at,
        ).where(record_table.c.extracted_text.isnot(None))
    ).fetchall()

    extractedtext_table = sa.table(
        "extractedtext",
        sa.column("uid", sa.UUID()),
        sa.column("record_id", sa.UUID()),
        sa.column("confidence", sa.Float()),
        sa.column("language", sa.String()),
        sa.column("extraction_type", sa.String()),
        sa.column("quality_score", sa.Float()),
        sa.column("notes", sa.Text()),
        sa.column("summary", sa.Text()),
        sa.column("model_name", sa.String()),
        sa.column("processing_date", sa.String()),
        sa.column("segments", postgresql.JSONB()),
        sa.column("named_entities", postgresql.JSONB()),
        sa.column("extraction_metadata", postgresql.JSONB()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )

    now = datetime.now(timezone.utc)
    insert_rows = []
    for record_uid, et_data, created_at, updated_at in results:
        created_at = created_at or now
        updated_at = updated_at or now

        if not isinstance(et_data, dict):
            insert_rows.append(
                {
                    "uid": uuid4(),
                    "record_id": record_uid,
                    "confidence": None,
                    "language": None,
                    "extraction_type": "manual",
                    "quality_score": None,
                    "notes": None,
                    "summary": None,
                    "model_name": None,
                    "processing_date": None,
                    "segments": None,
                    "named_entities": None,
                    "extraction_metadata": None,
                    "created_at": created_at,
                    "updated_at": updated_at,
                }
            )
            continue

        insert_rows.append(
            {
                "uid": uuid4(),
                "record_id": record_uid,
                "confidence": et_data.get("confidence"),
                "language": et_data.get("language"),
                "extraction_type": et_data.get("extraction_type", "manual"),
                "quality_score": et_data.get("quality_score"),
                "notes": et_data.get("notes"),
                "summary": et_data.get("summary"),
                "model_name": et_data.get("model_name"),
                "processing_date": et_data.get("processing_date"),
                "segments": et_data.get("segments"),
                "named_entities": et_data.get("named_entities"),
                "extraction_metadata": et_data.get("metadata"),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

    if insert_rows:
        connection.execute(sa.insert(extractedtext_table), insert_rows)

    # 3. Drop the old column from the record table
    op.drop_column("record", "extracted_text")


def downgrade() -> None:
    # 1. Add back the extracted_text column to the record table
    op.add_column(
        "record",
        sa.Column(
            "extracted_text", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )

    # 2. Migrate data back from the extractedtext table to the record table
    connection = op.get_bind()

    et_table = sa.table(
        "extractedtext",
        sa.column("record_id", sa.UUID()),
        sa.column("confidence", sa.Float()),
        sa.column("language", sa.String()),
        sa.column("extraction_type", sa.String()),
        sa.column("quality_score", sa.Float()),
        sa.column("notes", sa.Text()),
        sa.column("summary", sa.Text()),
        sa.column("model_name", sa.String()),
        sa.column("processing_date", sa.String()),
        sa.column("segments", postgresql.JSONB()),
        sa.column("named_entities", postgresql.JSONB()),
        sa.column("extraction_metadata", postgresql.JSONB()),
    )

    results = connection.execute(sa.select(et_table)).fetchall()

    updates_data = []
    for row in results:
        # Derive transcription from segments (OCR joins by \n, ASR by space)
        transcription = None
        if row.segments:
            if row.extraction_type == "ocr":
                transcription = "\n".join(
                    s.get("text", "") for s in row.segments if s.get("text")
                )
            else:
                transcription = " ".join(
                    s.get("text", "") for s in row.segments if s.get("text")
                )

        # Reconstruct the JSON object
        et_data = {
            "transcription": transcription,
            "confidence": row.confidence,
            "language": row.language,
            "extraction_type": row.extraction_type,
            "quality_score": row.quality_score,
            "notes": row.notes,
            "summary": row.summary,
            "model_name": row.model_name,
            "processing_date": row.processing_date,
            "segments": row.segments,
            "named_entities": row.named_entities,
            "metadata": row.extraction_metadata,
        }

        # Remove None values to keep it clean
        et_data = {k: v for k, v in et_data.items() if v is not None}
        updates_data.append(
            {"record_id": str(row.record_id), "extracted_text": et_data}
        )

    if updates_data:
        connection.execute(
            sa.text("""
                UPDATE record r
                SET extracted_text = d.et
                FROM (
                    SELECT (value->>'record_id')::uuid AS rid,
                           value->'extracted_text' AS et
                    FROM jsonb_array_elements(:updates::jsonb)
                ) d
                WHERE r.uid = d.rid
            """),
            {"updates": json.dumps(updates_data)},
        )

    # 3. Drop the extractedtext table
    op.drop_table("extractedtext")

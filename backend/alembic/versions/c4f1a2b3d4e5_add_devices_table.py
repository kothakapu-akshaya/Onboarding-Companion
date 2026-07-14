"""add devices table

Revision ID: c4f1a2b3d4e5
Revises: d6e7f8a9b0c1
Create Date: 2026-06-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4f1a2b3d4e5"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "device",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(length=255), nullable=False),
        sa.Column("fingerprint_hash", sa.String(length=255), nullable=True),
        sa.Column("device_name", sa.String(length=200), nullable=True),
        sa.Column(
            "os_type",
            sa.Enum(
                "android",
                "ios",
                "linux",
                "windows",
                "macos",
                "other",
                name="ostype",
            ),
            nullable=True,
        ),
        sa.Column("os_name", sa.String(length=100), nullable=True),
        sa.Column("os_version", sa.String(length=100), nullable=True),
        sa.Column("cpu_model", sa.String(length=200), nullable=True),
        sa.Column("cpu_architecture", sa.String(length=50), nullable=True),
        sa.Column("cpu_cores", sa.Integer(), nullable=True),
        sa.Column("ram_gb", sa.Float(), nullable=True),
        sa.Column("gpu_model", sa.String(length=200), nullable=True),
        sa.Column("gpu_cores", sa.Integer(), nullable=True),
        sa.Column("gpu_vram_gb", sa.Float(), nullable=True),
        sa.Column("download_speed_mbps", sa.Float(), nullable=True),
        sa.Column("upload_speed_mbps", sa.Float(), nullable=True),
        sa.Column(
            "compute_tier",
            sa.Enum("low", "medium", "high", name="computetier"),
            nullable=True,
        ),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint("device_id", name="uq_device_device_id"),
    )
    op.create_index(
        op.f("ix_device_fingerprint_hash"),
        "device",
        ["fingerprint_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_device_os_type"), "device", ["os_type"], unique=False
    )
    op.create_index(
        op.f("ix_device_compute_tier"), "device", ["compute_tier"], unique=False
    )

    op.create_table(
        "userdevice",
        sa.Column("uid", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("device_uid", sa.Uuid(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["device_uid"], ["device.uid"]),
        sa.PrimaryKeyConstraint("uid"),
        sa.UniqueConstraint(
            "user_id", "device_uid", name="uq_user_device_user_id_device_uid"
        ),
    )
    op.create_index(
        op.f("ix_userdevice_user_id"), "userdevice", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_userdevice_device_uid"),
        "userdevice",
        ["device_uid"],
        unique=False,
    )

    op.add_column("record", sa.Column("device_uid", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_record_device_uid"), "record", ["device_uid"], unique=False
    )
    op.create_foreign_key(
        "fk_record_device_uid_device",
        "record",
        "device",
        ["device_uid"],
        ["uid"],
    )

    op.add_column(
        "extractedtext", sa.Column("device_uid", sa.Uuid(), nullable=True)
    )
    op.create_index(
        op.f("ix_extractedtext_device_uid"),
        "extractedtext",
        ["device_uid"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_extractedtext_device_uid_device",
        "extractedtext",
        "device",
        ["device_uid"],
        ["uid"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_extractedtext_device_uid_device", "extractedtext", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_extractedtext_device_uid"), table_name="extractedtext"
    )
    op.drop_column("extractedtext", "device_uid")

    op.drop_constraint(
        "fk_record_device_uid_device", "record", type_="foreignkey"
    )
    op.drop_index(op.f("ix_record_device_uid"), table_name="record")
    op.drop_column("record", "device_uid")

    op.drop_index(op.f("ix_userdevice_device_uid"), table_name="userdevice")
    op.drop_index(op.f("ix_userdevice_user_id"), table_name="userdevice")
    op.drop_table("userdevice")
    op.drop_index(op.f("ix_device_compute_tier"), table_name="device")
    op.drop_index(op.f("ix_device_os_type"), table_name="device")
    op.drop_index(op.f("ix_device_fingerprint_hash"), table_name="device")
    op.drop_table("device")
    sa.Enum(name="computetier").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ostype").drop(op.get_bind(), checkfirst=True)

import os
import sys  # Ensure sys is imported
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import all models to ensure they're registered with SQLModel
from app.models.user import User
from app.models.role import Role
from app.models.category import Category
from app.models.record import Record
from app.models.extracted_text import ExtractedText
from app.models.otp import OTP
from app.models.associations import UserRoleLink
from app.models.points import PointsEvent
from app.models.institution import Institution
from app.models.course import Course
from app.models.record_history import (
    RecordHistory,
    RecordMajorSnapshot,
    RecordRestore,
    RecordVersion,
)
from app.models.change_enums import ChangeType, ChangeSource

# Make sure the app directory is in the path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import SQLModel


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

target_metadata = SQLModel.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects during migration generation.
    Exclude PostGIS system tables and other system objects.
    """
    if type_ == "table" and name in [
        "spatial_ref_sys",
        "geography_columns",
        "geometry_columns",
        "raster_columns",
        "raster_overviews",
    ]:
        return False
    return True


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects during migration generation.
    Exclude PostGIS system tables and other system objects.
    """
    if type_ == "table" and name in [
        "spatial_ref_sys",
        "geography_columns",
        "geometry_columns",
        "raster_columns",
        "raster_overviews",
        # Add other TIGER/PostGIS tables if Alembic tries to drop them
        "tiger",
        "tiger_data",
        "tiger_geocoder",
        "tiger_pages",
        "tiger_place",
        "tiger_roads",
        "tiger_zip",
        "geocode_settings",
        "geocode_settings_default",
        "loader_lookuptables",
        "loader_platform",
        "loader_variables",
        "pagc_gaz",
        "pagc_lex",
        "pagc_rules",
        "tabblock",
        "addrfeat",
        "bg",
        "county",
        "cousub",
        "direction_lookup",
        "edges",
        "featnames",
        "state",
        "street_type_lookup",
        "tract",
        "zcta5",
        "zip_lookup",
        "zip_lookup_all",
        "zip_lookup_base",
        "zip_state",
        "zip_state_loc",
    ]:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Get DATABASE_URL from environment variables
    from app.core.config import settings

    DATABASE_URL = settings.DATABASE_URL

    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    url = DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get DATABASE_URL from environment variables
    from app.core.config import settings

    DATABASE_URL = settings.DATABASE_URL

    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

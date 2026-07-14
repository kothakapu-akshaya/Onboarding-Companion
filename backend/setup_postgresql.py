#!/usr/bin/env python3
"""PostgreSQL Database Setup and Connection Test Script with PostGIS Support.

This script helps you:
1. Test the PostgreSQL connection
2. Create the database if it doesn't exist
3. Enable PostGIS extension for spatial data
4. Enable pg_trgm extension for fuzzy text search
5. Run migrations
6. Seed initial data
7. Validate PostGIS functionality

Usage:
    python setup_postgresql.py [--create-db] [--test-connection] \
    [--enable-postgis] [--enable-pgtrgm] [--migrate] [--seed] \
    [--validate-postgis]
"""

import argparse
import os
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text

# Add the app directory to the path
sys.path.insert(
    0, os.path.realpath(os.path.join(os.path.dirname(__file__), "."))
)

from app.core.config import settings  # noqa: E402

server_url = os.getenv("DATABASE_URL")


def get_server_url() -> str:
    """Return DATABASE_URL, failing fast if unset."""
    if server_url is None:
        raise RuntimeError("DATABASE_URL is not set")
    return server_url


def test_postgres_connection() -> bool:
    """Test if PostgreSQL server is accessible."""
    try:
        # Connect to PostgreSQL server (without specifying a database)
        engine = create_engine(get_server_url())

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version_row = result.fetchone()
            if version_row and len(version_row) > 0:
                version = version_row[0]
                print("✅ PostgreSQL server connection successful!")
                print(f"   Version: {version}")
                return True
            else:
                print("❌ Could not get PostgreSQL version")
                return False
    except Exception as e:
        print(f"❌ PostgreSQL server connection failed: {e}")
        print("   Make sure PostgreSQL is running and credentials are correct.")
        return False


def database_exists() -> bool:
    """Check if the target database exists."""
    try:
        engine = create_engine(get_server_url())

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    f"SELECT 1 FROM pg_database WHERE "
                    f"datname='{settings.DB_NAME}'"
                )
            )
            exists = result.fetchone() is not None
            return exists
    except Exception as e:
        print(f"❌ Error checking database existence: {e}")
        return False


def create_database() -> bool:
    """Create the database if it doesn't exist."""
    if database_exists():
        print(f"✅ Database '{settings.DB_NAME}' already exists.")
        return True

    try:
        # Connect using psycopg2 for database creation
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        cursor = conn.cursor()
        cursor.execute(f'CREATE DATABASE "{settings.DB_NAME}"')
        cursor.close()
        conn.close()

        print(f"✅ Database '{settings.DB_NAME}' created successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to create database: {e}")
        return False


def test_database_connection() -> bool:
    """Test connection to the target database."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_row = result.fetchone()
            if db_row and len(db_row) > 0:
                db_name = db_row[0]
                print(f"✅ Database '{db_name}' connection successful!")
                return True
            else:
                print("❌ Could not get current database name")
                return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def check_postgis_availability() -> bool:
    """Check if PostGIS extension is available in PostgreSQL."""
    try:
        engine = create_engine(get_server_url())

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT name FROM pg_available_extensions "
                    "WHERE name = 'postgis'"
                )
            )
            available = result.fetchone() is not None

            if available:
                print("✅ PostGIS extension is available in PostgreSQL!")
                return True
            else:
                print("❌ PostGIS extension is not available.")
                print(
                    "   Install PostGIS: sudo apt-get install "
                    "postgresql-postgis or brew install postgis"
                )
                return False
    except Exception as e:
        print(f"❌ Error checking PostGIS availability: {e}")
        return False


def check_postgis_enabled() -> bool:
    """Check if PostGIS extension is enabled in the target database."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT extname FROM pg_extension WHERE extname = 'postgis'"
                )
            )
            enabled = result.fetchone() is not None
            return enabled
    except Exception as e:
        print(f"❌ Error checking PostGIS status: {e}")
        return False


def enable_postgis() -> bool:
    """Enable PostGIS extension in the target database."""
    if check_postgis_enabled():
        print("✅ PostGIS extension is already enabled.")
        return True

    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Enable PostGIS extension
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.commit()

            # Verify installation by checking PostGIS version
            result = conn.execute(text("SELECT PostGIS_Version()"))
            version_row = result.fetchone()
            if version_row and len(version_row) > 0:
                version = version_row[0]
                print("✅ PostGIS extension enabled successfully!")
                print(f"   PostGIS Version: {version}")
                return True
            else:
                print("❌ PostGIS enabled but version check failed")
                return False
    except Exception as e:
        print(f"❌ Failed to enable PostGIS extension: {e}")
        return False


def enable_pg_trgm() -> bool:
    """Enable pg_trgm extension for trigram-based fuzzy text search."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            conn.commit()
            print("✅ pg_trgm extension enabled successfully!")
            return True
    except Exception as e:
        print(f"❌ Failed to enable pg_trgm extension: {e}")
        return False


def validate_postgis_functionality() -> bool:
    """Validate that PostGIS is working correctly.

    Tests basic spatial operations.
    """
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Test basic PostGIS functions
            tests = [
                {
                    "name": "PostGIS Version",
                    "query": "SELECT PostGIS_Version()",
                    "expected": "version string",
                },
                {
                    "name": "Point Creation",
                    "query": (
                        "SELECT ST_GeomFromText('POINT(78.4772 17.4065)', 4326)"
                    ),
                    "expected": "geometry object",
                },
                {
                    "name": "Coordinate Extraction",
                    "query": (
                        "SELECT ST_X("
                        "ST_GeomFromText('POINT(78.4772 17.4065)', "
                        "4326)) as lng, "
                        "ST_Y(ST_GeomFromText("
                        "'POINT(78.4772 17.4065)', 4326)) as lat"
                    ),
                    "expected": "coordinates",
                },
                {
                    "name": "Distance Calculation",
                    "query": (
                        "SELECT ST_Distance("
                        "ST_GeomFromText('POINT(78.4772 17.4065)', "
                        "4326), "
                        "ST_GeomFromText('POINT(77.5946 12.9716)', "
                        "4326)) as distance"
                    ),
                    "expected": "distance value",
                },
            ]

            print("🧪 Testing PostGIS functionality...")
            all_passed = True

            for test in tests:
                try:
                    result = conn.execute(text(test["query"]))
                    row = result.fetchone()
                    if row:
                        print(f"  ✅ {test['name']}: PASSED")
                        if test["name"] == "PostGIS Version":
                            print(f"     Version: {row[0]}")
                        elif test["name"] == "Coordinate Extraction":
                            print(
                                f"     Coordinates: lng={row[0]}, lat={row[1]}"
                            )
                        elif test["name"] == "Distance Calculation":
                            print(f"     Distance: {row[0]:.2f} degrees")
                    else:
                        print(f"  ❌ {test['name']}: FAILED (no result)")
                        all_passed = False
                except Exception as e:
                    print(f"  ❌ {test['name']}: FAILED ({e})")
                    all_passed = False

            if all_passed:
                print("✅ All PostGIS functionality tests passed!")
                return True
            else:
                print("❌ Some PostGIS functionality tests failed.")
                return False

    except Exception as e:
        print(f"❌ PostGIS validation failed: {e}")
        return False


def validate_record_table_postgis() -> bool:
    """Validate that the Record table has the correct PostGIS schema."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            # Check if record table exists
            result = conn.execute(
                text(
                    """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'record'
            """
                )
            )

            if not result.fetchone():
                print(
                    "ℹ️  Record table not found "
                    "(migrations may not have been run yet)"
                )
                return True  # Not an error if migrations haven't been run

            # Check if location column exists and is geometry type
            result = conn.execute(
                text(
                    """
                SELECT 
                    column_name,
                    data_type,
                    udt_name
                FROM information_schema.columns 
                WHERE table_name = 'record' 
                AND column_name = 'location'
            """
                )
            )

            row = result.fetchone()
            if row:
                column_name, data_type, udt_name = row
                if udt_name == "geometry":
                    print(
                        "✅ Record table has PostGIS location "
                        "column (geometry type)"
                    )

                    # Check for spatial index
                    result = conn.execute(
                        text(
                            """
                        SELECT indexname 
                        FROM pg_indexes 
                        WHERE tablename = 'record' 
                        AND indexname LIKE '%location%'
                    """
                        )
                    )

                    index_row = result.fetchone()
                    if index_row:
                        print(f"✅ Spatial index found: {index_row[0]}")
                    else:
                        print(
                            "ℹ️  No spatial index found "
                            "(will be created during migration)"
                        )

                    return True
                else:
                    print(
                        f"❌ Location column exists but wrong type: "
                        f"{udt_name} (expected: geometry)"
                    )
                    return False
            else:
                print(
                    "ℹ️  Location column not found "
                    "(old schema or migrations not run)"
                )
                return True  # Not an error if using old schema

    except Exception as e:
        print(f"❌ Record table validation failed: {e}")
        return False


def run_migrations() -> bool:
    """Run Alembic migrations."""
    try:
        import subprocess

        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=".",
        )
        if result.returncode == 0:
            print("✅ Database migrations completed successfully!")
            print(result.stdout)
            return True
        else:
            print("❌ Migration failed:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return False


def seed_initial_data() -> bool:
    """Seed initial data."""
    try:
        from sqlmodel import Session

        from app.db.session import engine
        from app.models import Category, Role, RoleEnum

        with Session(engine) as session:
            from sqlmodel import select

            # Check if roles already exist
            existing_roles = len(session.exec(select(Role)).all())
            if existing_roles > 0:
                print(f"✅ Roles already exist ({existing_roles} roles found).")
            else:
                # Create default roles
                roles = [
                    Role(name=RoleEnum.admin, description="Administrator role"),
                    Role(name=RoleEnum.user, description="Regular user role"),
                    Role(
                        name=RoleEnum.reviewer,
                        description="Content reviewer role",
                    ),
                ]

                for role in roles:
                    session.add(role)

            # Check if categories already exist
            existing_categories = len(session.exec(select(Category)).all())
            if existing_categories > 0:
                print(
                    f"✅ Categories already exist "
                    f"({existing_categories} categories found)."
                )
            else:
                # Create default categories
                categories = [
                    Category(
                        name="fables",
                        title="Fables",
                        description=(
                            "Traditional stories with moral lessons "
                            "and mythical characters"
                        ),
                        rank=1,
                        published=True,
                    ),
                    Category(
                        name="events",
                        title="Events",
                        description=(
                            "Happenings, celebrations, and special occasions"
                        ),
                        rank=2,
                        published=True,
                    ),
                    Category(
                        name="music",
                        title="Music",
                        description=(
                            "Musical content, songs, instruments, "
                            "and audio experiences"
                        ),
                        rank=3,
                        published=True,
                    ),
                    Category(
                        name="places",
                        title="Places",
                        description=(
                            "Locations, landmarks, and geographical content"
                        ),
                        rank=4,
                        published=True,
                    ),
                    Category(
                        name="food",
                        title="Food",
                        description=(
                            "Culinary content, recipes, and "
                            "food-related information"
                        ),
                        rank=5,
                        published=True,
                    ),
                    Category(
                        name="people",
                        title="People",
                        description=(
                            "Individuals, personalities, and "
                            "human-related content"
                        ),
                        rank=6,
                        published=True,
                    ),
                    Category(
                        name="literature",
                        title="Literature",
                        description=(
                            "Books, poems, writings, and literary works"
                        ),
                        rank=7,
                        published=True,
                    ),
                    Category(
                        name="architecture",
                        title="Architecture",
                        description=(
                            "Buildings, structures, and architectural designs"
                        ),
                        rank=8,
                        published=True,
                    ),
                    Category(
                        name="skills",
                        title="Skills",
                        description=(
                            "Abilities, talents, and learning resources"
                        ),
                        rank=9,
                        published=True,
                    ),
                    Category(
                        name="images",
                        title="Images",
                        description=(
                            "Visual content, pictures, and graphic materials"
                        ),
                        rank=10,
                        published=True,
                    ),
                    Category(
                        name="culture",
                        title="Culture",
                        description=(
                            "Cultural traditions, customs, and heritage"
                        ),
                        rank=11,
                        published=True,
                    ),
                    Category(
                        name="flora_&_fauna",
                        title="Flora & Fauna",
                        description="Plants, animals, and natural life forms",
                        rank=12,
                        published=True,
                    ),
                    Category(
                        name="education",
                        title="Education",
                        description=(
                            "Learning materials, courses, "
                            "and educational content"
                        ),
                        rank=13,
                        published=True,
                    ),
                    Category(
                        name="vegetation",
                        title="Vegetation",
                        description=(
                            "Plant life, gardening, and botanical content"
                        ),
                        rank=14,
                        published=True,
                    ),
                    Category(
                        name="folk tales",
                        title="Folk Tales",
                        description="Stories passed orally across generations",
                        rank=15,
                        published=True,
                    ),
                    Category(
                        name="folk_songs",
                        title="Folk Songs",
                        description=(
                            "Documenting traditional music reflecting "
                            "the cultural heritage of the region."
                        ),
                        rank=16,
                        published=True,
                    ),
                    Category(
                        name="traditional_skills",
                        title="Traditional Skills",
                        description=(
                            "Gathering data on local artisanal and "
                            "craft practices (e.g., weaving, pottery)."
                        ),
                        rank=17,
                        published=True,
                    ),
                    Category(
                        name="local_cultural_history",
                        title="Local Cultural History",
                        description=(
                            "Collecting data on cultural events, rituals, "
                            "and customs that define the local communities."
                        ),
                        rank=18,
                        published=True,
                    ),
                    Category(
                        name="local_history",
                        title="Local History",
                        description=(
                            "Compiling historical events and figures "
                            "significant to your region."
                        ),
                        rank=19,
                        published=True,
                    ),
                    Category(
                        name="food_agriculture",
                        title="Food & Agriculture",
                        description=(
                            "Documenting traditional recipes and cooking "
                            "methods, along with their cultural "
                            "significance. Include recipes, tools, "
                            "practices."
                        ),
                        rank=20,
                        published=True,
                    ),
                    Category(
                        name="old_newspapers",
                        title="Newspapers Older Than 1980s",
                        description=(
                            "From libraries or archives, scanned "
                            "or physical copies."
                        ),
                        rank=21,
                        published=True,
                    ),
                ]
                for category in categories:
                    session.add(category)

            session.commit()
            if existing_roles <= 0:
                print("✅ Initial roles seeded successfully!")
            if existing_categories <= 0:
                print("✅ Initial categories seeded successfully!")
            return True
    except Exception as e:
        print(f"❌ Failed to seed initial data: {e}")
        return False


def main() -> None:
    """CLI entry point for PostgreSQL setup."""
    parser = argparse.ArgumentParser(
        description="PostgreSQL Database Setup with PostGIS Support"
    )
    parser.add_argument(
        "--create-db",
        action="store_true",
        help="Create database if it doesn't exist",
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test database connection",
    )
    parser.add_argument(
        "--check-postgis",
        action="store_true",
        help="Check PostGIS availability",
    )
    parser.add_argument(
        "--enable-postgis", action="store_true", help="Enable PostGIS extension"
    )
    parser.add_argument(
        "--enable-pgtrgm",
        action="store_true",
        help="Enable pg_trgm extension for fuzzy search",
    )
    parser.add_argument(
        "--migrate", action="store_true", help="Run database migrations"
    )
    parser.add_argument("--seed", action="store_true", help="Seed initial data")
    parser.add_argument(
        "--validate-postgis",
        action="store_true",
        help="Validate PostGIS functionality",
    )
    parser.add_argument(
        "--validate-schema",
        action="store_true",
        help="Validate Record table PostGIS schema",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all setup steps including PostGIS",
    )

    args = parser.parse_args()

    # If no specific flags, show current configuration
    if not any(
        [
            args.create_db,
            args.test_connection,
            args.check_postgis,
            args.enable_postgis,
            args.migrate,
            args.seed,
            args.validate_postgis,
            args.validate_schema,
            args.all,
        ]
    ):
        print("🔧 Current PostgreSQL Configuration:")
        print(f"   Host: {settings.DB_HOST}")
        print(f"   Port: {settings.DB_PORT}")
        print(f"   Database: {settings.DB_NAME}")
        print(f"   User: {settings.DB_USER}")
        print(f"   URL: {settings.DATABASE_URL}")
        print("\n🗺️  PostGIS Integration:")
        print(
            "   This setup script now includes PostGIS spatial database support"
        )
        print("   for geographic location data in the Record model.")
        print(
            "\nUse --help to see available options, or --all to run full setup."
        )
        return

    success = True

    if args.all or args.test_connection:
        print("🔍 Testing PostgreSQL server connection...")
        if not test_postgres_connection():
            success = False
            return

    if args.all or args.check_postgis:
        print("🗺️  Checking PostGIS availability...")
        if not check_postgis_availability():
            print("   Please install PostGIS before continuing.")
            success = False
            return

    if args.all or args.create_db:
        print("🏗️  Creating database...")
        if not create_database():
            success = False
            return

    if args.all or args.test_connection:
        print("🔍 Testing database connection...")
        if not test_database_connection():
            success = False
            return

    if args.all or args.enable_postgis:
        print("🗺️  Enabling PostGIS extension...")
        if not enable_postgis():
            success = False
            return

    if args.all or args.enable_pgtrgm:
        print("🔤 Enabling pg_trgm extension...")
        if not enable_pg_trgm():
            success = False
            return

    if args.all or args.migrate:
        print("🚀 Running database migrations...")
        if not run_migrations():
            success = False
            return

    if args.all or args.validate_postgis:
        print("🧪 Validating PostGIS functionality...")
        if not validate_postgis_functionality():
            success = False
            return

    if args.all or args.validate_schema:
        print("🔍 Validating Record table PostGIS schema...")
        if not validate_record_table_postgis():
            success = False
            return

    if args.all or args.seed:
        print("🌱 Seeding initial data...")
        if not seed_initial_data():
            success = False
            return

    if success:
        print("\n🎉 Database setup completed successfully!")
        print("   ✅ PostgreSQL database is ready")
        print("   ✅ PostGIS extension is enabled and functional")
        print("   ✅ Spatial data support is available for Record locations")
        print("   ✅ pg_trgm extension is enabled for fuzzy search")
        print(
            "\nYou can now start the FastAPI application "
            "with geographic features."
        )
    else:
        print("\n❌ Database setup failed. Please check the errors above.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Docker Database Initialization Script.

This script runs the complete database setup within the Docker environment:
1. Waits for PostgreSQL to be ready
2. Creates database if needed
3. Enables PostGIS extension
4. Runs database migrations
5. Seeds initial data
6. Validates PostGIS functionality

This should be run as a one-time initialization service in Docker.
"""

import logging
import sys
import time

from setup_postgresql import (
    check_postgis_availability,
    create_database,
    enable_pg_trgm,
    enable_postgis,
    run_migrations,
    seed_initial_data,
    test_database_connection,
    test_postgres_connection,
    validate_postgis_functionality,
    validate_record_table_postgis,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def wait_for_postgres(max_retries: int = 30, delay: int = 2) -> bool:
    """Wait for PostgreSQL to be ready."""
    logger.info("🔍 Waiting for PostgreSQL to be ready...")

    for attempt in range(max_retries):
        try:
            if test_postgres_connection():
                logger.info("✅ PostgreSQL is ready!")
                return True
        except Exception:
            logger.info(
                f"Attempt {attempt + 1}/{max_retries}: "
                f"PostgreSQL not ready yet..."
            )

        if attempt < max_retries - 1:
            time.sleep(delay)

    logger.error("❌ PostgreSQL failed to become ready within timeout")
    return False


def is_database_initialized() -> bool:
    """Check if the database is already initialized.

    Checks for core tables and data.
    """
    try:
        if not test_database_connection():
            return False

        logger.info("🚀 Running database migrations...")
        if not run_migrations():
            logger.error("❌ Failed to run migrations")
            return False

        from sqlmodel import Session, select

        from app.db.session import engine
        from app.models import Role

        with Session(engine) as session:
            # Check if core tables exist and have data
            # 1. Check if roles table exists and has data
            try:
                roles = session.exec(select(Role)).all()
                if len(roles) >= 3:  # Should have admin, user, reviewer roles
                    logger.info(
                        f"✅ Database already initialized "
                        f"(found {len(roles)} roles)"
                    )
                    return True
            except Exception:
                # Table doesn't exist or other error - not initialized
                return False

        return False
    except Exception as e:
        logger.warning(f"Could not check initialization status: {e}")
        return False


def initialize_database() -> bool:
    """Run complete database initialization."""
    logger.info("🚀 Starting database initialization...")

    # Step 0: Check if already initialized
    logger.info("🔍 Checking if database is already initialized...")
    if is_database_initialized():
        logger.info(
            "✅ Database is already initialized, skipping initialization steps"
        )
        return True

    # Step 1: Wait for PostgreSQL
    if not wait_for_postgres():
        logger.error("❌ PostgreSQL not available, aborting initialization")
        return False

    # Step 2: Check PostGIS availability
    logger.info("🗺️  Checking PostGIS availability...")
    if not check_postgis_availability():
        logger.error("❌ PostGIS not available in PostgreSQL image")
        return False

    # Step 3: Create database
    logger.info("🏗️  Creating database if needed...")
    if not create_database():
        logger.error("❌ Failed to create database")
        return False

    # Step 4: Test database connection
    logger.info("🔍 Testing database connection...")
    if not test_database_connection():
        logger.error("❌ Failed to connect to database")
        return False

    # Step 5: Enable PostGIS
    logger.info("🗺️  Enabling PostGIS extension...")
    if not enable_postgis():
        logger.error("❌ Failed to enable PostGIS")
        return False

    # Step 6: Enable pg_trgm for fuzzy text search
    logger.info("🔤 Enabling pg_trgm extension...")
    if not enable_pg_trgm():
        logger.error("❌ Failed to enable pg_trgm")
        return False

    # Step 7: Run migrations
    logger.info("🚀 Running database migrations...")
    if not run_migrations():
        logger.error("❌ Failed to run migrations")
        return False

    # Step 8: Validate PostGIS functionality
    logger.info("🧪 Validating PostGIS functionality...")
    if not validate_postgis_functionality():
        logger.warning("⚠️  PostGIS validation failed, but continuing...")

    # Step 9: Validate Record table PostGIS schema
    logger.info("🔍 Validating Record table PostGIS schema...")
    if not validate_record_table_postgis():
        logger.warning("⚠️  Record table validation failed, but continuing...")

    # Step 10: Seed initial data
    logger.info("🌱 Seeding initial data...")
    if not seed_initial_data():
        logger.warning("⚠️  Failed to seed initial data, but continuing...")

    logger.info("🎉 Database initialization completed successfully!")
    return True


def main() -> None:
    """Main initialization function."""
    try:
        success = initialize_database()
        if success:
            logger.info("✅ Database initialization completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Database initialization failed!")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error during initialization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

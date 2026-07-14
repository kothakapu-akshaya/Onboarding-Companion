#!/usr/bin/env python3
"""Database Management Script.

This script provides utilities for managing the Indic languages corpus database:
- Check database initialization status
- Force database reinitialization (if needed)
- Show database statistics
- Clean up database volumes
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from setup_postgresql import (
    test_database_connection,
    test_postgres_connection,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_database_status() -> bool:
    """Check the current status of the database."""
    print("🔍 Checking Database Status")
    print("=" * 50)

    # Check PostgreSQL connection
    if test_postgres_connection():
        print("✅ PostgreSQL server is accessible")
    else:
        print("❌ PostgreSQL server is not accessible")
        return False

    # Check database connection
    if test_database_connection():
        print("✅ Target database is accessible")
    else:
        print("❌ Target database is not accessible")
        return False

    # Check if database has data
    try:
        from sqlmodel import Session, select, text

        from app.db.session import engine
        from app.models import Category, Record, Role, User

        with Session(engine) as session:
            # Check roles
            roles_count = len(session.exec(select(Role)).all())
            print(f"🔑 Roles: {roles_count}")

            # Check users
            users_count = len(session.exec(select(User)).all())
            print(f"👥 Users: {users_count}")

            # Check categories
            categories_count = len(session.exec(select(Category)).all())
            print(f"📂 Categories: {categories_count}")

            # Check records
            records_count = len(session.exec(select(Record)).all())
            print(f"📝 Records: {records_count}")

            # Check PostGIS status
            try:
                result = session.execute(
                    text("SELECT PostGIS_Version()")
                ).first()
                if result:
                    print(f"🗺️  PostGIS Version: {result[0]}")
                else:
                    print("❌ PostGIS not available")
            except Exception:
                print("❌ PostGIS not enabled")

            # Determine initialization status
            if roles_count >= 3:
                print("\n✅ Database appears to be fully initialized")
                return True
            else:
                print(
                    "\n⚠️  Database appears to be partially initialized or empty"
                )
                return False

    except Exception as e:
        print(f"❌ Error checking database contents: {e}")
        return False


def show_database_info() -> bool:
    """Show detailed database information."""
    print("📊 Database Information")
    print("=" * 50)

    print("🔧 Configuration:")
    print(f"   Host: {settings.DB_HOST}")
    print(f"   Port: {settings.DB_PORT}")
    print(f"   Database: {settings.DB_NAME}")
    print(f"   User: {settings.DB_USER}")
    print(f"   URL: {settings.DATABASE_URL}")

    return check_database_status()


def force_reinitialize() -> bool:
    """Force database reinitialization.

    WARNING: This will destroy existing data.
    """
    print("⚠️  FORCE REINITIALIZATION")
    print("=" * 50)
    print("WARNING: This will destroy all existing data in the database!")

    confirm = input(
        "Are you sure you want to continue? Type 'YES' to confirm: "
    )
    if confirm != "YES":
        print("❌ Operation cancelled")
        return False

    try:
        # Run the full initialization process
        from init_db import initialize_database

        print("🚀 Starting forced reinitialization...")

        # Drop all tables first
        print("🗑️  Dropping all tables...")
        try:
            result = subprocess.run(
                ["alembic", "downgrade", "base"],
                capture_output=True,
                text=True,
                cwd=".",
            )
            if result.returncode == 0:
                print("✅ Tables dropped successfully")
            else:
                print(f"⚠️  Warning during table drop: {result.stderr}")
        except Exception as e:
            print(f"⚠️  Could not drop tables: {e}")

        # Run full initialization
        if initialize_database():
            print("✅ Database reinitialization completed successfully!")
            return True
        else:
            print("❌ Database reinitialization failed!")
            return False

    except Exception as e:
        print(f"❌ Error during reinitialization: {e}")
        return False


def clean_docker_volumes() -> bool:
    """Clean up Docker volumes (WARNING: This will destroy all data)."""
    print("🧹 CLEAN DOCKER VOLUMES")
    print("=" * 50)
    print("WARNING: This will destroy all Docker volumes and data!")

    confirm = input(
        "Are you sure you want to continue? Type 'YES' to confirm: "
    )
    if confirm != "YES":
        print("❌ Operation cancelled")
        return False

    try:
        print("🛑 Stopping Docker containers...")
        subprocess.run(["docker-compose", "down"], cwd=".")

        print("🗑️  Removing Docker volumes...")
        subprocess.run(
            [
                "docker",
                "volume",
                "rm",
                "corpus-te_postgres_data",
                "corpus-te_redis_data",
                "corpus-te_celery_beat_data",
            ],
            capture_output=True,
        )

        print("✅ Docker volumes cleaned. You can now restart with fresh data.")
        print("   Run: docker-compose up -d")
        return True

    except Exception as e:
        print(f"❌ Error cleaning volumes: {e}")
        return False


def seed_sample_data() -> bool:
    """Seed sample data for testing."""
    print("🌱 Seeding Sample Data")
    print("=" * 50)

    try:
        # Check if database is initialized
        if not check_database_status():
            print(
                "❌ Database is not properly initialized. "
                "Please run database initialization first."
            )
            return False

        # Run the test data creation script
        script_path = Path(__file__).parent / "create_test_users.py"
        if script_path.exists():
            print("👥 Creating test users...")
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                cwd=".",
            )
            if result.returncode == 0:
                print("✅ Test users created successfully")
                print(result.stdout)
            else:
                print(f"❌ Failed to create test users: {result.stderr}")
                return False
        else:
            print("⚠️  Test user creation script not found")

        # Run the test data creation script if available
        test_data_script = (
            Path(__file__).parent / "tests" / "create_test_data.py"
        )
        if test_data_script.exists():
            print("📝 Creating test data...")
            result = subprocess.run(
                [sys.executable, str(test_data_script), "create"],
                capture_output=True,
                text=True,
                cwd=".",
            )
            if result.returncode == 0:
                print("✅ Test data created successfully")
                print(result.stdout)
            else:
                print(f"⚠️  Test data creation had issues: {result.stderr}")

        return True

    except Exception as e:
        print(f"❌ Error seeding sample data: {e}")
        return False


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Database Management Utilities"
    )
    parser.add_argument(
        "action",
        choices=["status", "info", "reinit", "clean", "seed"],
        help="Action to perform",
    )

    args: Any = parser.parse_args()

    print("🗃️  Indic languages Database Management")
    print("=" * 60)

    if args.action == "status":
        success = check_database_status()
    elif args.action == "info":
        success = show_database_info()
    elif args.action == "reinit":
        success = force_reinitialize()
    elif args.action == "clean":
        success = clean_docker_volumes()
    elif args.action == "seed":
        success = seed_sample_data()
    else:
        print("❌ Unknown action")
        success = False

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Database session configuration."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# Create engine with proper configuration
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_timeout=30,
    echo=False,  # Set to True for SQL debugging
)


def create_db_and_tables():
    """Create database tables if they don't exist."""
    # First, ensure enum types exist before creating tables
    # Use a separate connection to avoid transaction issues
    with engine.connect() as conn:
        # Create changetype enum if it doesn't exist
        # (PostgreSQL anonymous block)
        conn.execute(
            text(
                """
            DO $$
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'changetype'
                ) THEN 
                    CREATE TYPE changetype AS ENUM (
                        'created', 'updated', 'admin_override', 'system_update'
                    ); 
                END IF; 
            END 
            $$;
        """
            )
        )

        # Create changesource enum if it doesn't exist
        conn.execute(
            text(
                """
            DO $$
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'changesource'
                ) THEN 
                    CREATE TYPE changesource AS ENUM (
                        'user_edit', 'admin_action', 'system_process', 
                        'ai_processing', 'migration', 'bulk_update'
                    ); 
                END IF; 
            END 
            $$;
        """
            )
        )
        conn.commit()

    # Import all models to ensure they're registered and create tables
    SQLModel.metadata.create_all(engine, checkfirst=True)

    from app.services.language_service import LanguageService

    with Session(engine) as session:
        LanguageService.ensure_default_languages(session)


def get_session():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session


def get_db():
    """Alias for get_session for backward compatibility."""
    with Session(engine) as session:
        yield session


# Type annotation for session dependency
SessionDep = Annotated[Session, Depends(get_session)]

"""Database session configuration."""

from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.models.onboarding import OnboardingEvidence, OnboardingProgress

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
    """Create only the tables owned by the onboarding service."""
    SQLModel.metadata.create_all(
        engine,
        tables=[OnboardingProgress.__table__, OnboardingEvidence.__table__],
        checkfirst=True,
    )


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

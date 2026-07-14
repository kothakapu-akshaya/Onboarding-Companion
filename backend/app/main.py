"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from posthog import Posthog

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.validation_exceptions import register_exception_handlers
from app.db.session import create_db_and_tables

# Setup logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

posthog = Posthog(
    project_api_key=settings.POSTHOG_API_KEY,
    host=settings.POSTHOG_API_HOST,
    enable_exception_autocapture=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting up the application...")

    # Create database tables
    create_db_and_tables()
    logger.info("Database tables created/verified")

    yield

    # Shutdown
    logger.info("Shutting down the application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Indic languages corpus collections backend API",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register centralized exception handlers
register_exception_handlers(app)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    posthog.capture_exception(exc)
    logger.error(
        f"Unexpected error on {request.url}: {str(exc)}", exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_type": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "timestamp": "utcnow().isoformat()",
        },
    )


@app.get("/")
async def root():
    """Root endpoint with welcome message."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Include API routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Add a note that python-dotenv should be added to requirements.txt
# if .env files are to be used by pydantic-settings.

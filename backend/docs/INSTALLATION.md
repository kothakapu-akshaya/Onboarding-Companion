# Installation Instructions

## Prerequisites

- **For Windows**: Download [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **For Linux**: Download [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/linux/)
- **Python**: Version 3.13 or higher
- **uv**: Package manager

## Quick Start (Docker)

```bash
# Clone the repository
git clone https://code.swecha.org/corpus/corpus-server-app.git
cd corpus-server-app

# Start all services
docker compose up

# Rebuild after code changes
docker compose up --build
```

### Docker Compose Profiles

The project uses Docker Compose profiles for selective service startup:

```bash
# Core services only (PostgreSQL, Redis, app, celery workers)
docker compose up

# Include development tools (pgAdmin, MinIO)
docker compose --profile development up

# Include local-only services
docker compose --profile local up

# Combine profiles
docker compose --profile development --profile local up
```

Available profiles:
- **default** (no profile): Core services — app, PostgreSQL, Redis, Celery workers
- **development**: pgAdmin, MinIO
- **local**: Same as development (alias)

## Manual Setup (uv)

### Clone and Setup

```bash
git clone https://code.swecha.org/corpus/corpus-server-app.git
cd corpus-server-app

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies (production + development)
uv sync

# Or install only production dependencies
uv sync --no-group dev
```

### Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### Database Setup

Install PostgreSQL and Redis locally, or use Docker for infrastructure services:

```bash
# Start only infrastructure services via Docker
docker compose up postgres redis -d

# Run database migrations
uv run alembic upgrade head
```

See [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md) for detailed PostgreSQL installation and setup instructions.

### Start Development Server

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Development Commands

```bash
uv run pytest              # Run tests
uv run ruff check .        # Lint Python code
uv run ruff format .       # Format Python code
uv run alembic upgrade head  # Run database migrations
uv run python -m scripts.seed_database  # Seed database
```

## Environment Configuration

All environment variables are documented in `.env.example`. Key variables:

### Database
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `DATABASE_URL`: Full PostgreSQL connection string

### Application
- `PROJECT_NAME`: Application name
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Authentication
- `APP_SECRET_KEY`: JWT secret key (change in production)
- `ALGORITHM`: JWT algorithm (default: HS256)

### CORS
- `BACKEND_CORS_ORIGINS`: Comma-separated list of allowed origins

### Object Storage (Optional)
- `HZ_OBJ_ACCESS_KEY`, `HZ_OBJ_SECRET_KEY`, `HZ_OBJ_ENDPOINT`
- `HZ_OBJ_BUCKET_NAME`, `HZ_OBJ_USE_SSL`

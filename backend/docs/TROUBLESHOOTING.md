# Troubleshooting Guide

## Package Manager (uv)

### uv command not found
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Restart shell or source profile
source ~/.bashrc  # or ~/.zshrc
```

### uv sync fails with dependency conflicts
```bash
# Try resolving with a fresh lock
uv lock
uv sync
```

### Virtual environment issues
```bash
# Remove and recreate
rm -rf .venv
uv venv
uv sync
```

## Docker

### Docker not running
```bash
# Start Docker
sudo systemctl start docker  # Linux
# Docker Desktop on Windows/macOS

# Check status
docker info
```

### Port already in use
```bash
# Find process on port
sudo lsof -i :8000     # Linux
sudo lsof -i :5432     # Database port
sudo lsof -i :6379     # Redis port

# Kill process
kill -9 <PID>
```

### Service fails to start in Docker
```bash
# Check service logs
docker compose logs app
docker compose logs postgres
docker compose logs redis

# Rebuild and restart
docker compose down
docker compose up --build -d
```

### Profile not found
```bash
# List available profiles
docker compose config --profiles

# Use a profile that exists (development, local)
docker compose --profile development up
```

### Database container not healthy
```bash
# Check health status
docker compose ps

# Check logs
docker compose logs postgres

# Restart with fresh data
docker compose down -v
docker compose up -d
```

## Database

### Connection refused
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql  # Local install
docker compose ps postgres         # Docker

# Verify env variables
grep -E "DB_HOST|DB_PORT|DB_NAME|DB_USER|DB_PASSWORD" .env
```

### Migration fails
```bash
# Check current migration state
uv run alembic current

# View migration history
uv run alembic history

# Rollback one step
uv run alembic downgrade -1

# Rollback to base
uv run alembic downgrade base

# Re-run migrations
uv run alembic upgrade head
```

### Lost connection to MySQL during query
Wait timeout or connection drop — retry. If persistent:
```bash
# Check PostgreSQL max_connections
docker compose exec postgres psql -U postgres -c "SHOW max_connections;"

# Check active connections
docker compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

### Authentication failed
```bash
# Verify password in .env matches database
grep DB_PASSWORD .env

# Reset password
docker compose exec postgres psql -U postgres -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
```

### Relation does not exist
```bash
# Run migrations
uv run alembic upgrade head
```

### postgres / pg_isready error
```bash
# Verify PostgreSQL is running and accepting connections
docker compose ps
docker compose logs postgres | tail -20
```

## PostGIS

### PostGIS extension not available
```bash
# Verify image includes PostGIS
docker compose exec postgres psql -U postgres -d ${DB_NAME} -c "SELECT PostGIS_Version();"

# Enable extension
docker compose exec postgres psql -U postgres -d ${DB_NAME} -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

### Geography/Geometry type errors
Ensure your model fields use the correct SQLAlchemy/GeoAlchemy2 types:
- Use `Geometry` for 2D spatial data
- Use `Geography` for geodetic (lat/lon) data
- Check that PostGIS extension is enabled on the database

## Environment Configuration

### Application fails to start — missing env vars
```bash
# Copy example env and edit
cp .env.example .env

# Validate required variables
grep -E "^[A-Z_]+=" .env | head -20
```

### CORS errors in browser
```bash
# Update allowed origins in .env
BACKEND_CORS_ORIGINS="http://localhost:3000,http://localhost:5173,https://your-domain.com"
```

### Wrong database name or credentials
```bash
# Verify .env values match your running database
grep -E "DB_NAME|DB_USER|DB_PASSWORD|DB_HOST|DB_PORT" .env
```

### Log level too verbose or too quiet
```bash
# Set in .env
LOG_LEVEL=INFO    # Options: DEBUG, INFO, WARNING, ERROR
```

## Celery

### Celery worker not connecting to broker
```bash
# Verify Redis is running
docker compose ps redis
docker compose logs redis | tail -10

# Check broker URL in environment
grep CELERY_BROKER_URL .env
```

### Tasks not being processed
```bash
# Check worker logs
docker compose logs celery-worker | tail -20

# Verify queues match
# Worker queues are configured in docker-compose.yml command
# Default: default,file_processing,notifications,data_analysis
```

### Flower monitoring not accessible
```bash
# Verify Flower is running
docker compose ps flower

# Check port binding
docker compose logs flower | tail -10
# Default: http://localhost:5555
```

### Celery beat not scheduling tasks
```bash
# Check beat logs
docker compose logs celery-beat | tail -20

# Verify scheduler is set (redbeat)
# Command should include: --scheduler redbeat.RedBeatScheduler
```

## Authentication

### JWT token expired
```bash
# Increase token lifetime in .env
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### Invalid token / signature
```bash
# Ensure APP_SECRET_KEY is consistent across restarts
# Change only if you want to invalidate all existing tokens
grep APP_SECRET_KEY .env
```

### OTP not being sent
```bash
# Verify OTP provider configuration
# Check environment variables related to SMS/OTP provider

# Check logs
docker compose logs app | grep -i otp

# In development, check terminal output for OTP code
```

## File Upload

### File upload fails
```bash
# Check file size limit
grep MAX_FILE_SIZE .env

# Check available disk space
df -h /tmp

# Verify MinIO is running
docker compose ps minio
```

### Object storage (MinIO/S3) connection fails
```bash
# Verify MinIO is running and accessible
curl http://localhost:9000/minio/health/live

# Check credentials in .env
grep -E "HZ_OBJ_ACCESS_KEY|HZ_OBJ_SECRET_KEY|HZ_OBJ_ENDPOINT" .env

# For production S3, verify SSL setting
grep HZ_OBJ_USE_SSL .env
# Set to "true" for AWS S3, "false" for local MinIO
```

## Network

### Services can't reach each other in Docker
```bash
# Verify all services are on the same network
docker compose ps

# Check network config
docker network inspect corpus-te-network

# For local development, use localhost or 127.0.0.1
# For Docker, use service names (postgres, redis, etc.)
```

### Can't access application from browser
```bash
# Check if app is running
docker compose ps app
curl http://localhost:8000/health

# Check port binding — port 8000 should be mapped
docker compose port app 8000

# Firewall may be blocking — check with curl or wget
```

## Performance

### Application is slow
```bash
# Check resource usage
docker stats --no-stream

# Adjust Gunicorn workers (in docker-compose.yml)
# -w 4 for production, -w 2 for development

# Check database query performance
docker compose exec postgres psql -U postgres -d ${DB_NAME} -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

### Redis memory full
```bash
# Check Redis memory usage
docker compose exec redis redis-cli INFO memory

# Set memory limit in docker-compose.yml
# command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Disk space full
```bash
# Check Docker disk usage
docker system df

# Clean up unused images, containers, volumes
docker system prune -f

# Remove old database backups
rm -rf backups/*.sql.gz
```

## General

### Pre-commit hooks failing
```bash
# Re-install hooks
uv run pre-commit install

# Run against all files
uv run pre-commit run --all-files

# Skip hooks for a commit (emergency only)
git commit --no-verify -m "message"
```

### ImportError / ModuleNotFoundError
```bash
# Ensure virtual environment is activated and deps installed
source .venv/bin/activate
uv sync
```

### Port conflicts after reboot
```bash
# Check what's using the port
sudo lsof -i :8000

# Common conflicting ports: 8000 (app), 5432 (postgres), 6379 (redis)
# Change port mapping in docker-compose.yml if needed
```

### Git merge conflicts
```bash
# Abort merge and restart
git merge --abort
git pull origin develop
git merge your-branch

# Use a visual merge tool
git mergetool
```
</parameter>

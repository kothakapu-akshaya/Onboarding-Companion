# PostgreSQL Setup Guide

This guide provides step-by-step instructions for setting up PostgreSQL database for the Indic languages Corpus Collections application.

## Prerequisites

- Python 3.8+ with uv package manager
- Administrative access to install PostgreSQL
- Basic knowledge of command line operations

## Step 1: Install PostgreSQL

### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install PostgreSQL and additional utilities
sudo apt install postgresql postgresql-contrib postgresql-client

# Start and enable PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify installation
sudo systemctl status postgresql
```

### macOS (using Homebrew)

```bash
# Install PostgreSQL
brew install postgresql

# Start PostgreSQL service
brew services start postgresql

# Verify installation
brew services list | grep postgresql
```

### Windows

1. Download PostgreSQL installer from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run the installer and follow the setup wizard
3. Remember the password you set for the `postgres` user
4. Add PostgreSQL bin directory to your PATH

### CentOS/RHEL/Fedora

```bash
# Install PostgreSQL
sudo dnf install postgresql postgresql-server postgresql-contrib

# Initialize database
sudo postgresql-setup --initdb

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## Step 2: Configure PostgreSQL User and Database

### Method 1: Using psql (Recommended)

```bash
# Switch to postgres user and open psql
sudo -u postgres psql

# In PostgreSQL shell, create user and database:
CREATE USER corpus_user WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE corpus_te OWNER corpus_user;
GRANT ALL PRIVILEGES ON DATABASE corpus_te TO corpus_user;

# Grant schema permissions
\c corpus_te
GRANT ALL ON SCHEMA public TO corpus_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO corpus_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO corpus_user;

# Exit psql
\q
```

### Method 2: Using createuser and createdb commands

```bash
# Create user
sudo -u postgres createuser --interactive --pwprompt corpus_user

# Create database
sudo -u postgres createdb --owner=corpus_user corpus_te
```

## Step 3: Verify Database Connection

Test the connection to ensure everything is working:

```bash
# Test connection with the new user
psql -h localhost -U corpus_user -d corpus_te

# You should see a prompt like: corpus_te=>
# Type \q to exit
```

## Step 4: Configure Application Environment

### Create/Update .env file

```bash
# Copy example environment file (if it exists)
cp .env.example .env

# Or create new .env file
touch .env
```

### Add PostgreSQL configuration to .env:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=corpus_te
DB_USER=corpus_user
DB_PASSWORD=your_secure_password_here

# Constructed PostgreSQL URL
DATABASE_URL="postgresql://corpus_user:your_secure_password_here@localhost:5432/corpus_te"

# Application Settings
PROJECT_NAME="Indic languages Corpus Collections API"
LOG_LEVEL="WARNING"

# JWT Configuration (generate a secure secret key)
APP_SECRET_KEY="your-very-secure-secret-key-here-change-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Origins (adjust for your frontend)
BACKEND_CORS_ORIGINS="http://localhost:3000,http://localhost:8080"

# File Upload Settings
MAX_FILE_SIZE=104857600

# Object Storage (Optional - for MinIO/S3)
# HZ_OBJ_ACCESS_KEY="your_access_key"
# HZ_OBJ_SECRET_KEY="your_secret_key"
# HZ_OBJ_ENDPOINT="your_endpoint"
# HZ_OBJ_BUCKET_NAME="corpus-data"
```

### Generate a secure secret key:

```bash
# Method 1: Using Python
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Method 2: Using openssl
openssl rand -base64 64
```

## Step 5: Database Schema Setup with Alembic

### Initialize Alembic (if not already done)

```bash
# Check if alembic is already initialized
ls alembic/

# If alembic directory exists, skip this step
# If not, initialize:
alembic init alembic
```

### Configure Alembic for PostgreSQL

The project is already configured for PostgreSQL. Verify `alembic.ini` contains:

```ini
sqlalchemy.url = postgresql://corpus_user:password@localhost:5432/corpus_te
```

### Run Database Migrations

```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Apply all migrations to create tables and populate data
alembic upgrade head
```

This will create the following tables:

- `role` - System roles (admin, user, reviewer)
- `user` - User accounts
- `user_roles` - Many-to-many relationship between users and roles
- `category` - Content categories
- `record` - Media submissions

### Verify Database Schema

```bash
# Connect to database
psql -h localhost -U corpus_user -d corpus_te

# List all tables
\dt

# View table structure
\d user
\d role
\d user_roles
\d category
\d record

# Check if default roles are populated
SELECT * FROM role;

# Exit psql
\q
```

You should see output similar to:

```
 id |   name   |              description
----+----------+---------------------------------------
  1 | admin    | Administrator role with full access
  2 | user     | Standard user role with basic access
  3 | reviewer | Reviewer role with record review permissions
```

## Step 8: Database Management Commands

### Useful PostgreSQL Commands

```bash
# Connect to database
psql -h localhost -U corpus_user -d corpus_te

# Basic queries
SELECT COUNT(*) FROM "user";
SELECT COUNT(*) FROM role;
SELECT u.name, r.name as role_name FROM "user" u
  JOIN user_roles ur ON u.id = ur.user_id
  JOIN role r ON ur.role_id = r.id;

# Backup database
pg_dump -h localhost -U corpus_user corpus_te > backup.sql

# Restore database
psql -h localhost -U corpus_user corpus_te < backup.sql
```

### Alembic Migration Commands

```bash
# Create new migration
alembic revision --autogenerate -m "description of changes"

# Apply specific migration
alembic upgrade +1

# Rollback one migration
alembic downgrade -1

# Reset to base (removes all tables)
alembic downgrade base

# View SQL for upgrade
alembic upgrade head --sql

# Check migration status
alembic current
alembic history --verbose
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Connection Refused

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL if not running
sudo systemctl start postgresql

# Check if PostgreSQL is listening on port 5432
sudo netstat -plntu | grep :5432
```

#### 2. Authentication Failed

```bash
# Reset user password
sudo -u postgres psql
ALTER USER corpus_user WITH PASSWORD 'new_password';

# Update .env file with new password
```

#### 3. Permission Denied

```bash
# Grant all permissions to user
sudo -u postgres psql
GRANT ALL PRIVILEGES ON DATABASE corpus_te TO corpus_user;
\c corpus_te
GRANT ALL ON SCHEMA public TO corpus_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO corpus_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO corpus_user;
```

#### 4. Migration Errors

```bash
# Check migration status
alembic current

# Force to specific revision
alembic stamp head

# Reset and rerun migrations
alembic downgrade base
alembic upgrade head
```

#### 5. Database Already Exists Error

```bash
# Drop and recreate database
sudo -u postgres psql
DROP DATABASE corpus_te;
CREATE DATABASE corpus_te OWNER corpus_user;
```

### Log Files

Check application logs for detailed error information:

```bash
# View application logs
tail -f logs/app.log

# View PostgreSQL logs (Ubuntu/Debian)
sudo tail -f /var/log/postgresql/postgresql-*.log

# View PostgreSQL logs (macOS with Homebrew)
tail -f /usr/local/var/log/postgres.log
```

## Production Considerations

### Security

1. **Change default passwords** in production
2. **Use environment variables** for sensitive data
3. **Configure PostgreSQL authentication** (pg_hba.conf)
4. **Enable SSL/TLS** for database connections
5. **Use strong JWT secret keys**

### Performance

1. **Configure PostgreSQL memory settings** (shared_buffers, work_mem)
2. **Set up connection pooling** (pgbouncer)
3. **Create database indexes** for frequently queried columns
4. **Monitor query performance**

### Backup

1. **Set up automated backups** using pg_dump or pg_basebackup
2. **Test backup restoration** regularly
3. **Store backups securely** off-site

### Monitoring

1. **Monitor database connections**
2. **Track query performance**
3. **Set up alerts** for critical issues
4. **Monitor disk space** usage

## Next Steps

1. **Create your first user** through the API
2. **Set up authentication** and test protected endpoints
3. **Configure object storage** if using file uploads
4. **Set up monitoring and logging** for production
5. **Create automated backup scripts**
6. **Configure reverse proxy** (nginx/apache) for production deployment

For more information about the API endpoints and usage, see the main [README.md](https://code.swecha.org/corpus/corpus-server-app/-/blob/main/README.md) file.

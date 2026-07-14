# Corpus Collections API

A FastAPI-based backend service for managing corpus collections, supporting text, audio, video, image, and document submissions with PostgreSQL database and JWT authentication.

## Features

- **Multi-media Support**: Handle text, audio, video, image, and document submissions
- **User Management**: Many-to-many role-based user system (admin/user/reviewer)
- **Dual Authentication**: JWT-based with both OTP and password authentication methods
- **OTP Authentication**: SMS-based OTP verification with separate signup and login flows
- **Category Management**: Organize submissions by categories
- **Record Review System**: Support for content review workflows
- **Geolocation & PostGIS**: Advanced geographic data handling with spatial queries and indexing
- **PostgreSQL Database**: Robust database with proper foreign key constraints
- **File Storage**: Support for local and MinIO/S3 storage
- **RESTful API**: Full CRUD operations with OpenAPI documentation
- **Docker Compose Profiles**: Selective service startup (development, local) for flexible development workflows

## Project Structure

```
corpus-te/
├── app/
│   ├── main.py              # FastAPI application
│   ├── core/
│   │   ├── config.py        # Settings and configuration
│   │   ├── auth.py          # JWT authentication utilities
│   │   ├── exceptions.py    # Custom exceptions
│   │   ├── logging_config.py # Logging setup
│   │   └── rbac_fastapi.py  # Role-based access control utilities
│   ├── db/
│   │   └── session.py       # Database session
│   ├── models/
│   │   ├── __init__.py      # Database models
│   │   ├── associations.py  # Many-to-many association tables
│   │   ├── user.py          # User model
│   │   ├── role.py          # Role model
│   │   ├── category.py      # Category model
│   │   ├── record.py        # Record model
│   │   └── otp.py           # OTP model for authentication
│   ├── schemas/
│   │   ├── __init__.py      # Pydantic schemas
│   │   ├── geo_schemas.py   # Geographic coordinate schemas
│   │   └── otp.py           # OTP request/response schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py          # Legacy auth endpoints
│   │   └── v1/
│   │       ├── api.py       # API router
│   │       ├── __init__.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py      # Authentication endpoints (with OTP)
│   │           ├── users.py     # User management endpoints
│   │           ├── roles.py     # Role management endpoints
│   │           ├── categories.py # Category endpoints
│   │           ├── records.py   # Record endpoints
│   │           └── system_rbac.py # RBAC system endpoints
│   ├── services/            # Business logic services
│   │   └── otp_service.py   # OTP authentication service
│   └── utils/               # Utility modules
│       ├── __init__.py
│       ├── cleanup_storage.py      # Storage cleanup utilities
│       ├── hetzner_storage.py      # Hetzner object storage integration
│       ├── postgis_utils.py        # PostGIS geographic utilities
│       └── record_file_generator.py # Record file generation utilities
├── alembic/                 # Database migrations
│   ├── versions/            # Migration files
│   ├── alembic.ini          # Alembic configuration
│   └── env.py              # Migration environment
├── docs/                    # Documentation and guides
│   ├── INSTALLATION.md                     # Installation guide (Docker, manual, profiles)
│   ├── TESTS.md                            # Testing guide with pytest patterns
│   ├── TROUBLESHOOTING.md                  # Comprehensive troubleshooting guide
│   ├── HETZNER_DEPLOYMENT_GUIDE.md         # Production deployment guide
│   ├── CONTRIBUTING.md                     # Contribution guidelines
│   ├── AUTH.md                             # Complete authentication & security guide
│   ├── HETZNER_STORAGE_GUIDE.md            # Hetzner storage setup guide
│   ├── POSTGRESQL_SETUP.md                 # PostgreSQL setup guide
│   ├── RBAC_GUIDE.md                       # Role-based access control guide
│   ├── POSTGIS_INTEGRATION_SUMMARY.md      # PostGIS integration summary
│   ├── Plan.md                             # Project development plan
│   ├── OTP_TESTING_RESULTS.md              # OTP testing results
│   ├── RECORD_FILE_GENERATOR_GUIDE.md      # Record file generator guide
│   ├── demo_rbac_optimization.py           # RBAC demo script
│   ├── example_hetzner_storage.py          # Hetzner storage examples
│   ├── example_record_file_generator.py    # Record generator examples
│   ├── generate_record_files.py            # File generation script
│   └── otp_demo.py                         # OTP demo script
├── tests/                   # Test files
│   ├── create_test_data.py              # Test data creation script
│   ├── test_hetzner_storage.py          # Hetzner storage tests
│   ├── test_otp_api.py                  # OTP API tests
│   ├── test_postgis_api.py              # PostGIS API tests
│   ├── test_postgis_integration.py      # PostGIS integration tests
│   ├── test_updated_api_endpoints.py    # Updated API endpoint tests
│   └── verify_test_data.py              # Test data verification
├── scripts/                 # Development and utility scripts
│   ├── seed_database.py    # Database seeding script
│   └── daily_maintenance.py # Maintenance tasks
├── .env.example            # Environment variable template
├── docker-compose.yml      # Docker Compose with profiles
├── Dockerfile              # Application Dockerfile
├── pyproject.toml          # Project dependencies
├── uv.lock                 # UV dependency lock file
├── LICENSE                 # License file
└── README.md              # This file
```

## Key Features

### 🔐 OTP Authentication System

Complete SMS-based One-Time Password authentication system with separate flows for user signup and login:

#### **Signup Flow (New Users)**
- **Account Creation**: OTP-verified user registration without pre-registration
- **User Onboarding**: Collects name, email, password, and consent during signup
- **Role Assignment**: Automatic role assignment with RBAC integration

#### **Login Flow (Existing Users)**
- **Passwordless Login**: Secure OTP-based authentication for existing users
- **Phone Verification**: SMS delivery with international phone number validation

#### **Security Features**
- **SMS Integration**: Real SMS delivery via Ozonetel API with fallback support
- **HMAC Encryption**: HMAC-SHA256 OTP hashing with phone number salts
- **Rate Limiting**: Built-in protection against spam and abuse on both flows
- **Attempt Tracking**: Progressive security with automatic OTP invalidation
- **JWT Integration**: Seamless token generation after successful verification

📖 **[Complete Authentication Guide](docs/AUTH.md)**

### 🌍 PostGIS Geographic Integration

Advanced spatial data handling with PostGIS for location-based features:

- **Spatial Queries**: Efficient geographic data operations and indexing
- **Location Services**: Precise coordinate handling and validation
- **Performance Optimization**: Specialized indexes for geographic queries
- **Data Integrity**: Robust validation for coordinate formats and ranges

📖 **[PostGIS Integration Guide](docs/POSTGIS_INTEGRATION.md)**

### 👥 Role-Based Access Control (RBAC)

Comprehensive user management system with flexible permissions:

- **Multi-Role Support**: Admin, User, and Reviewer roles with granular permissions
- **Performance Optimized**: Efficient user-role queries and caching strategies
- **Scalable Architecture**: Designed for large-scale user management

📖 **[RBAC Performance Optimization Guide](docs/RBAC_PERFORMANCE_OPTIMIZATION.md)**

## API Endpoints

### Core Endpoints

- `GET /`: Welcome message
- `GET /health`: Health check
- `GET /docs`: Swagger UI API documentation
- `GET /redoc`: ReDoc API documentation

### Authentication (`/api/v1/auth/`)

#### **OTP Authentication (Recommended)**
**Login Flow (Existing Users):**
- `POST /api/v1/auth/login/send-otp`: Send OTP for login
- `POST /api/v1/auth/login/verify-otp`: Verify OTP and get JWT token
- `POST /api/v1/auth/login/resend-otp`: Resend OTP for login

**Signup Flow (New Users):**
- `POST /api/v1/auth/signup/send-otp`: Send OTP for account creation
- `POST /api/v1/auth/signup/verify-otp`: Verify OTP and create account
- `POST /api/v1/auth/signup/resend-otp`: Resend OTP for signup

#### **Password Authentication (Legacy)**
- `POST /api/v1/auth/login`: Login with phone/password
- `POST /api/v1/auth/change-password`: Change current password
- `POST /api/v1/auth/reset-password`: Admin password reset
- `POST /api/v1/auth/forgot-password/init`: Initiate password reset
- `POST /api/v1/auth/forgot-password/confirm`: Confirm password reset

#### **Common Authentication**
- `GET /api/v1/auth/me`: Get current user information
- `POST /api/v1/auth/refresh`: Refresh access token

### User Management (`/api/v1/users/`)

- `GET /api/v1/users/`: List all users (with pagination)
- `POST /api/v1/users/`: Create a new user
- `GET /api/v1/users/{user_id}`: Get user by ID
- `PUT /api/v1/users/{user_id}`: Update user
- `GET /api/v1/users/{user_id}/with-roles`: Get user with roles populated
- `GET /api/v1/users/phone/{phone}`: Get user by phone number

### User Role Management (`/api/v1/users/{user_id}/roles/`)

- `GET /api/v1/users/{user_id}/roles`: Get user's roles
- `POST /api/v1/users/{user_id}/roles`: Assign roles to user (replace all)
- `PUT /api/v1/users/{user_id}/roles/add`: Add a role to user
- `DELETE /api/v1/users/{user_id}/roles/{role_id}`: Remove role from user

### Role Management (`/api/v1/roles/`)

- `GET /api/v1/roles/`: List all roles
- `POST /api/v1/roles/`: Create a new role
- `GET /api/v1/roles/{role_id}`: Get role by ID

### Category Management (`/api/v1/categories/`)

- `GET /api/v1/categories/`: List all categories
- `POST /api/v1/categories/`: Create a new category
- `GET /api/v1/categories/{category_id}`: Get category by ID
- `DELETE /api/v1/categories/{category_id}`: Delete category

### Record Management (`/api/v1/records/`)

- `GET /api/v1/records/`: List all records
- `POST /api/v1/records/`: Create a new record
- `GET /api/v1/records/{record_id}`: Get record by ID

## Installation

See [INSTALLATION.md](docs/INSTALLATION.md) for:
- **Quick start** with Docker Compose
- **Docker Compose profiles** for selective service startup (development, local)
- **Manual setup** with uv
- **Environment configuration** reference

## Testing

See [TESTS.md](docs/TESTS.md) for the comprehensive testing guide covering test architecture, patterns, fixtures, and best practices.

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/unit/services/test_otp_service.py

# Run with coverage
uv run pytest tests/ --cov=app --cov-report=term-missing
```

### Test Structure

```
tests/
├── unit/                      # Unit tests
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/    # API endpoint tests
│   ├── core/                 # Core module tests
│   ├── db/                   # Database tests
│   ├── schemas/              # Schema validation tests
│   ├── services/             # Service layer tests
│   ├── tasks/                # Celery task tests
│   └── utils/                # Utility function tests
├── integration/              # Integration tests (if any)
└── app/                      # App-level tests (if any)
```

### Key Test Files

- `tests/unit/services/test_otp_service.py` - OTP authentication service tests
- `tests/unit/api/v1/endpoints/test_auth_v1.py` - Authentication endpoint tests
- `tests/unit/schemas/test_auth_validation.py` - Auth schema validation tests
- `tests/unit/tasks/test_reports.py` - Report generation task tests
- `tests/unit/core/test_rbac_fastapi.py` - RBAC functionality tests

### Test Coverage

Current test coverage is **73%**. To check coverage:

```bash
uv run pytest tests/ --cov=app --cov-report=term-missing
```

### Notes

- Tests use pytest with pytest-asyncio for async tests
- Some tests are skipped due to SQLAlchemy 2.0 incompatibilities
- Test files with import errors are excluded via pytest.ini

## Database Seeding

The project includes a database seeding script for local development. It creates a small deterministic dataset including:

- 1 user
- 4 sample records
- category links using existing seeded categories
- points events
- basic record history/version data

**Seeded login details**

- Phone: `+919900000001`
- Password: `SeedUser@123`

### Usage

Environment variables are loaded by `uv` natively via `--env-file`. Run all local scripts with:

```bash
# Seed the database
uv run --env-file .env python -m scripts.seed_database

# Clear seeded data and seed fresh
uv run --env-file .env python -m scripts.seed_database --clear

# Clear seeded data only
uv run --env-file .env python -m scripts.seed_database --clear --no-seed
```

### In Docker

Docker Compose injects environment variables directly — no `--env-file` flag needed:

```bash
# Seed the database
docker compose exec app uv run python -m scripts.seed_database

# Clear seeded data and seed fresh
docker compose exec app uv run python -m scripts.seed_database --clear

# Clear seeded data only
docker compose exec app uv run python -m scripts.seed_database --clear --no-seed
```

### Notes

- `--clear` removes only the deterministic dataset created by this script.
- The script is idempotent and safe to rerun.
- Base roles and categories are ensured before seeding fake data.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines, including commit message conventions, code style, and pull request requirements.

## Troubleshooting

If you run into issues, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for solutions to common problems with Docker, database, uv, Celery, authentication, and more.

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

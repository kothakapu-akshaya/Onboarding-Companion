# Testing Guide

A comprehensive guide to testing in the Corpus Server project, covering test design principles, implementation patterns, and best practices.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Architecture](#test-architecture)
- [Directory Structure](#directory-structure)
- [Test Categories](#test-categories)
- [Writing Tests](#writing-tests)
- [Test Data Management](#test-data-management)
- [Fixtures and Utilities](#fixtures-and-utilities)
- [Running Tests](#running-tests)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Corpus Server uses a comprehensive testing strategy that emphasizes:

- **Maintainability**: Centralized fixtures and test data eliminate duplication
- **Clarity**: Clear separation between unit, integration, and security tests
- **Efficiency**: Parameterized tests provide maximum coverage with minimal code
- **Reusability**: Builder patterns and shared utilities enable flexible test construction
- **Reliability**: Consistent test patterns and standardized assertions

### Test Framework Stack

- **pytest**: Primary testing framework
- **FastAPI TestClient**: API endpoint testing
- **SQLModel/SQLAlchemy**: Database testing
- **unittest.mock**: Mocking and test doubles
- **Pydantic**: Schema validation testing

## 🏗️ Test Architecture

The test suite follows a layered architecture with clear separation of concerns:

```
┌─────────────────┐
│   Security      │  Authentication, authorization, vulnerability testing
├─────────────────┤
│  Integration    │  API endpoints, database, external services
├─────────────────┤
│     Unit        │  Pure logic, schemas, services (isolated)
├─────────────────┤
│   Fixtures      │  Reusable test infrastructure
├─────────────────┤
│  Test Data      │  Centralized data management
└─────────────────┘
```

## 📁 Directory Structure

```
tests/
├── conftest.py                      # Global pytest configuration and fixture imports
├── data/
│   └── test_data.py                # Centralized test data with builder patterns
├── fixtures/                       # Specialized fixture modules
│   ├── api_fixtures.py            # API client and database fixtures
│   ├── auth_fixtures.py           # Authentication-related fixtures
│   └── user_fixtures.py           # User data and mock objects
├── helpers/                        # Test utilities and assertions
│   ├── assertions.py              # Custom assertion helpers
│   └── test_builders.py           # Test data builders with builder pattern
├── unit/                           # Pure unit tests (no external dependencies)
│   ├── core/
│   │   └── test_validators.py     # Core validation logic testing
│   ├── schemas/
│   │   └── test_auth_schemas.py   # Pydantic schema validation
│   └── services/
│       └── test_validation_service.py # Service layer orchestration
├── integration/                    # Integration tests (with external dependencies)
│   ├── api/
│   │   └── test_auth_endpoints.py # API endpoint integration
│   ├── database/
│   │   └── test_postgis_integration.py # Database integration
│   └── external/
│       └── test_otp_integration.py # External service integration
└── security/                      # Security-focused tests
    └── test_auth_security.py      # Authentication security testing
```

## 🧪 Test Categories

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual components in isolation without external dependencies.

**Characteristics**:
- Fast execution (< 1ms per test)
- No database, network, or file system access
- Use mocks for dependencies
- Focus on business logic and validation

**Example**:
```python
# tests/unit/core/test_validators.py
@pytest.mark.parametrize("password,expected_valid", [
    ("SecurePass123!", True),
    ("weak", False),
])
def test_password_validation(password, expected_valid):
    if expected_valid:
        assert validate_password_strength(password).is_valid
    else:
        with pytest.raises(ValidationError):
            validate_password_strength(password)
```

### Integration Tests (`tests/integration/`)

**Purpose**: Test component interactions and external system integration.

**Characteristics**:
- Slower execution (10ms-1s per test)
- May use database, API calls, or external services
- Test real component interactions
- Verify end-to-end workflows

**Example**:
```python
# tests/integration/api/test_auth_endpoints.py
def test_user_registration_flow(app_client, user_registration_data):
    response = app_client.post("/api/v1/auth/signup", json=user_registration_data)
    assert response.status_code == 201
    assert "user_id" in response.json()
```

### Security Tests (`tests/security/`)

**Purpose**: Test security aspects, vulnerabilities, and access controls.

**Characteristics**:
- Focus on authentication, authorization, and data protection
- Test for common vulnerabilities (injection, XSS, etc.)
- Verify rate limiting and access controls
- May be slower due to comprehensive testing

**Example**:
```python
# tests/security/test_auth_security.py
def test_login_rate_limiting(app_client):
    for _ in range(10):
        response = app_client.post("/api/v1/auth/login", 
                                 json={"phone": "9999999999", "password": "wrong"})
    assert response.status_code == 429  # Too Many Requests
```

## ✍️ Writing Tests

### Test Naming Conventions

Follow these naming patterns for consistency:

```python
# Test files
test_<module_name>.py              # General tests
test_<feature>_<aspect>.py         # Specific feature tests

# Test classes
class Test<FeatureName>:           # Group related tests
class Test<FeatureName><Aspect>:   # Specific aspect testing

# Test methods
def test_<action>_<expected_result>():           # Basic pattern
def test_<action>_with_<condition>():           # Conditional testing
def test_<action>_<condition>_<expected_result>(): # Full context
```

### Test Structure Pattern

Use the **Arrange-Act-Assert** pattern consistently:

```python
def test_user_registration_success():
    # Arrange: Set up test data and conditions
    registration_data = TestData.user_registration_data()
    
    # Act: Execute the function under test
    result = validate_user_registration(registration_data)
    
    # Assert: Verify the expected outcome
    assert isinstance(result, UserRegistrationValidation)
    assert result.phone.startswith("+91")
```

### Parameterized Tests

Use parameterization for testing multiple scenarios efficiently:

```python
@pytest.mark.parametrize("input_data,expected_valid,description", [
    ({"phone": "9876543210"}, True, "Valid Indian mobile"),
    ({"phone": "5876543210"}, False, "Invalid starting digit"),
    ({"phone": "987654321"}, False, "Too short"),
], ids=lambda x: x[2])  # Use description as test ID
def test_phone_validation(input_data, expected_valid, description):
    if expected_valid:
        assert validate_phone(input_data["phone"])
    else:
        with pytest.raises(ValidationError):
            validate_phone(input_data["phone"])
```

### Async Test Patterns

For testing async functions:

```python
import pytest

@pytest.mark.asyncio
async def test_async_otp_service():
    service = OTPService()
    result = await service.send_otp("+919876543210")
    assert result["status"] == "success"
```

## 📊 Test Data Management

### Centralized Test Data

All test data is managed through `tests/data/test_data.py`:

```python
class TestData:
    """Centralized test data with validation cases."""
    
    # Validation test cases
    VALID_PASSWORDS = ["SecurePass123!", "MyStr0ng#Password"]
    INVALID_PASSWORDS = ["weak", "12345678", "password"]
    
    # Builder methods for flexible data construction
    @staticmethod
    def user_registration_data(**overrides):
        """Build user registration data with optional overrides."""
        default = {
            "phone": "9876543210",
            "name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePass123!",
            "has_given_consent": True,
        }
        return {**default, **overrides}

# Pre-built parameterized test cases
PASSWORD_VALIDATION_CASES = [
    (password, True) for password in TestData.VALID_PASSWORDS
] + [
    (password, False) for password in TestData.INVALID_PASSWORDS
]
```

### Test Data Builders

Use builder pattern for complex test scenarios:

```python
# tests/helpers/test_builders.py
class UserDataBuilder:
    def __init__(self):
        self.data = TestData.user_registration_data()
    
    def with_phone(self, phone: str):
        self.data["phone"] = phone
        return self
    
    def with_invalid_password(self):
        self.data["password"] = "weak"
        self.data["confirm_password"] = "weak"
        return self
    
    def without_consent(self):
        self.data["has_given_consent"] = False
        return self
    
    def build(self):
        return self.data.copy()

# Usage in tests
def test_registration_without_consent():
    invalid_data = user_data().without_consent().build()
    with pytest.raises(ValidationError):
        UserRegistrationValidation(**invalid_data)
```

## 🔧 Fixtures and Utilities

### Core Fixtures

Essential fixtures available to all tests:

```python
# tests/fixtures/api_fixtures.py
@pytest.fixture(scope="session")
def app_client():
    """Single test client for all tests."""
    return TestClient(app)

@pytest.fixture
def db_session(db_engine):
    """Database session with automatic cleanup."""
    with Session(db_engine) as session:
        yield session
        session.rollback()

# tests/fixtures/user_fixtures.py
@pytest.fixture
def mock_user():
    """Mock user object for unit tests."""
    return Mock(spec=User, **TestData.mock_user_data())

@pytest.fixture
def test_user(db_session):
    """Real user in test database."""
    user = User(**TestData.mock_user_data())
    db_session.add(user)
    db_session.commit()
    yield user
    db_session.delete(user)
    db_session.commit()
```

### Custom Assertions

Use custom assertions for domain-specific validations:

```python
# tests/helpers/assertions.py
def assert_api_response(response, expected_status: int, expected_keys: List[str] = None):
    """Assert API response status and structure."""
    assert response.status_code == expected_status
    if expected_keys:
        response_data = response.json()
        for key in expected_keys:
            assert key in response_data

def assert_phone_formatted(actual: str, expected: str):
    """Assert phone number formatting."""
    assert actual == expected, f"Expected {expected}, got {actual}"

# Usage in tests
def test_login_success(app_client):
    response = app_client.post("/api/v1/auth/login", json=login_data)
    assert_api_response(response, 200, ["access_token", "token_type"])
```

## 🚀 Running Tests

### Basic Test Execution

```bash
# Run all tests
uv run pytest

# Run specific test category
uv run pytest tests/unit/          # Unit tests only
uv run pytest tests/integration/   # Integration tests only
uv run pytest tests/security/      # Security tests only

# Run specific test file
uv run pytest tests/unit/core/test_validators.py

# Run specific test
uv run pytest tests/unit/core/test_validators.py::test_password_validation
```

### Test Configuration

```bash
# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run with detailed output
uv run pytest -v --tb=short

# Run parallel tests (if pytest-xdist installed)
uv run pytest -n auto

# Run only failed tests from last run
uv run pytest --lf

# Run tests matching pattern
uv run pytest -k "password"
```

### Environment Variables

Set these for comprehensive testing:

```bash
# Enable integration tests
export RUN_INTEGRATION_TESTS=1

# Enable security tests
export RUN_SECURITY_TESTS=1

# Set test database
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
```

### Test Markers

Use pytest markers for test categorization:

```python
# In test files
@pytest.mark.slow
def test_heavy_operation():
    pass

@pytest.mark.integration
def test_database_integration():
    pass

@pytest.mark.security
def test_sql_injection_prevention():
    pass
```

```bash
# Run only fast tests
uv run pytest -m "not slow"

# Run only integration tests
uv run pytest -m integration

# Run security tests
uv run pytest -m security
```

## 🎯 Best Practices

### 1. Test Independence

Each test should be completely independent:

```python
# ✅ Good: Independent test
def test_user_creation():
    user_data = TestData.user_registration_data()
    user = create_user(user_data)
    assert user.phone == "+919876543210"

# ❌ Bad: Depends on previous test state
def test_user_exists():
    user = get_user_by_phone("+919876543210")  # Assumes previous test ran
    assert user is not None
```

### 2. Descriptive Test Names

Use clear, descriptive names that explain the test purpose:

```python
# ✅ Good: Clear intent
def test_user_registration_fails_when_phone_already_exists():
    pass

def test_password_validation_rejects_weak_passwords():
    pass

# ❌ Bad: Unclear purpose
def test_user_stuff():
    pass

def test_validation():
    pass
```

### 3. Single Responsibility

Each test should verify one specific behavior:

```python
# ✅ Good: Tests one thing
def test_password_requires_minimum_length():
    with pytest.raises(ValidationError):
        validate_password("short")

def test_password_requires_special_character():
    with pytest.raises(ValidationError):
        validate_password("NoSpecialChar123")

# ❌ Bad: Tests multiple things
def test_password_validation():
    # Tests length, special chars, numbers, etc. all in one test
    pass
```

### 4. Effective Mocking

Mock external dependencies, but not the code under test:

```python
# ✅ Good: Mock external service
@patch("app.services.otp_service.external_sms_api")
def test_otp_sending(mock_sms_api):
    mock_sms_api.send_sms.return_value = {"status": "sent"}
    
    service = OTPService()
    result = service.send_otp("+919876543210")
    
    assert result["status"] == "success"
    mock_sms_api.send_sms.assert_called_once()

# ❌ Bad: Mocking the code under test
@patch("app.services.otp_service.OTPService.send_otp")
def test_otp_sending(mock_send_otp):
    mock_send_otp.return_value = {"status": "success"}
    # This test doesn't verify the actual implementation
```

### 5. Test Data Isolation

Use fixtures and builders to keep test data isolated:

```python
# ✅ Good: Isolated test data
def test_user_creation(user_registration_data):
    # Each test gets fresh data
    user = create_user(user_registration_data)
    assert user.name == "John Doe"

# ✅ Good: Modified test data
def test_invalid_email():
    invalid_data = user_data().with_email("invalid.email").build()
    with pytest.raises(ValidationError):
        UserRegistrationValidation(**invalid_data)

# ❌ Bad: Shared mutable data
SHARED_USER_DATA = {"name": "John Doe", "phone": "9876543210"}

def test_user_creation():
    SHARED_USER_DATA["email"] = "john@example.com"  # Modifies shared state
    user = create_user(SHARED_USER_DATA)
```

## 🔄 Common Patterns

### Error Testing Pattern

```python
def test_validation_errors():
    """Test that validation errors are properly raised and formatted."""
    invalid_data = user_data().with_phone("invalid").build()
    
    with pytest.raises(ValidationError) as exc_info:
        UserRegistrationValidation(**invalid_data)
    
    # Verify specific error details
    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0]["field"] == "phone"
    assert "invalid phone format" in errors[0]["msg"].lower()
```

### Database Testing Pattern

```python
def test_user_persistence(db_session):
    """Test that user data is correctly persisted to database."""
    # Create user
    user_data = TestData.mock_user_data()
    user = User(**user_data)
    db_session.add(user)
    db_session.commit()
    
    # Verify persistence
    saved_user = db_session.query(User).filter_by(phone=user.phone).first()
    assert saved_user is not None
    assert saved_user.name == user_data["name"]
    assert saved_user.email == user_data["email"]
```

### API Testing Pattern

```python
def test_api_endpoint_success(app_client, user_registration_data):
    """Test successful API endpoint response."""
    response = app_client.post("/api/v1/auth/signup", json=user_registration_data)
    
    # Verify response
    assert_api_response(response, 201, ["user_id", "message"])
    
    response_data = response.json()
    assert response_data["message"] == "User registered successfully"
    assert isinstance(response_data["user_id"], str)

def test_api_endpoint_validation_error(app_client):
    """Test API endpoint validation error handling."""
    invalid_data = {"phone": "invalid"}
    
    response = app_client.post("/api/v1/auth/signup", json=invalid_data)
    
    assert_api_error(response, 422)
    error_detail = response.json()["detail"]
    assert any("phone" in str(error).lower() for error in error_detail)
```

### Mock Service Pattern

```python
@pytest.fixture
def mock_otp_service():
    """Mock OTP service for testing."""
    service = Mock(spec=OTPService)
    service.send_otp = AsyncMock(return_value={
        "status": "success",
        "reference_id": "test_ref_123"
    })
    service.verify_otp = AsyncMock(return_value={
        "valid": True,
        "message": "OTP verified successfully"
    })
    return service

def test_login_with_otp(app_client, mock_otp_service):
    """Test OTP-based login flow."""
    with patch("app.api.v1.endpoints.auth.OTPService", return_value=mock_otp_service):
        # Test OTP sending
        response = app_client.post("/api/v1/auth/login/send-otp", 
                                 json={"phone": "9876543210"})
        assert_api_response(response, 200, ["status", "reference_id"])
        
        # Test OTP verification
        otp_data = {
            "phone": "9876543210",
            "otp_code": "123456",
            "reference_id": "test_ref_123"
        }
        response = app_client.post("/api/v1/auth/login/verify-otp", json=otp_data)
        assert_api_response(response, 200, ["access_token"])
```

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. Import Errors

**Problem**: `ModuleNotFoundError` when running tests.

**Solution**: 
```bash
# Ensure you're running from project root
cd /path/to/corpus-server-app

# Install dependencies
uv sync

# Run tests
uv run pytest
```

#### 2. Database Connection Issues

**Problem**: Tests fail with database connection errors.

**Solution**:
```bash
# Set test database URL
export TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/test_db"

# Or skip database tests
pytest -m "not database"
```

#### 3. Fixture Not Found

**Problem**: `pytest.fixture` not found or not working.

**Solution**:
```python
# Ensure fixture is properly imported in conftest.py
# tests/conftest.py
from tests.fixtures.user_fixtures import *
from tests.fixtures.api_fixtures import *

# Or import directly in test file
from tests.fixtures.user_fixtures import mock_user
```

#### 4. Async Test Issues

**Problem**: Async tests not running or hanging.

**Solution**:
```bash
# Install dependencies (pytest-asyncio is already included)
uv sync

# Add to pytest.ini or pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

#### 5. Parameterized Test Failures

**Problem**: Parameterized tests failing with unclear error messages.

**Solution**:
```python
# Use ids parameter for clearer test names
@pytest.mark.parametrize("input,expected", [
    ("valid_input", True),
    ("invalid_input", False),
], ids=["valid_case", "invalid_case"])

# Or use lambda for dynamic ids
@pytest.mark.parametrize("data", test_cases, ids=lambda x: x.get("description", str(x)))
```

### Performance Issues

#### Slow Test Execution

1. **Use appropriate test scope**:
   ```python
   @pytest.fixture(scope="session")  # For expensive setup
   def expensive_fixture():
       pass
   ```

2. **Mock external services**:
   ```python
   @patch("app.services.external_api")
   def test_with_mock(mock_api):
       pass
   ```

3. **Use pytest-xdist for parallel execution**:
   ```bash
   # pytest-xdist is already included in dev dependencies
   uv run pytest -n auto
   ```

#### Memory Usage

1. **Clean up resources in fixtures**:
   ```python
   @pytest.fixture
   def resource():
       resource = create_resource()
       yield resource
       resource.cleanup()  # Always cleanup
   ```

2. **Use appropriate fixture scopes**:
   ```python
   @pytest.fixture(scope="function")  # Default, new instance per test
   @pytest.fixture(scope="class")     # Shared within test class
   @pytest.fixture(scope="session")   # Shared across entire test session
   ```

### Debugging Tips

1. **Use pytest debugging flags**:
   ```bash
   pytest -v --tb=long  # Verbose output with full tracebacks
   pytest --pdb         # Drop into debugger on failures
   pytest --capture=no  # Show print statements
   ```

2. **Add logging to tests**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   def test_something():
       logging.info("Test starting...")
       # Test code here
   ```

3. **Use pytest-sugar for better output**:
   ```bash
   # pytest-sugar is already included in dev dependencies
   uv run pytest  # Automatically provides better formatting
   ```

## 📚 Additional Resources

### Documentation
- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLModel testing patterns](https://sqlmodel.tiangolo.com/tutorial/)

### Tools and Plugins
- `pytest-cov`: Code coverage reporting
- `pytest-xdist`: Parallel test execution
- `pytest-mock`: Enhanced mocking capabilities
- `pytest-asyncio`: Async test support
- `pytest-sugar`: Better test output formatting

### Testing Philosophy
- Test behavior, not implementation
- Write tests first (TDD) when possible
- Keep tests simple and focused
- Maintain test code quality like production code
- Use meaningful test names and documentation

---

*This testing guide is a living document. Update it as new patterns emerge and the testing strategy evolves.*
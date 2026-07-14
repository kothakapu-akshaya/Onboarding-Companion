"""Custom pytest plugins for corpus-server-app testing.

Provides additional functionality and test utilities.
"""

import os
import time
from pathlib import Path

import pytest


def pytest_configure(config):
    """Configure pytest with custom settings and markers."""
    # Register custom markers (these are also in pytest.ini
    # but this is more explicit)
    config.addinivalue_line(
        "markers", "unit: Unit tests without external dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests with external systems"
    )
    config.addinivalue_line("markers", "security: Security-focused tests")
    config.addinivalue_line(
        "markers", "slow: Tests that take more than 1 second"
    )
    config.addinivalue_line(
        "markers", "database: Tests requiring database connection"
    )
    config.addinivalue_line("markers", "api: HTTP API endpoint tests")
    config.addinivalue_line("markers", "mock: Tests using extensive mocking")

    # Set test environment variables
    os.environ.setdefault("TESTING", "1")
    os.environ.setdefault(
        "LOG_LEVEL", "WARNING"
    )  # Reduce log noise during testing


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically.

    Based on test location.
    """
    for item in items:
        # Auto-mark tests based on their file path
        test_path = Path(item.fspath)
        relative_path = test_path.relative_to(Path(config.rootdir))

        # Add markers based on directory structure
        if "unit" in relative_path.parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in relative_path.parts:
            item.add_marker(pytest.mark.integration)
        elif "security" in relative_path.parts:
            item.add_marker(pytest.mark.security)

        # Add specific markers based on filename patterns
        if "test_auth" in item.name or "auth" in str(relative_path):
            item.add_marker(pytest.mark.auth)
        elif "test_validation" in item.name or "validation" in str(
            relative_path
        ):
            item.add_marker(pytest.mark.validation)
        elif "otp" in item.name or "otp" in str(relative_path):
            item.add_marker(pytest.mark.otp)
        elif "api" in str(relative_path) or "endpoint" in item.name:
            item.add_marker(pytest.mark.api)
        elif "database" in str(relative_path) or "db" in item.name:
            item.add_marker(pytest.mark.database)


def pytest_runtest_setup(item):
    """Set up individual test runs with environment checks."""
    # Skip integration tests if not explicitly enabled
    if item.get_closest_marker("integration") and not os.getenv(
        "RUN_INTEGRATION_TESTS"
    ):
        pytest.skip(
            "Integration tests disabled (set RUN_INTEGRATION_TESTS=1 to enable)"
        )

    # Skip security tests if not explicitly enabled
    if item.get_closest_marker("security") and not os.getenv(
        "RUN_SECURITY_TESTS"
    ):
        pytest.skip(
            "Security tests disabled (set RUN_SECURITY_TESTS=1 to enable)"
        )

    # Skip database tests if database is not available
    if item.get_closest_marker("database"):
        database_url = os.getenv("TEST_DATABASE_URL") or os.getenv(
            "DATABASE_URL"
        )
        if not database_url or "postgres" not in database_url.lower():
            pytest.skip("Database not available (set TEST_DATABASE_URL)")

    # Skip slow tests in fast mode
    if item.get_closest_marker("slow") and os.getenv("PYTEST_FAST_MODE"):
        pytest.skip("Slow tests disabled in fast mode")


def pytest_runtest_call(pyfuncitem):
    """Track test execution time and mark slow tests."""
    start_time = time.time()

    # Run the test
    try:
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time

        # Auto-mark slow tests
        if duration > 1.0 and not pyfuncitem.get_closest_marker("slow"):
            pyfuncitem.add_marker(pytest.mark.slow)


def pytest_sessionstart(session):
    """Print test session information."""
    print("\n🧪 Starting test session for corpus-server-app")
    print(f"📁 Test directory: {session.config.rootdir}/tests")

    # Show environment configuration
    env_vars = {
        "RUN_INTEGRATION_TESTS": os.getenv("RUN_INTEGRATION_TESTS", "Not set"),
        "RUN_SECURITY_TESTS": os.getenv("RUN_SECURITY_TESTS", "Not set"),
        "TEST_DATABASE_URL": "Set"
        if os.getenv("TEST_DATABASE_URL")
        else "Not set",
        "TESTING": os.getenv("TESTING", "Not set"),
    }

    print("🔧 Environment configuration:")
    for key, value in env_vars.items():
        print(f"   {key}: {value}")


def pytest_sessionfinish(session, exitstatus):
    """Print test session summary."""
    if exitstatus == 0:
        print("\n✅ All tests passed successfully!")
    else:
        print(f"\n❌ Tests completed with exit status: {exitstatus}")

    # Show test execution summary
    if hasattr(session, "testscollected"):
        print(f"📊 Total tests collected: {session.testscollected}")


@pytest.fixture(scope="session")
def test_environment():
    """Provide test environment information."""
    return {
        "testing": True,
        "database_available": bool(
            os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
        ),
        "integration_tests_enabled": bool(os.getenv("RUN_INTEGRATION_TESTS")),
        "security_tests_enabled": bool(os.getenv("RUN_SECURITY_TESTS")),
        "fast_mode": bool(os.getenv("PYTEST_FAST_MODE")),
    }


@pytest.fixture(scope="session")
def test_metrics():
    """Collect test execution metrics."""
    metrics = {
        "start_time": time.time(),
        "test_count": 0,
        "slow_tests": [],
        "failed_tests": [],
    }
    return metrics


@pytest.fixture
def performance_tracker():
    """Track test performance and provide timing utilities."""

    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.checkpoints = {}

        def start(self):
            self.start_time = time.time()
            return self

        def checkpoint(self, name: str):
            if self.start_time is None:
                self.start()
            self.checkpoints[name] = time.time() - self.start_time

        def elapsed(self):
            if self.start_time is None:
                return 0
            return time.time() - self.start_time

        def assert_faster_than(self, seconds: float):
            elapsed = self.elapsed()
            assert elapsed < seconds, (
                f"Test took {elapsed:.2f}s, expected < {seconds}s"
            )

    return PerformanceTracker()


class TestDataManager:
    """Manage test data lifecycle and cleanup."""

    def __init__(self):
        self.created_resources = []
        self.cleanup_callbacks = []

    def track_resource(self, resource, cleanup_callback=None):
        """Track a resource for automatic cleanup."""
        self.created_resources.append(resource)
        if cleanup_callback:
            self.cleanup_callbacks.append(cleanup_callback)
        return resource

    def cleanup(self):
        """Clean up all tracked resources."""
        for callback in reversed(self.cleanup_callbacks):
            try:
                callback()
            except Exception as e:
                print(f"Warning: Cleanup failed: {e}")

        self.created_resources.clear()
        self.cleanup_callbacks.clear()


@pytest.fixture
def test_data_manager():
    """Provide test data management utilities."""
    manager = TestDataManager()
    yield manager
    manager.cleanup()


# Custom pytest hooks for better error reporting
def pytest_runtest_makereport(item, call):
    """Create custom test reports with additional context."""
    if call.when == "call":
        # Add test location and markers to reports
        markers = [marker.name for marker in item.iter_markers()]
        if markers:
            item.user_properties.append(("markers", ", ".join(markers)))

        # Add test file location
        item.user_properties.append(("location", f"{item.fspath}::{item.name}"))


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add custom summary information to test output."""
    if exitstatus != 0:
        return

    # Count tests by category
    test_counts = {}
    for item in terminalreporter.stats.get("passed", []):
        for prop_name, prop_value in item.user_properties:
            if prop_name == "markers":
                for marker in prop_value.split(", "):
                    test_counts[marker] = test_counts.get(marker, 0) + 1

    if test_counts:
        terminalreporter.write_sep("=", "Test Summary by Category")
        for marker, count in sorted(test_counts.items()):
            terminalreporter.write_line(f"  {marker}: {count} tests")

    # Show quick start message
    terminalreporter.write_sep("=", "Quick Commands")
    terminalreporter.write_line(
        "  Run unit tests only:       pytest tests/unit/"
    )
    terminalreporter.write_line(
        "  Run integration tests:     pytest tests/integration/"
    )
    terminalreporter.write_line(
        "  Run security tests:        pytest tests/security/"
    )
    terminalreporter.write_line(
        "  Run with coverage:          pytest --cov=app"
    )
    terminalreporter.write_line("  Run parallel:               pytest -n auto")
    terminalreporter.write_line("  Run failed tests:           pytest --lf")

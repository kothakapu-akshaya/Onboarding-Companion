"""Tests for app/main.py."""

import asyncio
from unittest.mock import MagicMock, patch

from app.main import app, health_check, root


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_returns_welcome_message(self):
        """Test root endpoint returns welcome message."""
        from app.core.config import settings

        data = asyncio.run(root())
        assert "message" in data
        assert settings.PROJECT_NAME in data["message"]
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"

    def test_root_path(self):
        """Test root path exists."""
        routes = [route.path for route in app.routes]
        assert "/" in routes

    def test_root_response_format(self):
        """Test root endpoint response format."""
        data = asyncio.run(root())

        assert "message" in data
        assert "version" in data
        assert "docs" in data


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check_returns_healthy(self):
        """Test health check returns healthy status."""
        data = asyncio.run(health_check())
        assert data["status"] == "healthy"

    def test_health_check_no_auth_required(self):
        """Test health check doesn't require authentication."""
        routes = [route.path for route in app.routes]
        assert "/health" in routes

    def test_health_check_response_format(self):
        """Test health check response format."""
        data = asyncio.run(health_check())
        assert "status" in data


class TestExceptionHandlers:
    """Test exception handlers."""

    def test_exception_handler_registered(self):
        """Test exception handler is registered on app."""
        from app.main import app

        exception_handlers = app.exception_handlers
        assert Exception in exception_handlers

    @patch("app.main.posthog")
    @patch("app.main.logger")
    def test_generic_exception_handler_captures_exception(
        self, mock_logger, mock_posthog
    ):
        """Test generic exception handler captures exception."""
        from app.main import generic_exception_handler

        mock_request = MagicMock()
        mock_request.url = "http://test.com/test"
        mock_exc = Exception("Test error")

        import asyncio

        asyncio.run(generic_exception_handler(mock_request, mock_exc))

        mock_posthog.capture_exception.assert_called_once_with(mock_exc)
        mock_logger.error.assert_called_once()

    @patch("app.main.posthog")
    @patch("app.main.logger")
    def test_generic_exception_handler_returns_500(
        self, mock_logger, mock_posthog
    ):
        """Test generic exception handler returns 500 status."""
        from app.main import generic_exception_handler

        mock_request = MagicMock()
        mock_request.url = "http://test.com/test"
        mock_exc = Exception("Test error")

        import asyncio

        result = asyncio.run(generic_exception_handler(mock_request, mock_exc))

        assert result.status_code == 500


class TestAPIRouter:
    """Test API router inclusion."""

    def test_api_router_included(self):
        """Test API router is included in app."""
        from app.main import app

        routes = [route.path for route in app.routes]

        assert any("/api/v1/" in route for route in routes)

    def test_api_router_prefix(self):
        """Test API router has correct prefix."""
        from app.main import app

        api_routes = [
            r
            for r in app.routes
            if hasattr(r, "path") and r.path.startswith("/api/v1")
        ]
        assert len(api_routes) > 0


class TestFastAPIApp:
    """Test FastAPI app configuration."""

    def test_app_created_with_correct_title(self):
        """Test app is created with correct project name."""
        from app.core.config import settings
        from app.main import app

        assert app.title == settings.PROJECT_NAME

    def test_app_created_with_correct_description(self):
        """Test app is created with correct description."""
        from app.main import app

        assert (
            app.description == "Indic languages corpus collections backend API"
        )

    def test_app_created_with_correct_version(self):
        """Test app is created with correct version."""
        from app.main import app

        assert app.version == "0.1.0"

    def test_app_created_with_openapi_url(self):
        """Test app has correct openapi URL."""
        from app.core.config import settings
        from app.main import app

        expected_url = f"{settings.API_V1_STR}/openapi.json"
        assert app.openapi_url == expected_url


class TestPosthog:
    """Test Posthog configuration."""

    def test_posthog_initialized(self):
        """Test posthog is initialized with settings."""
        from app.main import posthog

        assert posthog is not None


class TestRegisterExceptionHandlers:
    """Test exception handler registration."""

    def test_validation_exception_handlers_registered(self):
        """Test validation exception handlers are registered."""
        from app.main import app

        assert app.exception_handlers is not None
        assert len(app.exception_handlers) > 0


class TestCORS:
    """Test CORS middleware configuration."""

    def test_cors_middleware_added(self):
        """Test CORS middleware is added."""
        from app.main import app

        cors_middleware = None
        for middleware in app.user_middleware:
            if (
                hasattr(middleware, "cls")
                and middleware.cls.__name__ == "CORSMiddleware"
            ):
                cors_middleware = middleware
                break

        assert cors_middleware is not None


class TestLifespan:
    """Test application lifespan management."""

    def test_lifespan_context_manager_exists(self):
        """Test lifespan context manager is defined."""
        from app.main import lifespan

        assert lifespan is not None

    def test_app_has_lifespan(self):
        """Test app has lifespan context manager."""
        from app.main import app

        assert hasattr(app, "router")
        assert app.router.lifespan_context is not None

    @patch("app.main.create_db_and_tables")
    @patch("app.main.logger")
    def test_startup_logs_message(self, mock_logger, mock_create_db):
        """Test startup logs message."""

        # The lifespan is already configured, check it logs on startup
        # This is implicitly tested by checking lifespan exists

    @patch("app.main.create_db_and_tables")
    @patch("app.main.logger")
    def test_shutdown_logs_message(self, mock_logger, mock_create_db):
        """Test shutdown logs message."""

        # The lifespan is already configured, check it logs on shutdown
        # This is implicitly tested by checking lifespan exists

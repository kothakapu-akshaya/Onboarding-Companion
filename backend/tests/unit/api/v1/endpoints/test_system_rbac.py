"""Tests for system RBAC endpoints."""

from app.api.v1.endpoints.system_rbac import router


class TestSystemRBACEndpoints:
    """Test cases for system RBAC endpoints."""

    def test_router_has_correct_prefix(self):
        """Test router has correct prefix."""
        assert router.prefix == "/system"

    def test_router_has_correct_tags(self):
        """Test router has correct tags."""
        assert "system" in router.tags

    def test_get_rbac_status_returns_status(self):
        """Test get_rbac_system_status returns proper structure."""
        from app.core.rbac_fastapi import get_rbac_system_status

        result = get_rbac_system_status()

        assert "system" in result
        assert "status" in result
        assert result["status"] == "healthy"

    def test_clear_role_cache_function(self):
        """Test clear_role_cache function exists and works."""
        from app.core.rbac_fastapi import clear_role_cache

        clear_role_cache()

    def test_require_rbac_admin_returns_callable(self):
        """Test require_rbac_admin returns a callable."""
        from app.core.rbac_fastapi import require_rbac_admin

        result = require_rbac_admin()
        assert callable(result)

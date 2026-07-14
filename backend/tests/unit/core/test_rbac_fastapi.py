"""Tests for app/core/rbac_fastapi.py."""

from unittest.mock import MagicMock, patch

from app.core.rbac_fastapi import (
    PERMISSION_MATRIX,
    can_user_access,
    clear_role_cache,
    create_rbac_dependency,
    get_available_permissions,
    get_rbac_system_status,
    get_user_permission_summary,
    get_user_roles,
    has_permission,
    require_admin,
    require_any_permission,
    require_any_role,
    require_multiple_permissions,
    require_permission,
    require_rbac_admin,
    require_reviewer,
    require_users_delete,
    require_users_read,
    require_users_update,
    require_users_write,
)
from app.models.role import RoleEnum


class TestPermissionMatrix:
    """Test permission matrix configuration."""

    def test_permission_matrix_has_admin_role(self):
        """Test admin role has all permissions."""
        assert RoleEnum.admin in PERMISSION_MATRIX
        assert "users" in PERMISSION_MATRIX[RoleEnum.admin]
        assert "records" in PERMISSION_MATRIX[RoleEnum.admin]
        assert "DELETE" in PERMISSION_MATRIX[RoleEnum.admin]["users"]

    def test_permission_matrix_has_reviewer_role(self):
        """Test reviewer role has correct permissions."""
        assert RoleEnum.reviewer in PERMISSION_MATRIX
        assert "users" in PERMISSION_MATRIX[RoleEnum.reviewer]
        assert "GET" in PERMISSION_MATRIX[RoleEnum.reviewer]["users"]

    def test_permission_matrix_has_user_role(self):
        """Test user role has correct permissions."""
        assert RoleEnum.user in PERMISSION_MATRIX
        assert "records" in PERMISSION_MATRIX[RoleEnum.user]
        assert "POST" in PERMISSION_MATRIX[RoleEnum.user]["records"]


class TestGetAvailablePermissions:
    """Test get_available_permissions function."""

    def test_admin_permissions(self):
        """Test admin gets all permissions."""
        result = get_available_permissions(["admin"])
        assert "users" in result
        assert "records" in result
        assert "categories" in result
        assert "DELETE" in result["users"]

    def test_reviewer_permissions(self):
        """Test reviewer gets limited permissions."""
        result = get_available_permissions(["reviewer"])
        assert "users" in result
        assert "records" in result
        assert "GET" in result["users"]
        assert "PUT" in result["records"]

    def test_user_permissions(self):
        """Test regular user gets basic permissions."""
        result = get_available_permissions(["user"])
        assert "records" in result
        assert "categories" in result
        assert "GET" in result["records"]
        assert "POST" in result["records"]

    def test_multiple_roles(self):
        """Test combining multiple roles."""
        result = get_available_permissions(["user", "reviewer"])
        assert "GET" in result.get("records", set())

    def test_empty_roles(self):
        """Test empty roles list."""
        result = get_available_permissions([])
        assert result == {}

    def test_case_insensitive(self):
        """Test case insensitive role matching."""
        result = get_available_permissions(["ADMIN", "USER"])
        assert "records" in result


class TestHasPermission:
    """Test has_permission function."""

    def test_admin_can_delete_users(self):
        """Test admin can delete users."""
        assert has_permission(["admin"], "users", "DELETE") is True

    def test_reviewer_can_get_users(self):
        """Test reviewer can get users."""
        assert has_permission(["reviewer"], "users", "GET") is True

    def test_reviewer_cannot_delete_users(self):
        """Test reviewer cannot delete users."""
        assert has_permission(["reviewer"], "users", "DELETE") is False

    def test_user_cannot_delete_records(self):
        """Test user cannot delete records."""
        assert has_permission(["user"], "records", "DELETE") is False

    def test_user_can_post_records(self):
        """Test user can post records."""
        assert has_permission(["user"], "records", "POST") is True

    def test_invalid_resource_returns_false(self):
        """Test invalid resource returns false."""
        assert has_permission(["admin"], "invalid", "GET") is False

    def test_invalid_method_returns_false(self):
        """Test invalid method returns false."""
        assert has_permission(["admin"], "users", "PATCH") is False

    def test_empty_roles_returns_false(self):
        """Test empty roles returns false."""
        assert has_permission([], "users", "GET") is False


class TestCanUserAccess:
    """Test can_user_access function."""

    @patch("app.core.rbac_fastapi.get_user_roles")
    def test_can_access_with_admin_role(self, mock_get_roles):
        """Test user with admin role can access."""
        mock_get_roles.return_value = ["admin"]
        assert can_user_access("123", "users", "DELETE") is True

    @patch("app.core.rbac_fastapi.get_user_roles")
    def test_cannot_access_without_permission(self, mock_get_roles):
        """Test user without permission cannot access."""
        mock_get_roles.return_value = ["user"]
        assert can_user_access("123", "users", "DELETE") is False


class TestGetUserPermissionSummary:
    """Test get_user_permission_summary function."""

    @patch("app.core.rbac_fastapi.get_user_roles")
    def test_returns_summary_with_admin(self, mock_get_roles):
        """Test summary for admin user."""
        mock_get_roles.return_value = ["admin"]
        result = get_user_permission_summary("123")

        assert result["user_id"] == "123"
        assert "admin" in result["roles"]
        assert "permissions" in result
        assert result["total_permissions"] > 0

    @patch("app.core.rbac_fastapi.get_user_roles")
    def test_returns_summary_with_user_role(self, mock_get_roles):
        """Test summary for regular user."""
        mock_get_roles.return_value = ["user"]
        result = get_user_permission_summary("456")

        assert result["user_id"] == "456"
        assert "user" in result["roles"]


class TestClearRoleCache:
    """Test clear_role_cache function."""

    @patch("app.core.rbac_fastapi.get_user_roles_cached")
    def test_clears_cache(self, mock_cached):
        """Test cache is cleared."""
        mock_cached.cache_clear = MagicMock()
        clear_role_cache()
        mock_cached.cache_clear.assert_called_once()


class TestCreateRbacDependency:
    """Test create_rbac_dependency function."""

    def test_returns_callable(self):
        """Test returns a callable."""
        result = create_rbac_dependency()
        assert callable(result)

    def test_with_roles_parameter(self):
        """Test with roles parameter."""
        result = create_rbac_dependency(roles=RoleEnum.admin)
        assert callable(result)

    def test_with_resource_and_method(self):
        """Test with resource and method."""
        result = create_rbac_dependency(resource="users", method="GET")
        assert callable(result)

    def test_with_list_of_roles(self):
        """Test with list of roles."""
        result = create_rbac_dependency(
            roles=[RoleEnum.admin, RoleEnum.reviewer]
        )
        assert callable(result)


class TestRequireAnyPermission:
    """Test require_any_permission function."""

    def test_returns_callable(self):
        """Test returns callable."""
        result = require_any_permission("users")
        assert callable(result)


class TestRequireMultiplePermissions:
    """Test require_multiple_permissions function."""

    def test_returns_callable(self):
        """Test returns callable."""
        result = require_multiple_permissions([("users", "GET")])
        assert callable(result)


class TestRequireFunctions:
    """Test require_* convenience functions."""

    def test_require_admin(self):
        """Test require_admin returns callable."""
        result = require_admin()
        assert callable(result)

    def test_require_reviewer(self):
        """Test require_reviewer returns callable."""
        result = require_reviewer()
        assert callable(result)

    def test_require_any_role(self):
        """Test require_any_role returns callable."""
        result = require_any_role()
        assert callable(result)

    def test_require_permission(self):
        """Test require_permission returns callable."""
        result = require_permission("users", "GET")
        assert callable(result)

    def test_require_any_permission(self):
        """Test require_any_permission returns callable."""
        result = require_any_permission("records")
        assert callable(result)

    def test_require_multiple_permissions(self):
        """Test require_multiple_permissions returns callable."""
        result = require_multiple_permissions(
            [("users", "GET"), ("records", "POST")]
        )
        assert callable(result)


class TestResourceSpecificShortcuts:
    """Test resource-specific shortcut functions."""

    def test_require_users_read(self):
        """Test require_users_read returns callable."""
        result = require_users_read()
        assert callable(result)

    def test_require_users_write(self):
        """Test require_users_write returns callable."""
        result = require_users_write()
        assert callable(result)

    def test_require_users_update(self):
        """Test require_users_update returns callable."""
        result = require_users_update()
        assert callable(result)

    def test_require_users_delete(self):
        """Test require_users_delete returns callable."""
        result = require_users_delete()
        assert callable(result)


class TestGetRbacSystemStatus:
    """Test get_rbac_system_status function."""

    def test_returns_status_dict(self):
        """Test returns status dictionary."""
        result = get_rbac_system_status()

        assert result["system"] == "RBAC FastAPI"
        assert result["status"] == "healthy"
        assert "features" in result
        assert "cache_stats" in result

    def test_includes_permission_matrix_info(self):
        """Test includes permission matrix info."""
        result = get_rbac_system_status()

        assert "permission_matrix" in result
        assert result["permission_matrix"]["total_roles"] == 3

    def test_cache_stats_structure(self):
        """Test cache stats structure."""
        result = get_rbac_system_status()
        stats = result["cache_stats"]

        assert "hits" in stats
        assert "misses" in stats
        assert "current_size" in stats
        assert "max_size" in stats
        assert "hit_rate" in stats

    def test_features_are_enabled(self):
        """Test features are properly configured."""
        result = get_rbac_system_status()
        features = result["features"]

        assert features["role_caching"] is True
        assert features["permission_matrix"] is True
        assert features["unified_dependencies"] is True
        assert features["backwards_compatible"] is True

    def test_permission_matrix_totals(self):
        """Test permission matrix totals are calculated correctly."""
        result = get_rbac_system_status()
        matrix_stats = result["permission_matrix"]

        assert matrix_stats["total_resources"] >= 3
        assert matrix_stats["total_permissions"] > 0


class TestGetUserRoles:
    """Test get_user_roles function."""

    @patch("app.core.rbac_fastapi.get_user_roles_cached")
    def test_returns_list_of_roles(self, mock_cached):
        """Test returns list from cached tuple."""
        mock_cached.return_value = ("admin", "user")
        result = get_user_roles("test-id")
        assert result == ["admin", "user"]
        assert isinstance(result, list)

    @patch("app.core.rbac_fastapi.get_user_roles_cached")
    def test_converts_user_id_to_string(self, mock_cached):
        """Test user_id is converted to string."""
        from uuid import uuid4

        mock_cached.return_value = ()

        user_id = uuid4()
        get_user_roles(user_id)
        mock_cached.assert_called_once_with(str(user_id))


class TestRequireRbacAdmin:
    """Test require_rbac_admin function."""

    def test_returns_callable(self):
        """Test require_rbac_admin returns callable."""
        result = require_rbac_admin()
        assert callable(result)

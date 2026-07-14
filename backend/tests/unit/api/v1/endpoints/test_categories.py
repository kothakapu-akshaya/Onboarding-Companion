"""Tests for categories API endpoint."""

from unittest.mock import Mock, patch


class TestCategoriesEndpoint:
    """Test cases for categories endpoint."""

    def test_router_exists(self):
        """Test categories router exists."""
        from app.api.v1.endpoints.categories import router

        assert router is not None

    def test_is_user_admin_function(self):
        """Test is_user_admin function."""
        from app.api.v1.endpoints.categories import is_user_admin

        mock_user = Mock()
        mock_user.id = "test-user-id"

        with patch(
            "app.api.v1.endpoints.categories.get_user_roles",
            return_value=["admin"],
        ):
            result = is_user_admin(mock_user)
            assert result is True

    def test_is_user_admin_false(self):
        """Test is_user_admin returns False for non-admin."""
        from app.api.v1.endpoints.categories import is_user_admin

        mock_user = Mock()
        mock_user.id = "test-user-id"

        with patch(
            "app.api.v1.endpoints.categories.get_user_roles",
            return_value=["user"],
        ):
            result = is_user_admin(mock_user)
            assert result is False

    def test_category_model(self):
        """Test Category model exists."""
        from app.models.category import Category

        assert Category is not None

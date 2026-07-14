"""Tests for roles API endpoint."""

from app.models.role import RoleEnum


class TestRolesEndpoint:
    """Test cases for roles endpoint."""

    def test_role_router_exists(self):
        """Test role router exists."""
        from app.api.v1.endpoints.roles import router

        assert router is not None

    def test_role_read_schema(self):
        """Test RoleRead schema."""
        from app.schemas import RoleRead

        role = RoleRead(id=1, name=RoleEnum.user)
        assert role.id == 1
        assert role.name == RoleEnum.user

    def test_role_create_schema(self):
        """Test RoleCreate schema."""
        from app.schemas import RoleCreate

        role = RoleCreate(name=RoleEnum.admin)
        assert role.name == RoleEnum.admin

    def test_role_enum_values(self):
        """Test RoleEnum has expected values."""
        assert RoleEnum.admin is not None
        assert RoleEnum.user is not None
        assert RoleEnum.reviewer is not None

    def test_role_read_with_optional_fields(self):
        """Test RoleRead with optional description."""
        from app.schemas import RoleRead

        role = RoleRead(id=1, name=RoleEnum.user)
        assert hasattr(role, "id")
        assert hasattr(role, "name")

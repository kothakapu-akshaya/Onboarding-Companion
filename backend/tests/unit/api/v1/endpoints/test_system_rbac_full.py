"""Tests for app/api/v1/endpoints/system_rbac.py.

Missing lines: 17, 27-38
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest


class TestGetRbacStatus:
    """Tests for get_rbac_status endpoint - lines 11-17."""

    @pytest.mark.asyncio
    async def test_get_rbac_status_returns_status(self):
        """Test get_rbac_status returns system status - line 17."""
        from app.api.v1.endpoints.system_rbac import get_rbac_status

        mock_user = Mock()
        mock_user.id = uuid4()

        with patch(
            "app.api.v1.endpoints.system_rbac.get_rbac_system_status"
        ) as mock_status:
            mock_status.return_value = {
                "enabled": True,
                "cache_stats": {"size": 0},
            }
            result = await get_rbac_status(current_user=mock_user)
            assert result["enabled"] is True


class TestClearRbacCache:
    """Tests for clear_rbac_cache endpoint - lines 20-42."""

    @pytest.mark.asyncio
    async def test_clear_rbac_cache_returns_message(self):
        """Test clear_rbac_cache clears cache - lines 27-38."""
        from app.api.v1.endpoints.system_rbac import clear_rbac_cache

        mock_user = Mock()
        mock_user.id = uuid4()

        mock_status_before = {"cache_stats": {"size": 10}}
        mock_status_after = {"cache_stats": {"size": 0}}

        with patch(
            "app.api.v1.endpoints.system_rbac.get_rbac_system_status"
        ) as mock_status:
            with patch("app.core.rbac_fastapi.clear_role_cache") as mock_clear:
                mock_status.side_effect = [
                    mock_status_before,
                    mock_status_after,
                ]
                result = await clear_rbac_cache(current_user=mock_user)
                assert "message" in result
                assert result["cache_before"]["size"] == 10
                assert result["cache_after"]["size"] == 0
                mock_clear.assert_called_once()

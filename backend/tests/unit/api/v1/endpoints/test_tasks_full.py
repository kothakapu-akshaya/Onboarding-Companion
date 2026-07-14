"""Tests for app/api/v1/endpoints/tasks.py.

Missing lines: 22-32
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest


class TestExportUserDataEndpoint:
    """Tests for export_user_data_endpoint - lines 17-32."""

    @pytest.mark.asyncio
    async def test_export_user_data_success(self):
        """Test export_user_data_endpoint returns task response.

        - lines 22-30.
        """
        from app.api.v1.endpoints.tasks import export_user_data_endpoint

        mock_user = Mock()
        mock_user.id = uuid4()

        mock_task = Mock()
        mock_task.id = "task-123"

        with patch(
            "app.api.v1.endpoints.tasks.export_user_data"
        ) as mock_export:
            mock_export.delay.return_value = mock_task
            result = await export_user_data_endpoint(
                export_format="json", current_user=mock_user
            )
            assert result.task_id == "task-123"
            assert result.task_name == "export_user_data"

    @pytest.mark.asyncio
    async def test_export_user_data_raises_http_exception(self):
        """Test export_user_data_endpoint raises 500 on error - lines 31-32."""
        from fastapi import HTTPException

        from app.api.v1.endpoints.tasks import export_user_data_endpoint

        mock_user = Mock()
        mock_user.id = uuid4()

        with patch(
            "app.api.v1.endpoints.tasks.export_user_data"
        ) as mock_export:
            mock_export.delay.side_effect = Exception("Celery error")

            with pytest.raises(HTTPException) as exc_info:
                await export_user_data_endpoint(
                    export_format="json", current_user=mock_user
                )
            assert exc_info.value.status_code == 500

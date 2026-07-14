"""Tests for tasks API endpoint."""


class TestTasksEndpoint:
    """Test cases for tasks endpoint."""

    def test_tasks_router_exists(self):
        """Test tasks router exists."""
        from app.api.v1.endpoints.tasks import router

        assert router is not None

    def test_task_response_schema(self):
        """Test TaskResponse schema."""
        from app.schemas.task import TaskResponse

        task = TaskResponse(
            task_id="test-task-id",
            task_name="export_user_data",
            status="PENDING",
            message="Data export started",
        )
        assert task.task_id == "test-task-id"
        assert task.task_name == "export_user_data"
        assert task.status == "PENDING"

    def test_task_status_response_schema(self):
        """Test TaskStatusResponse schema with result."""
        from app.schemas.task import TaskStatusResponse

        task = TaskStatusResponse(
            task_id="test-task-id",
            status="SUCCESS",
            result={"url": "https://example.com/export.zip"},
        )
        assert task.status == "SUCCESS"
        assert task.result is not None

    def test_task_info_schema(self):
        """Test TaskInfo schema."""
        from app.schemas.task import TaskInfo

        task = TaskInfo(task_id="test-task-id", task_name="export_user_data")
        assert task.task_id == "test-task-id"
        assert task.task_name == "export_user_data"
        assert task.args == []
        assert task.kwargs == {}

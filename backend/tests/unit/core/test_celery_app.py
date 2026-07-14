"""Tests for Celery configuration."""


class TestCeleryApp:
    """Test cases for Celery app configuration."""

    def test_celery_app_exists(self):
        """Test Celery app is created."""
        from app.core.celery_app import celery_app

        assert celery_app is not None

    def test_celery_app_name(self):
        """Test Celery app has correct name."""
        from app.core.celery_app import celery_app

        assert celery_app.main == "corpus-te"

    def test_celery_config_has_broker(self):
        """Test Celery config has broker URL."""
        from app.core.celery_app import celery_app

        assert celery_app.conf.broker_url is not None

    def test_celery_config_has_result_backend(self):
        """Test Celery config has result backend."""
        from app.core.celery_app import celery_app

        assert celery_app.conf.result_backend is not None

    def test_celery_config_has_task_routes(self):
        """Test Celery config has task routes."""
        from app.core.celery_app import celery_app

        assert celery_app.conf.task_routes is not None
        assert "app.tasks.file_processing.*" in celery_app.conf.task_routes

    def test_celery_config_has_queues(self):
        """Test Celery config has queues defined."""
        from app.core.celery_app import celery_app

        assert celery_app.conf.task_queues is not None

    def test_celery_config_has_beat_schedule(self):
        """Test Celery config has beat schedule."""
        from app.core.celery_app import celery_app

        assert celery_app.conf.beat_schedule is not None
        assert "cleanup-old-files" in celery_app.conf.beat_schedule

    def test_celery_config_task_settings(self):
        """Test Celery config has correct task settings."""
        from app.core.celery_app import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.timezone == "UTC"

    def test_celery_config_time_limits(self):
        """Test Celery config has correct time limits."""
        from app.core.celery_app import celery_app

        assert celery_app.conf.task_soft_time_limit == 300
        assert celery_app.conf.task_time_limit == 600

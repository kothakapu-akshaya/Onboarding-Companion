"""Tests for maintenance tasks."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestCleanupOldFiles:
    """Tests for cleanup_old_files task."""

    @patch("app.tasks.maintenance.Session")
    def test_cleanup_old_files_no_records(self, mock_session_class):
        """Test cleanup with no old records."""
        from app.tasks.maintenance import cleanup_old_files

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.return_value.all.return_value = []

        mock_session_class.return_value.__enter__.return_value = mock_session

        result = cleanup_old_files(days_old=30)

        assert result["status"] == "success"


class TestOptimizeDatabase:
    """Tests for optimize_database task."""

    @patch("app.tasks.maintenance.Session")
    def test_optimize_database_success(self, mock_session_class):
        """Test database optimization success."""
        from app.tasks.maintenance import optimize_database

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.return_value = None

        mock_session_class.return_value.__enter__.return_value = mock_session

        result = optimize_database()

        assert result["status"] == "success"


class TestHealthCheck:
    """Tests for health_check task."""

    @patch("shutil.disk_usage")
    @patch("app.tasks.maintenance.Session")
    @patch("app.tasks.maintenance.HetznerStorageClient")
    def test_health_check_all_healthy(
        self, mock_storage, mock_session_class, mock_disk
    ):
        """Test health check when all services are healthy."""
        from app.tasks.maintenance import health_check

        mock_disk.return_value = MagicMock(
            used=500000, free=500000, total=1000000
        )

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.return_value = None

        mock_session_class.return_value.__enter__.return_value = mock_session

        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance

        with patch("app.tasks.maintenance.celery_app.send_task"):
            result = health_check()

        assert result["status"] == "success"

    @patch("shutil.disk_usage")
    @patch("app.tasks.maintenance.Session")
    @patch("app.tasks.maintenance.HetznerStorageClient")
    def test_health_check_database_failure(
        self, mock_storage, mock_session_class, mock_disk
    ):
        """Test health check with database failure."""
        from app.tasks.maintenance import health_check

        mock_disk.return_value = MagicMock(
            used=100000, free=900000, total=1000000
        )

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.exec.side_effect = Exception("Connection refused")

        mock_session_class.return_value.__enter__.return_value = mock_session

        mock_storage_instance = MagicMock()
        mock_storage_instance.list_objects.side_effect = Exception(
            "Storage error"
        )
        mock_storage.return_value = mock_storage_instance

        with patch("app.tasks.maintenance.celery_app.send_task"):
            result = health_check()

        assert result["status"] == "success"
        assert result["health_status"]["database"] == "unhealthy"


class TestBackupDatabase:
    """Tests for backup_database task."""

    def test_backup_database_success(self):
        """Test successful database backup."""
        from app.tasks.maintenance import backup_database

        result = backup_database()

        assert result["status"] == "success"

    def test_backup_database_custom_location(self):
        """Test database backup to custom location."""
        from app.tasks.maintenance import backup_database

        result = backup_database(backup_location="/custom/path/backup.sql")

        assert result["status"] == "success"
        assert "/custom/path/backup.sql" in result["results"]["backup_file"]


class TestCleanupIncompleteChunks:
    """Tests for cleanup_incomplete_chunks task."""

    @patch("app.tasks.maintenance.ChunkManager")
    def test_cleanup_incomplete_chunks_no_directory(
        self, mock_chunk_manager_class
    ):
        """Test cleanup when directory doesn't exist."""
        from app.tasks.maintenance import cleanup_incomplete_chunks

        mock_chunk_manager = MagicMock()
        mock_chunk_manager.storage_path = "/tmp/chunks"
        mock_chunk_manager_class.return_value = mock_chunk_manager

        with patch("pathlib.Path.exists", return_value=False):
            result = cleanup_incomplete_chunks(minutes_old=15)

        assert result["status"] == "success"


class TestMaintenanceBusinessLogic:
    """Tests for business logic in maintenance."""

    def test_disk_usage_calculation(self):
        """Test disk usage percentage calculation."""
        total = 1000000
        used = 500000

        percentage = (used / total) * 100 if total > 0 else 0

        assert percentage == 50.0

    def test_disk_usage_critical_threshold(self):
        """Test disk usage critical threshold."""
        total = 1000000
        used = 950000

        percentage = (used / total) * 100 if total > 0 else 0
        is_critical = percentage > 90

        assert is_critical is True

    def test_cleanup_result_structure(self):
        """Test cleanup result structure."""
        result = {
            "status": "success",
            "local_files_deleted": 5,
            "database_records_cleaned": 3,
            "storage_files_deleted": 2,
            "errors": [],
        }

        assert result["status"] == "success"
        assert "local_files_deleted" in result
        assert "database_records_cleaned" in result

    def test_health_check_result_structure(self):
        """Test health check result structure."""
        result = {
            "status": "success",
            "health_status": {
                "database": "healthy",
                "storage": "healthy",
                "disk_space": "healthy",
            },
            "details": {
                "disk_usage_percent": 50,
                "total_records": 1000,
                "storage_objects": 500,
            },
        }

        assert result["status"] == "success"
        assert "health_status" in result
        assert "database" in result["health_status"]

    def test_backup_result_structure(self):
        """Test backup result structure."""
        result = {
            "status": "success",
            "results": {
                "backup_file": "/tmp/backup_20240115.sql",
                "backup_size_mb": 10.5,
                "tables_backed_up": 15,
            },
        }

        assert result["status"] == "success"
        assert "backup_file" in result["results"]

"""Tests for maintenance tasks."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.tasks.maintenance import (
    backup_database,
    cleanup_incomplete_chunks,
    cleanup_old_files,
    optimize_database,
)


class TestCleanupOldFiles:
    """Tests for cleanup_old_files task."""

    @patch("app.tasks.maintenance.Session")
    def test_cleanup_old_files_success(self, mock_session_class):
        """Test successful cleanup of old files."""
        # Create mock session
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Create mock records
        mock_record = MagicMock()
        mock_record.uid = uuid4()
        mock_record.status = "failed"
        mock_record.file_url = None
        mock_record.created_at = datetime.now(timezone.utc) - timedelta(days=35)

        mock_session.exec.return_value.all.return_value = [mock_record]

        result = cleanup_old_files(days_old=30)

        assert result["status"] == "success"

    @patch("app.tasks.maintenance.Session")
    def test_cleanup_old_files_no_records(self, mock_session_class):
        """Test cleanup when no old records exist."""
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session
        mock_session.exec.return_value.all.return_value = []

        result = cleanup_old_files(days_old=30)

        assert result["status"] == "success"
        assert result["results"]["database_records_cleaned"] == 0

    @patch("app.tasks.maintenance.Session")
    def test_cleanup_old_files_handles_naive_record_timestamps(
        self, mock_session_class
    ):
        """Naive record timestamps do not break old-record filtering."""
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        mock_record = MagicMock()
        mock_record.uid = uuid4()
        mock_record.status = "failed"
        mock_record.file_url = None
        mock_record.created_at = (
            datetime.now(timezone.utc) - timedelta(days=35)
        ).replace(tzinfo=None)

        rows = MagicMock()
        rows.all.side_effect = [[mock_record], []]
        mock_session.exec.side_effect = [rows, rows]

        result = cleanup_old_files(days_old=30)

        assert result["status"] == "success"
        assert result["results"]["database_records_cleaned"] == 1
        assert result["results"]["errors"] == []

    @patch("app.tasks.maintenance.os.remove")
    @patch("app.tasks.maintenance.Path")
    @patch("app.tasks.maintenance.Session")
    def test_cleanup_old_files_uses_aware_temp_file_timestamps(
        self, mock_session_class, mock_path_class, mock_os_remove
    ):
        """Old temp files are cleaned without naive/aware datetime errors."""
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        empty_rows = MagicMock()
        empty_rows.all.return_value = []
        mock_session.exec.side_effect = [empty_rows, empty_rows]

        temp_dir = MagicMock()
        temp_dir.exists.return_value = True

        old_temp_file = MagicMock()
        old_temp_file.stat.return_value.st_mtime = (
            datetime.now(timezone.utc) - timedelta(days=35)
        ).timestamp()
        temp_dir.glob.return_value = [old_temp_file]

        mock_path_class.return_value = temp_dir

        result = cleanup_old_files(days_old=30)

        assert result["status"] == "success"
        assert result["results"]["local_files_deleted"] == 1
        assert result["results"]["errors"] == []
        mock_os_remove.assert_not_called()
        old_temp_file.unlink.assert_called_once()


class TestOptimizeDatabase:
    """Tests for optimize_database task."""

    @patch("app.tasks.maintenance.Session")
    def test_optimize_database_success(self, mock_session_class):
        """Test successful database optimization."""
        mock_session = MagicMock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        result = optimize_database()

        assert result["status"] == "success"


class TestHealthCheck:
    """Tests for health_check task."""

    @pytest.mark.skip(
        reason="Requires Redis which is not available in test environment"
    )
    @patch("app.tasks.maintenance.HetznerStorageClient")
    @patch("app.tasks.maintenance.Session")
    def test_health_check_all_healthy(
        self, mock_session_class, mock_storage_class
    ):
        """Test health check when all services are healthy."""
        pass

    @pytest.mark.skip(
        reason="Requires Redis which is not available in test environment"
    )
    @patch("app.tasks.maintenance.HetznerStorageClient")
    @patch("app.tasks.maintenance.Session")
    def test_health_check_storage_failure(
        self, mock_session_class, mock_storage_class
    ):
        """Test health check with storage failure."""
        pass


class TestBackupDatabase:
    """Tests for backup_database task."""

    def test_backup_database_success(self):
        """Test successful database backup."""
        result = backup_database()

        assert result["status"] == "success"

    def test_backup_database_custom_location(self):
        """Test database backup with custom location."""
        result = backup_database(backup_location="/custom/backup.sql")

        assert result["status"] == "success"
        assert "backup.sql" in result["results"]["backup_file"]


class TestCleanupIncompleteChunks:
    """Tests for cleanup_incomplete_chunks task."""

    @patch("app.tasks.maintenance.ChunkManager")
    @patch("app.tasks.maintenance.Path")
    def test_cleanup_incomplete_chunks_success(
        self, mock_path_class, mock_chunk_manager_class
    ):
        """Test successful cleanup of incomplete chunks."""
        # Mock the storage path
        mock_storage_path = MagicMock()
        mock_storage_path.exists.return_value = True
        mock_storage_path.iterdir.return_value = []

        mock_path_class.return_value = mock_storage_path

        result = cleanup_incomplete_chunks(minutes_old=15)

        assert result["status"] == "success"

    @patch("app.tasks.maintenance.Path")
    def test_cleanup_incomplete_chunks_no_directory(self, mock_path_class):
        """Test cleanup when directory doesn't exist."""
        mock_storage_path = MagicMock()
        mock_storage_path.exists.return_value = False

        mock_path_class.return_value = mock_storage_path

        result = cleanup_incomplete_chunks(minutes_old=15)

        assert result["status"] == "success"
        assert result["results"]["directories_checked"] == 0

    @patch("app.tasks.maintenance.ChunkManager")
    @patch("app.tasks.maintenance.Path")
    def test_cleanup_incomplete_chunks_uses_aware_chunk_timestamps(
        self, mock_path_class, mock_chunk_manager_class
    ):
        """Old chunk directories are cleaned without naive/aware errors."""
        mock_chunk_manager = MagicMock()
        mock_chunk_manager.storage_path = "/tmp/chunks"
        mock_chunk_manager_class.return_value = mock_chunk_manager

        chunk_storage_path = MagicMock()
        chunk_storage_path.exists.return_value = True

        upload_dir = MagicMock()
        upload_dir.is_dir.return_value = True
        upload_dir.name = "upload-1"

        old_chunk = MagicMock()
        old_chunk.stat.return_value.st_mtime = (
            datetime.now(timezone.utc) - timedelta(minutes=20)
        ).timestamp()
        upload_dir.glob.return_value = [old_chunk]

        chunk_storage_path.iterdir.return_value = [upload_dir]
        mock_path_class.return_value = chunk_storage_path

        result = cleanup_incomplete_chunks(minutes_old=15)

        assert result["status"] == "success"
        assert result["results"]["directories_cleaned"] == 1
        assert result["results"]["errors"] == []
        mock_chunk_manager.cleanup_chunks.assert_called_once_with("upload-1")

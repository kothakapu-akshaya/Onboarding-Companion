"""Tests for the chunk manager utility."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.utils.chunk_manager import ChunkManager


@pytest.fixture(autouse=True)
def mock_logger():
    """Provide a mocked logger."""
    with patch("app.utils.chunk_manager.logger") as mock_logger:
        yield mock_logger


@pytest.fixture
def chunk_manager(tmp_path):
    """Chunk manager."""
    storage_path = tmp_path / "chunks"
    staging_path = tmp_path / "staging"
    storage_path.mkdir(parents=True, exist_ok=True)
    staging_path.mkdir(parents=True, exist_ok=True)

    manager = ChunkManager(str(storage_path))
    manager.staging_path = staging_path
    yield manager


class TestChunkManagerInit:
    """Tests for ChunkManagerInit."""

    @patch("app.utils.chunk_manager.Path")
    def test_init_default_paths(self, MockPath, mock_logger):
        """Test init default paths."""
        mock_storage_path = Mock()
        mock_staging_path = Mock()
        MockPath.side_effect = [mock_storage_path, mock_staging_path]

        manager = ChunkManager()

        assert manager.storage_path == mock_storage_path
        assert manager.staging_path == mock_staging_path
        mock_storage_path.mkdir.assert_called_once_with(
            parents=True, exist_ok=True
        )
        mock_staging_path.mkdir.assert_called_once_with(
            parents=True, exist_ok=True
        )
        mock_logger.info.assert_called_once()

    @patch("app.utils.chunk_manager.Path")
    def test_init_custom_paths(self, MockPath, mock_logger):
        """Test init custom paths."""
        mock_storage_path = Mock()
        mock_staging_path = Mock()
        MockPath.side_effect = [mock_storage_path, mock_staging_path]

        manager = ChunkManager("/custom/chunks")

        assert manager.storage_path == mock_storage_path
        assert manager.staging_path == mock_staging_path
        mock_storage_path.mkdir.assert_called_once_with(
            parents=True, exist_ok=True
        )
        mock_staging_path.mkdir.assert_called_once_with(
            parents=True, exist_ok=True
        )
        mock_logger.info.assert_called_once()


class TestChunkManagerSaveChunk:
    """Tests for ChunkManagerSaveChunk."""

    def test_save_chunk_success(self, chunk_manager, mock_logger, tmp_path):
        """Test save chunk success."""
        upload_uuid = "test_uuid"
        chunk_index = 0
        total_chunks = 2
        chunk_data = b"chunk_data_0"

        result = chunk_manager.save_chunk(
            upload_uuid, chunk_index, total_chunks, chunk_data
        )
        assert result is True

        upload_dir = chunk_manager.storage_path / upload_uuid
        expected_chunk_path = (
            upload_dir / f"chunk_{chunk_index}_{total_chunks}.chunk"
        )
        assert expected_chunk_path.exists()
        assert expected_chunk_path.read_bytes() == chunk_data
        mock_logger.info.assert_called()

    def test_save_chunk_multiple_chunks(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test save chunk multiple chunks."""
        upload_uuid = "test_uuid"
        total_chunks = 3

        for i in range(total_chunks):
            result = chunk_manager.save_chunk(
                upload_uuid, i, total_chunks, f"chunk_data_{i}".encode()
            )
            assert result is True

        upload_dir = chunk_manager.storage_path / upload_uuid
        assert len(list(upload_dir.glob("*.chunk"))) == total_chunks

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_save_chunk_write_error(
        self, mock_file, chunk_manager, mock_logger, tmp_path
    ):
        """Test save chunk write error."""
        upload_uuid = "test_uuid"
        chunk_index = 0
        total_chunks = 2
        chunk_data = b"chunk_data_0"

        result = chunk_manager.save_chunk(
            upload_uuid, chunk_index, total_chunks, chunk_data
        )
        assert result is False
        mock_logger.error.assert_called()

    @patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied"))
    def test_save_chunk_mkdir_error(
        self, mock_mkdir, chunk_manager, mock_logger, tmp_path
    ):
        """Test save chunk mkdir error."""
        upload_uuid = "test_uuid"
        chunk_index = 0
        total_chunks = 2
        chunk_data = b"chunk_data_0"

        result = chunk_manager.save_chunk(
            upload_uuid, chunk_index, total_chunks, chunk_data
        )
        assert result is False
        mock_logger.error.assert_called()


class TestChunkManagerCombineChunks:
    """Tests for ChunkManagerCombineChunks."""

    def test_combine_chunks_success(self, chunk_manager, mock_logger, tmp_path):
        """Test combine chunks success."""
        upload_uuid = "test_uuid"
        filename = "final_file.txt"

        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_2.chunk").write_bytes(b"data1")
        (chunk_dir / "chunk_1_2.chunk").write_bytes(b"data2")

        result = chunk_manager.combine_chunks(upload_uuid, filename)

        assert result is not None
        assert os.path.exists(result)
        assert open(result, "rb").read() == b"data1data2"
        mock_logger.info.assert_called()

    def test_combine_chunks_upload_dir_not_found(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test combine chunks upload dir not found."""
        upload_uuid = "non_existent_uuid"
        filename = "final_file.txt"

        result = chunk_manager.combine_chunks(upload_uuid, filename)
        assert result is None
        mock_logger.error.assert_called_once()

    def test_combine_chunks_no_valid_chunks(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test combine chunks no valid chunks."""
        upload_uuid = "test_uuid"
        filename = "final_file.txt"

        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "invalid.chunk").write_bytes(b"data")

        result = chunk_manager.combine_chunks(upload_uuid, filename)
        assert result is None
        mock_logger.error.assert_called_once()

    def test_combine_chunks_missing_chunks(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test combine chunks missing chunks."""
        upload_uuid = "test_uuid"
        filename = "final_file.txt"

        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_2.chunk").write_bytes(b"data1")

        result = chunk_manager.combine_chunks(upload_uuid, filename)
        assert result is None
        mock_logger.error.assert_called()

    @patch("builtins.open", side_effect=OSError("Read error"))
    def test_combine_chunks_read_error(
        self, mock_file, chunk_manager, mock_logger, tmp_path
    ):
        """Test combine chunks read error."""
        upload_uuid = "test_uuid"
        filename = "final_file.txt"

        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_1.chunk").write_bytes(b"data1")

        result = chunk_manager.combine_chunks(upload_uuid, filename)
        assert result is None
        mock_logger.error.assert_called()

    def test_combine_chunks_with_extension(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test combine chunks with extension."""
        upload_uuid = "test_uuid"
        filename = "video.mp4"

        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_1.chunk").write_bytes(b"videodata")

        result = chunk_manager.combine_chunks(upload_uuid, filename)

        assert result is not None
        assert result.endswith(".mp4")

    def test_combine_chunks_invalid_filename_format(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test combine chunks invalid filename format."""
        upload_uuid = "test_uuid"
        filename = "file"

        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_1.chunk").write_bytes(b"data")

        result = chunk_manager.combine_chunks(upload_uuid, filename)

        assert result is not None


class TestChunkManagerCleanupChunks:
    """Tests for ChunkManagerCleanupChunks."""

    def test_cleanup_chunks_success(self, chunk_manager, mock_logger, tmp_path):
        """Test cleanup chunks success."""
        upload_uuid = "test_uuid"

        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)
        (chunk_dir / "chunk_0_1.chunk").write_bytes(b"data")

        result = chunk_manager.cleanup_chunks(upload_uuid)
        assert result is True
        mock_logger.info.assert_called()

    def test_cleanup_chunks_dir_not_found(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test cleanup chunks dir not found."""
        upload_uuid = "non_existent_uuid"

        result = chunk_manager.cleanup_chunks(upload_uuid)
        assert result is True
        mock_logger.warning.assert_called_once()

    def test_cleanup_chunks_actual_removal(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test cleanup chunks actual removal."""
        upload_uuid = "test_uuid"

        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)
        (chunk_dir / "chunk_0_1.chunk").write_bytes(b"data")

        assert chunk_dir.exists()

        result = chunk_manager.cleanup_chunks(upload_uuid)

        assert result is True
        assert not chunk_dir.exists()


class TestChunkManagerGetMissingChunks:
    """Tests for ChunkManagerGetMissingChunks."""

    def test_get_missing_chunks_all_missing_dir_not_found(
        self, chunk_manager, tmp_path
    ):
        """Test get missing chunks all missing dir not found."""
        missing = chunk_manager.get_missing_chunks("test_uuid", 3)
        assert missing == [0, 1, 2]

    def test_get_missing_chunks_some_missing(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test get missing chunks some missing."""
        upload_uuid = "test_uuid"
        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_3.chunk").write_bytes(b"data0")
        (chunk_dir / "chunk_2_3.chunk").write_bytes(b"data2")

        missing = chunk_manager.get_missing_chunks(upload_uuid, 3)
        assert missing == [1]
        mock_logger.info.assert_called()

    def test_get_missing_chunks_none_missing(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test get missing chunks none missing."""
        upload_uuid = "test_uuid"
        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_2.chunk").write_bytes(b"data0")
        (chunk_dir / "chunk_1_2.chunk").write_bytes(b"data1")

        missing = chunk_manager.get_missing_chunks(upload_uuid, 2)
        assert missing == []
        mock_logger.info.assert_called()

    def test_get_missing_chunks_invalid_filename(self, chunk_manager, tmp_path):
        """Test get missing chunks invalid filename."""
        upload_uuid = "test_uuid"
        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "invalid_name.chunk").write_bytes(b"data")
        (chunk_dir / "chunk_0_2.chunk").write_bytes(b"data0")

        missing = chunk_manager.get_missing_chunks(upload_uuid, 2)
        assert missing == [1]

    def test_get_missing_chunks_single_chunk(
        self, chunk_manager, mock_logger, tmp_path
    ):
        """Test get missing chunks single chunk."""
        upload_uuid = "test_uuid"
        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_1.chunk").write_bytes(b"data")

        missing = chunk_manager.get_missing_chunks(upload_uuid, 1)
        assert missing == []

    def test_get_missing_chunks_with_invalid_parts(
        self, chunk_manager, tmp_path
    ):
        """Test get missing chunks with invalid parts."""
        upload_uuid = "test_uuid"
        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_abc_2.chunk").write_bytes(b"data")

        missing = chunk_manager.get_missing_chunks(upload_uuid, 2)
        assert missing == [0, 1]


class TestChunkManagerValidateChunkSequence:
    """Tests for ChunkManagerValidateChunkSequence."""

    def test_validate_chunk_sequence_complete(self, chunk_manager, tmp_path):
        """Test validate chunk sequence complete."""
        upload_uuid = "test_uuid"
        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_2.chunk").write_bytes(b"data0")
        (chunk_dir / "chunk_1_2.chunk").write_bytes(b"data1")

        is_valid = chunk_manager.validate_chunk_sequence(upload_uuid, 2)
        assert is_valid is True

    def test_validate_chunk_sequence_incomplete(self, chunk_manager, tmp_path):
        """Test validate chunk sequence incomplete."""
        upload_uuid = "test_uuid"
        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        (chunk_dir / "chunk_0_2.chunk").write_bytes(b"data0")

        is_valid = chunk_manager.validate_chunk_sequence(upload_uuid, 2)
        assert is_valid is False

    def test_validate_chunk_sequence_no_chunks(self, chunk_manager, tmp_path):
        """Test validate chunk sequence no chunks."""
        upload_uuid = "test_uuid"

        is_valid = chunk_manager.validate_chunk_sequence(upload_uuid, 5)
        assert is_valid is False

    def test_validate_chunk_sequence_all_present(self, chunk_manager, tmp_path):
        """Test validate chunk sequence all present."""
        upload_uuid = "test_uuid"
        chunk_dir = chunk_manager.storage_path / upload_uuid
        chunk_dir.mkdir(parents=True, exist_ok=True)

        for i in range(10):
            (chunk_dir / f"chunk_{i}_10.chunk").write_bytes(f"data{i}".encode())

        is_valid = chunk_manager.validate_chunk_sequence(upload_uuid, 10)
        assert is_valid is True


class TestChunkManagerIntegration:
    """Tests for ChunkManagerIntegration."""

    def test_full_upload_workflow(self, chunk_manager, mock_logger, tmp_path):
        """Test full upload workflow."""
        upload_uuid = "workflow_test"
        total_chunks = 3

        for i in range(total_chunks):
            result = chunk_manager.save_chunk(
                upload_uuid, i, total_chunks, f"chunk_{i}".encode()
            )
            assert result is True

        missing = chunk_manager.get_missing_chunks(upload_uuid, total_chunks)
        assert missing == []

        is_valid = chunk_manager.validate_chunk_sequence(
            upload_uuid, total_chunks
        )
        assert is_valid is True

        combined = chunk_manager.combine_chunks(upload_uuid, "combined.txt")
        assert combined is not None
        assert Path(combined).read_bytes() == b"chunk_0chunk_1chunk_2"

        cleanup_result = chunk_manager.cleanup_chunks(upload_uuid)
        assert cleanup_result is True

        missing_after = chunk_manager.get_missing_chunks(
            upload_uuid, total_chunks
        )
        assert missing_after == [0, 1, 2]

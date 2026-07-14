"""Tests for the file hashing utility."""

import hashlib
from unittest.mock import Mock, mock_open, patch

import pytest

from app.utils.file_hashing import get_file_hash


# Mock logger to prevent console output during tests
@pytest.fixture(autouse=True)
def mock_logger():
    """Provide a mocked logger."""
    with patch("app.utils.file_hashing.logger") as mock_logger:
        yield mock_logger


class TestGetFileHash:
    """Tests for GetFileHash."""

    def test_get_file_hash_sha256_success(self, tmp_path):
        """Test get file hash sha256 success."""
        file_content = b"test content for hashing"
        file_path = tmp_path / "test_file.txt"
        file_path.write_bytes(file_content)

        expected_hash = hashlib.sha256(file_content).hexdigest()
        actual_hash = get_file_hash(str(file_path), "sha256")
        assert actual_hash == expected_hash

    def test_get_file_hash_md5_success(self, tmp_path):
        """Test get file hash md5 success."""
        file_content = b"another test content"
        file_path = tmp_path / "another_file.txt"
        file_path.write_bytes(file_content)

        expected_hash = hashlib.md5(file_content).hexdigest()
        actual_hash = get_file_hash(str(file_path), "md5")
        assert actual_hash == expected_hash

    def test_get_file_hash_file_not_found(self, mock_logger):
        """Test get file hash file not found."""
        result = get_file_hash("non_existent_file.txt", "sha256")
        assert result is None
        mock_logger.error.assert_called_once_with(
            "File not found: non_existent_file.txt"
        )

    def test_get_file_hash_unsupported_algorithm(self, mock_logger):
        """Test get file hash unsupported algorithm."""
        with pytest.raises(
            ValueError, match="unsupported hash type invalid_algo"
        ):
            get_file_hash("dummy.txt", "invalid_algo")
        mock_logger.error.assert_called_once_with(
            "Unsupported hashing algorithm: invalid_algo"
        )

    @patch("builtins.open", new_callable=mock_open)
    def test_get_file_hash_read_error(self, mock_file, mock_logger):
        """Test get file hash read error."""
        mock_file.side_effect = Exception("Permission denied")
        result = get_file_hash("test_file.txt", "sha256")
        assert result is None
        mock_logger.error.assert_called_once_with(
            "Error hashing file test_file.txt: Permission denied"
        )

    @patch("builtins.open", new_callable=mock_open)
    def test_get_file_hash_large_file_chunks(self, mock_file, mock_logger):
        """Test get file hash large file chunks."""
        # Simulate reading in chunks
        mock_file.return_value.read.side_effect = [
            b"chunk1",
            b"chunk2",
            b"chunk3",
            b"",
        ]

        # Mock hashlib.new to get a mock hasher object
        with patch("app.utils.file_hashing.hashlib.new") as mock_hashlib_new:
            mock_hasher = Mock()
            mock_hashlib_new.return_value = mock_hasher
            mock_hasher.hexdigest.return_value = "mock_hexdigest"

            result = get_file_hash("large_file.bin", "sha256")
            assert result == "mock_hexdigest"
            mock_hasher.update.assert_any_call(b"chunk1")
            mock_hasher.update.assert_any_call(b"chunk2")
            mock_hasher.update.assert_any_call(b"chunk3")
            assert mock_hasher.update.call_count == 3

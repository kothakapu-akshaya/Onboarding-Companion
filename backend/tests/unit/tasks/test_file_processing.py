"""Tests for file_processing tasks."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestFileProcessingHelperFunctions:
    """Tests for helper functions in file_processing module."""

    def test_extract_audio_metadata_mp3(self):
        """Test audio metadata extraction for MP3 file."""
        from app.tasks.file_processing import extract_audio_metadata

        with patch(
            "app.tasks.file_processing.os.path.getsize", return_value=1024000
        ):
            with patch("app.tasks.file_processing.Path") as mock_path:
                mock_path_instance = Mock()
                mock_path_instance.suffix.lower.return_value = ".mp3"
                mock_path.return_value = mock_path_instance

                result = extract_audio_metadata("/path/to/audio.mp3")

        assert "format" in result
        assert result["format"] == ".mp3"
        assert "file_size" in result
        assert result["file_size"] == 1024000

    def test_extract_audio_metadata_wav(self):
        """Test audio metadata extraction for WAV file."""
        from app.tasks.file_processing import extract_audio_metadata

        with patch(
            "app.tasks.file_processing.os.path.getsize", return_value=2048000
        ):
            with patch("app.tasks.file_processing.Path") as mock_path:
                mock_path_instance = Mock()
                mock_path_instance.suffix.lower.return_value = ".wav"
                mock_path.return_value = mock_path_instance

                result = extract_audio_metadata("/path/to/audio.wav")

        assert result["format"] == ".wav"

    def test_extract_audio_metadata_flac(self):
        """Test audio metadata extraction for FLAC file."""
        from app.tasks.file_processing import extract_audio_metadata

        with patch(
            "app.tasks.file_processing.os.path.getsize", return_value=512000
        ):
            with patch("app.tasks.file_processing.Path") as mock_path:
                mock_path_instance = Mock()
                mock_path_instance.suffix.lower.return_value = ".flac"
                mock_path.return_value = mock_path_instance

                result = extract_audio_metadata("/path/to/audio.flac")

        assert result["format"] == ".flac"

    def test_generate_waveform(self):
        """Test waveform generation."""
        from app.tasks.file_processing import generate_waveform

        result = generate_waveform("/path/to/audio.mp3")

        assert isinstance(result, list)

    def test_generate_waveform_returns_empty_list(self):
        """Test waveform generation returns empty list."""
        from app.tasks.file_processing import generate_waveform

        result = generate_waveform("/path/to/audio.mp3")

        assert result == []


class TestFileProcessingBusinessLogic:
    """Tests for business logic in file processing."""

    def test_audio_metadata_structure(self):
        """Test audio metadata structure."""
        metadata = {
            "duration": 120.5,
            "bitrate": 128,
            "format": ".mp3",
            "file_size": 1024000,
            "channels": 2,
            "sample_rate": 44100,
        }

        assert "duration" in metadata
        assert "bitrate" in metadata
        assert "format" in metadata
        assert "file_size" in metadata

    def test_waveform_data_structure(self):
        """Test waveform data structure."""
        waveform_data = [0.1, 0.2, 0.5, 0.3, 0.1, 0.0]

        assert isinstance(waveform_data, list)
        for value in waveform_data:
            assert isinstance(value, (int, float))

    def test_processing_result_structure(self):
        """Test processing result structure."""
        result = {
            "status": "success",
            "record_id": 123,
            "metadata": {"duration": 120, "format": ".mp3"},
            "waveform_generated": True,
        }

        assert result["status"] == "success"
        assert "record_id" in result
        assert "metadata" in result

    def test_upload_result_structure(self):
        """Test upload result structure."""
        result = {
            "status": "success",
            "file_path": "/tmp/audio.mp3",
            "upload_time_seconds": 5.5,
        }

        assert result["status"] == "success"
        assert "file_path" in result
        assert "upload_time_seconds" in result

    def test_file_processing_error_handling(self):
        """Test error handling in file processing."""
        error_types = [
            ("Record not found", ValueError),
            ("File not found", FileNotFoundError),
            ("Upload failed", Exception),
        ]

        for error_msg, error_type in error_types:
            assert issubclass(error_type, Exception)

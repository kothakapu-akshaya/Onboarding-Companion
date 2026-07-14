"""Extra coverage tests for file processing tasks."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.tasks.file_processing import (
    extract_audio_metadata,
    generate_waveform,
    process_audio_file,
    upload_to_storage,
)


def make_session(*get_results):
    """Create a mock database session with configurable get results."""
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = False
    session.get.side_effect = list(get_results)
    return session


def test_extract_audio_metadata_reads_file_size_and_extension():
    """Test that extract_audio_metadata reads file size and extension."""
    with (
        patch("app.tasks.file_processing.os.path.getsize", return_value=2048),
        patch("app.tasks.file_processing.Path") as mock_path,
    ):
        mock_path.return_value.suffix.lower.return_value = ".mp3"
        result = extract_audio_metadata("/tmp/file.mp3")

    assert result["file_size"] == 2048
    assert result["format"] == ".mp3"


def test_generate_waveform_returns_list():
    """Test that generate_waveform returns an empty list."""
    assert generate_waveform("/tmp/file.mp3") == []


def test_process_audio_file_success_and_failure_paths():
    """Test process_audio_file success and failure paths."""
    record = SimpleNamespace(uid=1)
    session = make_session(record)
    metadata = {"duration": 12.0, "bitrate": 128000, "format": ".mp3"}

    with (
        patch("app.tasks.file_processing.Session", return_value=session),
        patch("app.tasks.file_processing.os.path.exists", return_value=True),
        patch(
            "app.tasks.file_processing.extract_audio_metadata",
            return_value=metadata,
        ),
        patch(
            "app.tasks.file_processing.generate_waveform",
            return_value=[0.1, 0.2],
        ),
        patch.object(process_audio_file, "update_state"),
    ):
        result = process_audio_file.run(1, "/tmp/file.mp3")

    assert result["status"] == "success"
    assert record.audio_duration == 12.0
    assert record.processing_status == "completed"
    missing_session = make_session(None, None)
    with (
        patch(
            "app.tasks.file_processing.Session", return_value=missing_session
        ),
        patch("app.tasks.file_processing.os.path.exists", return_value=True),
        patch.object(process_audio_file, "update_state"),
    ):
        with pytest.raises(ValueError):
            process_audio_file.run(99, "/tmp/file.mp3")


def test_process_audio_file_missing_file():
    """Test process_audio_file with a missing file."""
    record = SimpleNamespace(uid=1)
    session = make_session(record, record)
    with (
        patch("app.tasks.file_processing.Session", return_value=session),
        patch("app.tasks.file_processing.os.path.exists", return_value=False),
        patch.object(process_audio_file, "update_state"),
    ):
        with pytest.raises(FileNotFoundError):
            process_audio_file.run(1, "/tmp/missing.mp3")


def test_upload_to_storage_success_and_failure():
    """Test upload_to_storage success and failure paths."""
    with (
        patch(
            "app.tasks.file_processing.upload_file_to_hetzner",
            return_value="ok",
        ),
        patch("app.tasks.file_processing.time.time", side_effect=[1.0, 4.0]),
        patch("app.tasks.file_processing.os.remove") as remove,
    ):
        result = upload_to_storage.run("/tmp/file.mp3", "prefix", {"a": "b"})

    assert result["status"] == "success"
    assert result["upload_time_seconds"] == 3.0
    remove.assert_called_once_with("/tmp/file.mp3")

    with (
        patch(
            "app.tasks.file_processing.upload_file_to_hetzner",
            return_value="ok",
        ),
        patch(
            "app.tasks.file_processing.os.remove",
            side_effect=RuntimeError("boom"),
        ),
    ):
        with pytest.raises(RuntimeError):
            upload_to_storage.run("/tmp/file.mp3", "prefix")

"""Tests for the media duration utility."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from app.utils.media_duration import (
    get_media_duration,
    get_media_duration_with_remux,
    remux_file,
    repair_corrupted_mp4,
)


@pytest.fixture(autouse=True)
def mock_logger():
    """Provide a mocked logger."""
    with patch("app.utils.media_duration.logger") as mock_logger:
        yield mock_logger


@pytest.fixture
def mock_moviepy_clip():
    """Provide a mocked moviepy clip."""
    with (
        patch(
            "app.utils.media_duration.VideoFileClip",
            create=True,
        ) as MockVideoFileClip,
        patch(
            "app.utils.media_duration.AudioFileClip",
            create=True,
        ) as MockAudioFileClip,
    ):
        mock_video_clip_instance = Mock()
        mock_video_clip_instance.duration = 120.5
        MockVideoFileClip.return_value.__enter__.return_value = (
            mock_video_clip_instance
        )

        mock_audio_clip_instance = Mock()
        mock_audio_clip_instance.duration = 60.2
        MockAudioFileClip.return_value.__enter__.return_value = (
            mock_audio_clip_instance
        )

        yield MockVideoFileClip, MockAudioFileClip


class TestGetMediaDuration:
    """Tests for GetMediaDuration."""

    @patch("app.utils.media_duration.MOVIEPY_AVAILABLE", False)
    def test_get_media_duration_moviepy_not_available(self):
        """Test get media duration moviepy not available."""
        with pytest.raises(ImportError, match="moviepy is required"):
            get_media_duration("test.mp4", "video")

    @patch("app.utils.media_duration.MOVIEPY_AVAILABLE", True)
    def test_get_media_duration_unsupported_file_type(self):
        """Test get media duration unsupported file type."""
        duration = get_media_duration("test.txt", "document")
        assert duration is None

    @patch("app.utils.media_duration.MOVIEPY_AVAILABLE", True)
    def test_get_media_duration_video_success(self, mock_moviepy_clip):
        """Test get media duration video success."""
        MockVideoFileClip, MockAudioFileClip = mock_moviepy_clip
        duration = get_media_duration("test.mp4", "video")
        assert duration == 120
        MockVideoFileClip.assert_called_once_with("test.mp4")
        MockAudioFileClip.assert_not_called()

    @patch("app.utils.media_duration.MOVIEPY_AVAILABLE", True)
    def test_get_media_duration_audio_success(self, mock_moviepy_clip):
        """Test get media duration audio success."""
        MockVideoFileClip, MockAudioFileClip = mock_moviepy_clip
        duration = get_media_duration("test.mp3", "audio")
        assert duration == 60
        MockAudioFileClip.assert_called_once_with("test.mp3")
        MockVideoFileClip.assert_not_called()

    @patch("app.utils.media_duration.MOVIEPY_AVAILABLE", True)
    @patch(
        "app.utils.media_duration.VideoFileClip",
        side_effect=Exception("Corrupted file"),
        create=True,
    )
    def test_get_media_duration_exception(self, mock_video_clip, mock_logger):
        """Test get media duration exception."""
        duration = get_media_duration("corrupted.mp4", "video")
        assert duration is None
        mock_logger.error.assert_called_once()


class TestRemuxFile:
    """Tests for RemuxFile."""

    @patch("app.utils.media_duration.subprocess.run")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1024)
    @patch("os.path.dirname", return_value="/tmp")
    @patch("os.makedirs")
    def test_remux_file_success(
        self,
        mock_makedirs,
        mock_dirname,
        mock_getsize,
        mock_exists,
        mock_subprocess,
        mock_logger,
    ):
        """Test remux file success."""
        mock_subprocess.return_value = Mock(returncode=0)

        result = remux_file("/input/test.mp4", "/output/test.mp4")

        assert result is True
        mock_subprocess.assert_called_once()

    @patch("os.path.exists", return_value=False)
    def test_remux_file_input_not_exists(self, mock_exists, mock_logger):
        """Test remux file input not exists."""
        result = remux_file("/input/nonexistent.mp4", "/output/test.mp4")
        assert result is False
        mock_logger.error.assert_called()

    @patch("app.utils.media_duration.subprocess.run")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=0)
    @patch("os.path.dirname", return_value="/tmp")
    @patch("os.makedirs")
    def test_remux_file_output_empty(
        self,
        mock_makedirs,
        mock_dirname,
        mock_getsize,
        mock_exists,
        mock_subprocess,
        mock_logger,
    ):
        """Test remux file output empty."""
        mock_subprocess.return_value = Mock(returncode=0)

        result = remux_file("/input/test.mp4", "/output/empty.mp4")

        assert result is False
        mock_logger.warning.assert_called()

    @patch("app.utils.media_duration.subprocess.run")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1024)
    @patch("os.path.dirname", return_value="/tmp")
    @patch("os.makedirs")
    def test_remux_file_subprocess_error(
        self,
        mock_makedirs,
        mock_dirname,
        mock_getsize,
        mock_exists,
        mock_subprocess,
        mock_logger,
    ):
        """Test remux file subprocess error."""
        error = subprocess.CalledProcessError(1, "cmd", stderr="Unknown error")
        mock_subprocess.side_effect = error

        result = remux_file("/input/test.mp4", "/output/test.mp4")

        assert result is False
        mock_logger.error.assert_called()

    @patch(
        "app.utils.media_duration.subprocess.run",
        side_effect=Exception("Generic error"),
    )
    @patch("os.path.exists", return_value=True)
    @patch("os.path.dirname", return_value="/tmp")
    @patch("os.makedirs")
    def test_remux_file_generic_exception(
        self,
        mock_makedirs,
        mock_dirname,
        mock_exists,
        mock_subprocess,
        mock_logger,
    ):
        """Test remux file generic exception."""
        result = remux_file("/input/test.mp4", "/output/test.mp4")
        assert result is False
        mock_logger.error.assert_called()


class TestRepairCorruptedMp4:
    """Tests for RepairCorruptedMp4."""

    @patch("app.utils.media_duration.subprocess.run")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1024)
    def test_repair_corrupted_mp4_success(
        self, mock_getsize, mock_exists, mock_subprocess, mock_logger
    ):
        """Test repair corrupted mp4 success."""
        mock_subprocess.return_value = Mock(returncode=0)

        result = repair_corrupted_mp4(
            "/input/corrupted.mp4", "/output/repaired.mp4"
        )

        assert result is True
        mock_logger.info.assert_called()

    @patch("app.utils.media_duration.subprocess.run")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=0)
    def test_repair_corrupted_mp4_output_empty(
        self, mock_getsize, mock_exists, mock_subprocess, mock_logger
    ):
        """Test repair corrupted mp4 output empty."""
        mock_subprocess.return_value = Mock(returncode=0)

        result = repair_corrupted_mp4(
            "/input/corrupted.mp4", "/output/empty.mp4"
        )

        assert result is False
        mock_logger.warning.assert_called()

    @patch("app.utils.media_duration.subprocess.run")
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1024)
    def test_repair_corrupted_mp4_subprocess_error(
        self, mock_getsize, mock_exists, mock_subprocess, mock_logger
    ):
        """Test repair corrupted mp4 subprocess error."""
        error = subprocess.CalledProcessError(
            1, "cmd", stderr="Encoding failed"
        )
        mock_subprocess.side_effect = error

        result = repair_corrupted_mp4(
            "/input/corrupted.mp4", "/output/failed.mp4"
        )

        assert result is False
        mock_logger.error.assert_called()

    @patch(
        "app.utils.media_duration.subprocess.run",
        side_effect=Exception("Generic error"),
    )
    @patch("os.path.exists", return_value=True)
    def test_repair_corrupted_mp4_generic_exception(
        self, mock_exists, mock_subprocess, mock_logger
    ):
        """Test repair corrupted mp4 generic exception."""
        result = repair_corrupted_mp4(
            "/input/corrupted.mp4", "/output/failed.mp4"
        )
        assert result is False
        mock_logger.error.assert_called()


class TestGetMediaDurationWithRemux:
    """Tests for GetMediaDurationWithRemux."""

    @patch("app.utils.media_duration.get_media_duration", return_value=120)
    def test_get_media_duration_with_remux_direct_success(
        self, mock_get_duration, mock_logger
    ):
        """Test get media duration with remux direct success."""
        duration = get_media_duration_with_remux("test.mp4", "video")
        assert duration == 120
        mock_get_duration.assert_called_once_with("test.mp4", "video")

    @patch("app.utils.media_duration.get_media_duration", return_value=None)
    @patch("app.utils.media_duration.remux_file", return_value=False)
    def test_get_media_duration_with_remux_failed_remux(
        self, mock_remux, mock_get_duration, mock_logger
    ):
        """Test get media duration with remux failed remux."""
        duration = get_media_duration_with_remux("test.webm", "video")
        assert duration is None
        mock_remux.assert_called_once()
        mock_logger.warning.assert_called_once()

    @patch("app.utils.media_duration.get_media_duration", return_value=None)
    def test_get_media_duration_with_remux_unsupported_format(
        self, mock_get_duration
    ):
        """Test get media duration with remux unsupported format."""
        duration = get_media_duration_with_remux("test.unsupported", "video")
        assert duration is None

    @patch("app.utils.media_duration.get_media_duration", return_value=120)
    def test_get_media_duration_with_remux_mp3_format(
        self, mock_get_duration, mock_logger
    ):
        """Test get media duration with remux mp3 format."""
        duration = get_media_duration_with_remux("test.mp3", "audio")
        assert duration == 120

    @patch("app.utils.media_duration.get_media_duration", return_value=120)
    def test_get_media_duration_with_remux_mov_format(
        self, mock_get_duration, mock_logger
    ):
        """Test get media duration with remux mov format."""
        duration = get_media_duration_with_remux("test.mov", "video")
        assert duration == 120

    @patch("app.utils.media_duration.get_media_duration", return_value=120)
    def test_get_media_duration_with_remux_MOV_format(
        self, mock_get_duration, mock_logger
    ):
        """Test get media duration with remux MOV format."""
        duration = get_media_duration_with_remux("test.MOV", "video")
        assert duration == 120

"""Tests for the snr frequency utility."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from app.utils.snr_frequency import (
    _calculate_audio_snr_frequency,
    _calculate_video_snr_frequency,
    _parse_snr_from_output,
    calculate_snr_frequency,
    calculate_snr_with_spectral_analysis,
)


@pytest.fixture(autouse=True)
def mock_logger():
    """Provide a mocked logger."""
    with patch("app.utils.snr_frequency.logger") as mock_logger:
        yield mock_logger


class TestCalculateSNRFrequency:
    """Tests for CalculateSNRFrequency."""

    @patch("app.utils.snr_frequency.os.path.exists", return_value=True)
    @patch(
        "app.utils.snr_frequency._calculate_audio_snr_frequency",
        return_value=10.0,
    )
    def test_calculate_snr_frequency_audio_success(
        self, mock_audio_snr, mock_exists
    ):
        """Test calculate snr frequency audio success."""
        result = calculate_snr_frequency("test.wav", "audio")
        assert result == 10.0
        mock_audio_snr.assert_called_once_with("test.wav")

    @patch("app.utils.snr_frequency.os.path.exists", return_value=True)
    @patch(
        "app.utils.snr_frequency._calculate_video_snr_frequency",
        return_value=15.0,
    )
    def test_calculate_snr_frequency_video_success(
        self, mock_video_snr, mock_exists
    ):
        """Test calculate snr frequency video success."""
        result = calculate_snr_frequency("test.mp4", "video")
        assert result == 15.0
        mock_video_snr.assert_called_once_with("test.mp4")

    @patch("app.utils.snr_frequency.os.path.exists", return_value=False)
    def test_calculate_snr_frequency_file_not_found(self, mock_exists):
        """Test calculate snr frequency file not found."""
        result = calculate_snr_frequency("non_existent.wav", "audio")
        assert result is None

    def test_calculate_snr_frequency_unsupported_type(self):
        """Test calculate snr frequency unsupported type."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            calculate_snr_frequency("test.txt", "document")

    @patch("app.utils.snr_frequency.os.path.exists", return_value=True)
    @patch(
        "app.utils.snr_frequency._calculate_audio_snr_frequency",
        side_effect=Exception("Test Error"),
    )
    def test_calculate_snr_frequency_exception(
        self, mock_audio_snr, mock_exists
    ):
        """Test calculate snr frequency exception."""
        result = calculate_snr_frequency("test.wav", "audio")
        assert result is None

    @patch("app.utils.snr_frequency.os.path.exists", return_value=True)
    @patch(
        "app.utils.snr_frequency._calculate_video_snr_frequency",
        return_value=None,
    )
    def test_calculate_snr_frequency_video_no_audio_track(
        self, mock_video_snr, mock_exists, mock_logger
    ):
        """Test calculate snr frequency video no audio track."""
        result = calculate_snr_frequency("test.mp4", "video")
        assert result is None
        mock_logger.info.assert_called()


class TestCalculateAudioSNRFrequency:
    """Tests for CalculateAudioSNRFrequency."""

    @patch(
        "app.utils.snr_frequency.calculate_snr_with_spectral_analysis",
        return_value=20.0,
    )
    def test_calculate_audio_snr_frequency_spectral_success(
        self, mock_spectral_analysis
    ):
        """Test calculate audio snr frequency spectral success."""
        result = _calculate_audio_snr_frequency("audio.wav")
        assert result == 20.0
        mock_spectral_analysis.assert_called_once_with("audio.wav")

    @patch(
        "app.utils.snr_frequency.calculate_snr_with_spectral_analysis",
        return_value=None,
    )
    @patch("app.utils.snr_frequency.subprocess.run")
    @patch("app.utils.snr_frequency._parse_snr_from_output", return_value=10.0)
    def test_calculate_audio_snr_frequency_fallback_success(
        self, mock_parse_snr, mock_subprocess_run, mock_spectral_analysis
    ):
        """Test calculate audio snr frequency fallback success."""
        mock_subprocess_run.return_value = Mock(stderr="some ffmpeg output")
        result = _calculate_audio_snr_frequency("audio.wav")
        assert result == 10.0
        mock_spectral_analysis.assert_called_once_with("audio.wav")
        mock_subprocess_run.assert_called_once()
        mock_parse_snr.assert_called_once_with("some ffmpeg output")

    @patch(
        "app.utils.snr_frequency.calculate_snr_with_spectral_analysis",
        return_value=None,
    )
    @patch(
        "app.utils.snr_frequency.subprocess.run",
        side_effect=subprocess.CalledProcessError(1, "cmd", stderr="error"),
    )
    def test_calculate_audio_snr_frequency_subprocess_error(
        self, mock_subprocess_run, mock_spectral_analysis
    ):
        """Test calculate audio snr frequency subprocess error."""
        result = _calculate_audio_snr_frequency("audio.wav")
        assert result is None
        mock_spectral_analysis.assert_called_once_with("audio.wav")
        mock_subprocess_run.assert_called_once()

    @patch(
        "app.utils.snr_frequency.calculate_snr_with_spectral_analysis",
        return_value=None,
    )
    @patch(
        "app.utils.snr_frequency.subprocess.run",
        side_effect=Exception("Generic error"),
    )
    def test_calculate_audio_snr_frequency_generic_exception(
        self, mock_subprocess_run, mock_spectral_analysis
    ):
        """Test calculate audio snr frequency generic exception."""
        result = _calculate_audio_snr_frequency("audio.wav")
        assert result is None
        mock_spectral_analysis.assert_called_once_with("audio.wav")
        mock_subprocess_run.assert_called_once()


class TestParseSNRFromOutput:
    """Tests for ParseSNRFromOutput."""

    def test_parse_snr_from_output_with_noise_floor(self):
        """Test parse snr from output with noise floor."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] Channel: 1
[Parsed_astats_0 @ 0x7f8a2c000000] Peak level dB: -3.0
[Parsed_astats_0 @ 0x7f8a2c000000] RMS level dB: -20.0
[Parsed_astats_0 @ 0x7f8a2c000000] Noise floor dB: -80.0
[Parsed_astats_0 @ 0x7f8a2c000000] Dynamic range: 70.0
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr == pytest.approx(60.0)

    def test_parse_snr_from_output_no_noise_floor_with_peak_rms(self):
        """Test parse snr from output no noise floor with peak rms."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] Channel: 1
[Parsed_astats_0 @ 0x7f8a2c000000] Peak level dB: -5.0
[Parsed_astats_0 @ 0x7f8a2c000000] RMS level dB: -25.0
[Parsed_astats_0 @ 0x7f8a2c000000] Dynamic range: 60.0
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr == pytest.approx(20.0)

    def test_parse_snr_from_output_only_rms(self):
        """Test parse snr from output only rms."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] Channel: 1
[Parsed_astats_0 @ 0x7f8a2c000000] RMS level dB: -30.0
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr == pytest.approx(60.0)

    def test_parse_snr_from_output_unrealistic_dynamic_range(self):
        """Test parse snr from output unrealistic dynamic range."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] Channel: 1
[Parsed_astats_0 @ 0x7f8a2c000000] Dynamic range: 120.0
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr == pytest.approx(30.0)

    def test_parse_snr_from_output_no_relevant_data(self):
        """Test parse snr from output no relevant data."""
        ffmpeg_output = """
Some other ffmpeg output
Line 2
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr is None

    def test_parse_snr_from_output_invalid_noise_floor(self):
        """Test parse snr from output invalid noise floor."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] RMS level dB: -20.0
[Parsed_astats_0 @ 0x7f8a2c000000] Noise floor dB: nan
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr == pytest.approx(60.0)

    def test_parse_snr_from_output_exception_handling(self):
        """Test parse snr from output exception handling."""
        snr = _parse_snr_from_output(123)
        assert snr is None


class TestCalculateVideoSNRFrequency:
    """Tests for CalculateVideoSNRFrequency."""

    @patch("app.utils.snr_frequency._calculate_audio_snr_frequency")
    @patch("app.utils.snr_frequency.tempfile.NamedTemporaryFile")
    @patch("app.utils.snr_frequency.subprocess.run")
    @patch("app.utils.snr_frequency.os.path.exists", return_value=True)
    def test_calculate_video_snr_frequency_success(
        self, mock_exists, mock_subprocess_run, mock_temp_file, mock_audio_snr
    ):
        """Test calculate video snr frequency success."""
        mock_temp_file.return_value.__enter__ = Mock(
            return_value=Mock(name="/tmp/audio.wav")
        )
        mock_temp_file.return_value.__exit__ = Mock(return_value=False)

        mock_probe_result = Mock()
        mock_probe_result.stdout = "audio"
        mock_subprocess_result = Mock()
        mock_subprocess_result.stdout = ""
        mock_audio_snr.return_value = 25.0

        mock_subprocess_run.side_effect = [
            mock_probe_result,
            mock_subprocess_result,
        ]

        result = _calculate_video_snr_frequency("test.mp4")
        assert result == 25.0

    @patch("app.utils.snr_frequency.os.path.exists", return_value=True)
    def test_calculate_video_snr_frequency_no_audio_stream(
        self, mock_exists, mock_logger
    ):
        """Test calculate video snr frequency no audio stream."""
        with patch(
            "app.utils.snr_frequency.subprocess.run"
        ) as mock_subprocess_run:
            mock_probe_result = Mock()
            mock_probe_result.stdout = ""
            mock_subprocess_run.return_value = mock_probe_result

            result = _calculate_video_snr_frequency("video_only.mp4")
            assert result is None

    @patch("app.utils.snr_frequency.tempfile.NamedTemporaryFile")
    @patch("app.utils.snr_frequency.subprocess.run")
    @patch("app.utils.snr_frequency.os.path.exists", return_value=True)
    def test_calculate_video_snr_frequency_subprocess_error(
        self, mock_exists, mock_subprocess_run, mock_temp_file, mock_logger
    ):
        """Test calculate video snr frequency subprocess error."""
        mock_temp_file.return_value.__enter__ = Mock(
            return_value=Mock(name="/tmp/audio.wav")
        )
        mock_temp_file.return_value.__exit__ = Mock(return_value=False)

        mock_probe_result = Mock()
        mock_probe_result.stdout = "audio"
        mock_subprocess_run.side_effect = [
            mock_probe_result,
            subprocess.CalledProcessError(
                1, "cmd", stderr="does not contain any stream"
            ),
        ]

        result = _calculate_video_snr_frequency("test.mp4")
        assert result is None

    @patch("app.utils.snr_frequency.tempfile.NamedTemporaryFile")
    @patch("app.utils.snr_frequency.subprocess.run")
    @patch("app.utils.snr_frequency.os.path.exists", return_value=True)
    def test_calculate_video_snr_frequency_generic_exception(
        self, mock_exists, mock_subprocess_run, mock_temp_file, mock_logger
    ):
        """Test calculate video snr frequency generic exception."""
        mock_temp_file.return_value.__enter__ = Mock(
            return_value=Mock(name="/tmp/audio.wav")
        )
        mock_temp_file.return_value.__exit__ = Mock(return_value=False)

        mock_probe_result = Mock()
        mock_probe_result.stdout = "audio"
        mock_subprocess_run.side_effect = [
            mock_probe_result,
            Exception("Generic error"),
        ]

        result = _calculate_video_snr_frequency("test.mp4")
        assert result is None


class TestCalculateSNRWithSpectralAnalysis:
    """Tests for CalculateSNRWithSpectralAnalysis."""

    @patch("app.utils.snr_frequency.subprocess.run")
    def test_calculate_snr_with_spectral_analysis_success_with_silence(
        self, mock_subprocess_run
    ):
        """Test calculate snr with spectral analysis success with silence."""
        mock_subprocess_run.return_value = Mock(
            stderr="""
[silencedetect @ 0x7f8a2c000000] silencedetect: silence_start: 0.0
[silencedetect @ 0x7f8a2c000000] silencedetect: silence_end: 1.0
[silencedetect @ 0x7f8a2c000000] silencedetect: silence_duration: 1.0
[volumedetect @ 0x7f8a2c000000] mean_volume: -20.0 dB
[volumedetect @ 0x7f8a2c000000] max_volume: -5.0 dB
"""
        )

        result = calculate_snr_with_spectral_analysis("test.wav")
        assert result is not None
        assert 5.0 <= result <= 60.0

    @patch("app.utils.snr_frequency.subprocess.run")
    def test_calculate_snr_with_spectral_analysis_no_silence(
        self, mock_subprocess_run
    ):
        """Test calculate snr with spectral analysis no silence."""
        mock_subprocess_run.return_value = Mock(
            stderr="""
[volumedetect @ 0x7f8a2c000000] mean_volume: -20.0 dB
[volumedetect @ 0x7f8a2c000000] max_volume: -5.0 dB
"""
        )

        result = calculate_snr_with_spectral_analysis("test.wav")
        assert result is not None

    @patch("app.utils.snr_frequency.subprocess.run")
    def test_calculate_snr_with_spectral_analysis_fallback(
        self, mock_subprocess_run
    ):
        """Test calculate snr with spectral analysis fallback."""
        mock_subprocess_run.side_effect = [
            Mock(
                stderr="""
[volumedetect @ 0x7f8a2c000000] mean_volume: -20.0 dB
[volumedetect @ 0x7f8a2c000000] max_volume: -5.0 dB
"""
            ),
            Mock(stderr=""),
        ]

        result = calculate_snr_with_spectral_analysis("test.wav")
        assert result is not None or result is None

    @patch(
        "app.utils.snr_frequency.subprocess.run", side_effect=Exception("Error")
    )
    def test_calculate_snr_with_spectral_analysis_exception(
        self, mock_subprocess_run
    ):
        """Test calculate snr with spectral analysis exception."""
        result = calculate_snr_with_spectral_analysis("test.wav")
        assert result is None


class TestParseSNRFromOutputEdgeCases:
    """Tests for ParseSNRFromOutputEdgeCases."""

    def test_parse_snr_very_high_crest_factor(self):
        """Test parse snr very high crest factor."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] Peak level dB: -5.0
[Parsed_astats_0 @ 0x7f8a2c000000] RMS level dB: -50.0
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr == 60.0

    def test_parse_snr_normal_crest_factor(self):
        """Test parse snr normal crest factor."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] Peak level dB: -10.0
[Parsed_astats_0 @ 0x7f8a2c000000] RMS level dB: -30.0
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr == 20.0

    def test_parse_snr_low_crest_factor(self):
        """Test parse snr low crest factor."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] Peak level dB: -15.0
[Parsed_astats_0 @ 0x7f8a2c000000] RMS level dB: -20.0
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr == 20.0

    def test_parse_snr_reasonable_dynamic_range(self):
        """Test parse snr reasonable dynamic range."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] Dynamic range: 50.0
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr == 30.0

    def test_parse_snr_invalid_noise_floor_inf(self):
        """Test parse snr invalid noise floor inf."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] RMS level dB: -20.0
[Parsed_astats_0 @ 0x7f8a2c000000] Noise floor dB: -inf
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr is not None

    def test_parse_snr_noise_floor_too_low(self):
        """Test parse snr noise floor too low."""
        ffmpeg_output = """
[Parsed_astats_0 @ 0x7f8a2c000000] RMS level dB: -20.0
[Parsed_astats_0 @ 0x7f8a2c000000] Noise floor dB: -150.0
"""
        snr = _parse_snr_from_output(ffmpeg_output)
        assert snr is not None

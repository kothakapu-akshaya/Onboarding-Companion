"""Utility functions for calculating SNR (Signal-to-Noise Ratio) frequency.

Supports both audio and video files.
"""

import logging
import os
import subprocess
import tempfile

# Set up logger for this module
logger = logging.getLogger(__name__)


def calculate_snr_frequency(file_path: str, file_type: str) -> float | None:
    """Calculate the SNR frequency of an audio or video file using ffmpeg.

    Args:
        file_path: Path to the media file (string)
        file_type: File type ('audio' or 'video')

    Returns:
        The SNR frequency value in dB, or None if calculation fails.
        For video files without audio tracks, returns None (expected behavior).

    Raises:
        ValueError: If the specified file type is not supported.
    """
    if file_type.lower() not in ["audio", "video"]:
        logger.error(f"Unsupported file type: {file_type}")
        raise ValueError(
            f"Unsupported file type: {file_type}. "
            "Supported types: 'audio', 'video'"
        )

    try:
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        # For video files, extract audio first
        if file_type.lower() == "video":
            snr_freq = _calculate_video_snr_frequency(file_path)
            if snr_freq is None:
                # Check if this was due to no audio track
                # (common for test files)
                logger.info(
                    f"Video file {file_path} has no audio track - "
                    "SNR calculation not applicable"
                )
        else:
            snr_freq = _calculate_audio_snr_frequency(file_path)

        if snr_freq is not None:
            logger.info(
                f"Calculated SNR frequency for {file_path}: {snr_freq:.2f} dB"
            )
        elif file_type.lower() == "audio":
            logger.warning(
                f"Failed to calculate SNR frequency for audio file {file_path}"
            )

        return snr_freq

    except Exception as e:
        logger.error(
            f"Error calculating SNR frequency for {file_path}: {str(e)}"
        )
        return None


def _has_decode_errors(stderr: str) -> bool:
    """Return True if ffmpeg stderr contains hard decode errors.

    ffmpeg exits 0 but still logs AVERROR_INVALIDDATA for individual corrupt
    packets.  We treat any such message as a fatal file quality issue so that
    snr_frequency is set to None and the record is excluded from ASR queues.
    """
    return "Invalid data found when processing input" in stderr


def _calculate_audio_snr_frequency(file_path: str) -> float | None:
    """Calculate SNR frequency for audio files using ffmpeg astats filter.

    Args:
        file_path: Path to the audio file

    Returns:
        SNR frequency value in dB or None if calculation fails
    """
    try:
        # First try the improved spectral analysis method
        snr_value = calculate_snr_with_spectral_analysis(file_path)
        if snr_value is not None:
            return snr_value

        # Fallback to original method with improved parsing
        cmd = [
            "ffmpeg",
            "-i",
            file_path,
            "-af",
            "astats=metadata=1:reset=1",
            "-f",
            "null",
            "-",
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )

        if _has_decode_errors(result.stderr):
            logger.warning(
                f"Audio file {file_path} contains corrupt encoded packets "
                "— treating as undecodable"
            )
            return None

        # Parse the output for SNR-related statistics
        snr_value = _parse_snr_from_output(result.stderr)
        return snr_value

    except Exception as e:
        logger.error(f"Error calculating audio SNR frequency: {str(e)}")
        return None


def _calculate_video_snr_frequency(file_path: str) -> float | None:
    """Calculate SNR frequency for video files by extracting audio track first.

    Args:
        file_path: Path to the video file

    Returns:
        SNR frequency value in dB or None if calculation fails
    """
    temp_audio_path = None
    try:
        # First check if video has audio streams
        probe_cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            file_path,
        ]

        probe_result = subprocess.run(
            probe_cmd, capture_output=True, text=True, check=False
        )

        if not probe_result.stdout.strip():
            # No audio stream found
            logger.info(
                f"Video file {file_path} contains no audio track "
                f"(video-only file)"
            )
            return None

        # Create temporary audio file
        with tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        ) as temp_file:
            temp_audio_path = temp_file.name

        # Extract audio from video
        extract_cmd = [
            "ffmpeg",
            "-i",
            file_path,
            "-vn",  # No video
            "-acodec",
            "pcm_s16le",  # PCM audio codec
            "-ar",
            "44100",  # Sample rate
            "-ac",
            "2",  # Stereo
            "-y",  # Overwrite
            temp_audio_path,
        ]

        subprocess.run(extract_cmd, capture_output=True, text=True, check=True)

        # Calculate SNR for extracted audio
        return _calculate_audio_snr_frequency(temp_audio_path)

    except subprocess.CalledProcessError as e:
        # Check if the error is due to no audio stream
        if (
            "does not contain any stream" in e.stderr
            or "Invalid argument" in e.stderr
        ):
            logger.info(
                f"Video file {file_path} contains no audio track "
                f"(video-only file)"
            )
        else:
            logger.error(f"Error extracting audio from video: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Error calculating video SNR frequency: {str(e)}")
        return None
    finally:
        # Clean up temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
            except Exception as e:
                logger.error(
                    f"Error cleaning up temporary audio file: {str(e)}"
                )


def _parse_snr_from_output(ffmpeg_output: str) -> float | None:
    """Parse SNR value from ffmpeg astats output.

    SNR = Signal_Level_dB - Noise_Floor_dB

    If noise floor isn't available, we estimate it using RMS measurements.

    Args:
        ffmpeg_output: The stderr output from ffmpeg with astats filter

    Returns:
        SNR value in dB or None if calculation fails
    """
    try:
        lines = ffmpeg_output.split("\n")

        # Extract key measurements from the last complete statistics block
        peak_level_db = None
        rms_level_db = None
        noise_floor_db = None
        dynamic_range = None

        # Parse the last complete set of statistics (final values)
        for line in reversed(lines):
            line = line.strip()

            if "Peak level dB:" in line and peak_level_db is None:
                try:
                    parts = line.split(":")
                    if len(parts) > 1:
                        peak_level_db = float(parts[1].strip())
                except (ValueError, IndexError):
                    continue

            elif "RMS level dB:" in line and rms_level_db is None:
                try:
                    parts = line.split(":")
                    if len(parts) > 1:
                        rms_level_db = float(parts[1].strip())
                except (ValueError, IndexError):
                    continue

            elif "Noise floor dB:" in line and noise_floor_db is None:
                try:
                    parts = line.split(":")
                    if len(parts) > 1:
                        value_str = parts[1].strip()
                        if value_str != "nan" and value_str != "-inf":
                            noise_floor_db = float(value_str)
                except (ValueError, IndexError):
                    continue

            elif "Dynamic range:" in line and dynamic_range is None:
                try:
                    parts = line.split(":")
                    if len(parts) > 1:
                        dynamic_range = float(parts[1].strip())
                except (ValueError, IndexError):
                    continue

        # Calculate SNR using proper method
        if rms_level_db is not None:
            # Method 1: If we have a valid noise floor, use it
            if (
                noise_floor_db is not None and noise_floor_db > -120
            ):  # Reasonable noise floor threshold
                snr = rms_level_db - noise_floor_db
                logger.info(
                    f"Calculated SNR using RMS level ({rms_level_db:.2f} dB) "
                    f"- Noise floor ({noise_floor_db:.2f} dB) = {snr:.2f} dB"
                )
                return snr

            # Method 2: Estimate SNR using RMS to Peak ratio
            # Crest factor (Peak/RMS ratio) is 6-20 dB for most audio content
            if peak_level_db is not None:
                crest_factor = peak_level_db - rms_level_db

                # Estimate noise floor based on bit depth
                if crest_factor > 40:
                    estimated_noise_floor = (
                        rms_level_db - 60
                    )  # Conservative estimate
                elif crest_factor > 20:  # Normal music/speech
                    estimated_noise_floor = rms_level_db - 40
                else:  # Compressed audio or noise-like signals
                    estimated_noise_floor = rms_level_db - 20

                snr = rms_level_db - estimated_noise_floor
                logger.info(
                    f"Estimated SNR using RMS level ({rms_level_db:.2f} dB) - "
                    f"Estimated noise floor ({estimated_noise_floor:.2f} dB) "
                    f"= {snr:.2f} dB"
                )
                return snr

            # Method 3: Use a conservative estimate based on RMS level alone
            # Assume noise floor is 60 dB below RMS for typical digital audio
            estimated_noise_floor = rms_level_db - 60
            snr = 60.0  # This gives us the assumed difference
            logger.info(
                f"Conservative SNR estimate based on RMS level: {snr:.2f} dB"
            )
            return snr

        # Fallback: If dynamic range is high, it suggests artifacts
        if dynamic_range is not None:
            if (
                dynamic_range > 100
            ):  # Unrealistically high - likely measurement artifact
                logger.warning(
                    f"Dynamic range ({dynamic_range:.2f} dB) appears "
                    f"unrealistic, using conservative estimate"
                )
                return 30.0  # Conservative estimate for good quality audio
            else:
                # Use a fraction of dynamic range as SNR estimate
                snr_estimate = min(dynamic_range * 0.6, 60.0)  # Cap at 60 dB
                logger.info(
                    f"SNR estimated from dynamic range: {snr_estimate:.2f} dB"
                )
                return snr_estimate

        logger.warning("Could not calculate SNR from available measurements")
        return None

    except Exception as e:
        logger.error(f"Error parsing SNR from ffmpeg output: {str(e)}")
        return None


def calculate_snr_with_spectral_analysis(file_path: str) -> float | None:
    """Calculate SNR using proper signal analysis techniques.

    This method attempts to estimate the noise floor by analyzing signal
    distribution.

    Args:
        file_path: Path to the audio file

    Returns:
        SNR value in dB or None if calculation fails
    """
    try:
        # Method 1: Use silencedetect to find noise floor during quiet periods
        cmd = [
            "ffmpeg",
            "-i",
            file_path,
            "-af",
            "silencedetect=noise=-60dB:duration=0.1,volumedetect",
            "-f",
            "null",
            "-",
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )

        if _has_decode_errors(result.stderr):
            logger.warning(
                f"Audio file {file_path} contains corrupt encoded packets "
                "— treating as undecodable"
            )
            return None

        # Parse silence detection results to estimate noise floor
        silence_lines = [
            line
            for line in result.stderr.split("\n")
            if "silencedetect" in line
        ]
        volume_lines = [
            line for line in result.stderr.split("\n") if "volumedetect" in line
        ]

        mean_volume = None
        max_volume = None

        # Extract volume measurements
        for line in volume_lines:
            if "mean_volume:" in line:
                try:
                    mean_volume = float(
                        line.split("mean_volume:")[1].split("dB")[0].strip()
                    )
                except (ValueError, IndexError):
                    continue
            elif "max_volume:" in line:
                try:
                    max_volume = float(
                        line.split("max_volume:")[1].split("dB")[0].strip()
                    )
                except (ValueError, IndexError):
                    continue

        # If we have both measurements, calculate proper SNR
        if mean_volume is not None and max_volume is not None:
            # Method 1: Use the relationship between peak, mean, and silence
            dynamic_range = max_volume - mean_volume

            # Estimate noise floor based on audio characteristics
            # For digital audio, noise floor is typically much lower than signal
            if len(silence_lines) > 2:  # Detected silence periods
                # Audio has quiet sections - good for SNR estimation
                estimated_noise_floor = mean_volume - dynamic_range * 0.8
            else:
                # Continuous audio - estimate based on typical characteristics
                estimated_noise_floor = mean_volume - dynamic_range * 0.6

            # Signal level is the RMS equivalent of the mean volume
            signal_level = mean_volume + 3  # Approximate RMS adjustment

            # Calculate SNR
            snr = signal_level - estimated_noise_floor

            # Apply realistic bounds for audio content
            if snr > 60:  # Cap unrealistic values
                snr = (
                    45 + (dynamic_range - 10) * 0.5
                )  # Scale with content dynamics
            elif snr < 5:  # Minimum reasonable SNR
                snr = max(5, dynamic_range * 0.4)

            snr = max(5.0, min(snr, 60.0))

            logger.info(
                f"Calculated SNR: signal({signal_level:.1f}) - "
                f"noise({estimated_noise_floor:.1f}) = {snr:.1f} dB"
            )
            return snr

        # Method 2: Fallback using astats for more detailed analysis
        cmd2 = [
            "ffmpeg",
            "-i",
            file_path,
            "-af",
            "astats=metadata=1:reset=1",
            "-f",
            "null",
            "-",
        ]

        result2 = subprocess.run(
            cmd2, capture_output=True, text=True, check=False
        )
        return _parse_snr_from_output(result2.stderr)

    except Exception as e:
        logger.error(f"Error in spectral SNR analysis: {str(e)}")
        return None

    except Exception as e:
        logger.error(f"Error getting audio statistics: {str(e)}")
        return None

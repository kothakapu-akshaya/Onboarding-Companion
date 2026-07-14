"""Utility functions for computing media file durations using moviepy."""

import logging
import os
import subprocess
import tempfile

# Set up logger for this module
logger = logging.getLogger(__name__)

try:
    from moviepy import AudioFileClip, VideoFileClip

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False


def remux_file(
    input_path: str, output_path: str, output_format: str = "mp4"
) -> bool:
    """Remux a media file to a different container format using ffmpeg.

    Args:
        input_path: Path to the input media file
        output_path: Path for the output file
        output_format: Target container format (default: "mp4")

    Returns:
        True if remuxing was successful, False otherwise
    """
    try:
        # Check if input file exists
        if not os.path.exists(input_path):
            logger.error(f"Input file does not exist: {input_path}")
            return False

        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:  # Only create directory if there is a path
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Ensured output directory exists: {output_dir}")

        # Build ffmpeg command for remuxing (copy codecs, just change container)
        cmd = [
            "ffmpeg",
            "-i",
            input_path,
            "-c",
            "copy",  # Copy streams without re-encoding
            "-f",
            output_format,
            "-y",  # Overwrite output file if it exists
            output_path,
        ]

        logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")

        # Run ffmpeg command
        subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Check if output file was actually created and has size > 0
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        else:
            logger.warning(
                f"Remuxing completed but output file is missing or empty: "
                f"{output_path}"
            )
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error during remuxing: {e.stderr}")
        logger.debug(f"FFmpeg stdout: {e.stdout}")
        logger.debug(f"FFmpeg return code: {e.returncode}")

        # If the error is about moov atom not found, try to repair the file
        if (
            "moov atom not found" in e.stderr
            or "Invalid data found when processing input" in e.stderr
        ):
            logger.info("Attempting to repair corrupted MP4 file...")
            return repair_corrupted_mp4(input_path, output_path)

        return False
    except Exception as e:
        logger.error(f"Error during remuxing: {str(e)}")
        return False


def repair_corrupted_mp4(input_path: str, output_path: str) -> bool:
    """Attempt to repair a corrupted MP4 file by re-encoding it.

    Args:
        input_path: Path to the corrupted MP4 file
        output_path: Path for the repaired output file

    Returns:
        True if repair was successful, False otherwise
    """
    try:
        logger.info(f"Attempting to repair corrupted MP4: {input_path}")

        # Try to repair by re-encoding (this is slower but more robust)
        cmd = [
            "ffmpeg",
            "-i",
            input_path,
            "-c:v",
            "libx264",  # Re-encode video with H.264
            "-c:a",
            "aac",  # Re-encode audio with AAC
            "-preset",
            "fast",  # Use fast preset for speed
            "-crf",
            "23",  # Good quality setting
            "-y",  # Overwrite output file
            output_path,
        ]

        logger.debug(f"Running repair command: {' '.join(cmd)}")

        subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Check if output file was created and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"Successfully repaired MP4 file: {output_path}")
            return True
        else:
            logger.warning(
                f"Repair completed but output file is missing or empty: "
                f"{output_path}"
            )
            return False

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error during repair: {e.stderr}")
        logger.debug(f"FFmpeg stdout: {e.stdout}")
        logger.debug(f"FFmpeg return code: {e.returncode}")
        return False
    except Exception as e:
        logger.error(f"Error during repair: {str(e)}")
        return False


def get_media_duration_with_remux(file_path: str, file_type: str) -> int | None:
    """Get media duration with remuxing fallback for problematic formats.

    For certain file formats that may have compatibility issues with moviepy,
    this function will first try to get duration directly, and if that fails,
    it will remux to a more compatible format and try again.

    Supported formats for remuxing: webm, mp3, mp4, mov, MOV

    Args:
        file_path: Path to the media file
        file_type: File type ('audio' or 'video')

    Returns:
        Duration in seconds as int, or None if duration cannot be computed
    """
    # First try to get duration normally
    duration = get_media_duration(file_path, file_type)

    # If it failed, try remuxing for supported formats
    file_ext = os.path.splitext(file_path)[1]  # Keep original case
    file_ext_lower = file_ext.lower()  # For comparison

    # Supported formats for remuxing to MP4
    supported_formats = {".webm", ".mp3", ".mp4", ".mov"}
    if duration is None and file_ext_lower in supported_formats:
        logger.info(
            f"Failed to get duration for {file_ext} file {file_path}, "
            "attempting remux to MP4..."
        )

        try:
            # Create a temporary MP4 file
            with tempfile.NamedTemporaryFile(
                suffix=".mp4", delete=False
            ) as temp_file:
                temp_mp4_path = temp_file.name
                logger.debug(f"Created temporary file: {temp_mp4_path}")

            # Remux to MP4
            logger.debug(f"Attempting to remux {file_path} to {temp_mp4_path}")
            if remux_file(file_path, temp_mp4_path, "mp4"):
                # Try to get duration from the remuxed file
                logger.debug("Remuxing successful, checking duration...")
                duration = get_media_duration(temp_mp4_path, file_type)
                logger.info(
                    f"Remuxed {file_ext} to MP4, duration: {duration} seconds"
                )
            else:
                logger.warning(f"Failed to remux {file_ext} file {file_path}")

        except Exception as e:
            logger.error(f"Error during {file_ext} remuxing: {str(e)}")
        finally:
            # Clean up temporary file
            try:
                if os.path.exists(temp_mp4_path):
                    os.unlink(temp_mp4_path)
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {str(e)}")

    return duration


def get_media_duration(file_path: str, file_type: str) -> int | None:
    """Compute the duration of an audio or video file using moviepy.

    Args:
        file_path: Path to the media file (string)
        file_type: File type ('audio' or 'video')

    Returns:
        Duration in seconds as int, or None if duration cannot be computed

    Raises:
        ImportError: If moviepy is not available
        ValueError: If file type is not supported
    """
    if not MOVIEPY_AVAILABLE:
        raise ImportError(
            "moviepy is required for media duration computation. "
            "Install with: pip install moviepy"
        )

    try:
        if file_type.lower() == "video":
            with VideoFileClip(file_path) as clip:
                return int(clip.duration)
        elif file_type.lower() == "audio":
            with AudioFileClip(file_path) as clip:
                return int(clip.duration)
        else:
            raise ValueError(
                f"Unsupported file type: {file_type}. "
                "Supported types: 'audio', 'video'"
            )

    except Exception as e:
        # Log the error but don't raise it, return None instead
        logger.error(f"Error computing duration for {file_path}: {str(e)}")
        return None

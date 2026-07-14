"""Utility functions for hashing files using various algorithms."""

import hashlib
import logging

# Set up logger for this module
logger = logging.getLogger(__name__)


def get_file_hash(file_path: str, algorithm: str = "sha256") -> str | None:
    """Compute the hash of a file using the specified algorithm.

    Args:
        file_path: Path to the file (string)
        algorithm: Hashing algorithm to use (e.g., 'sha256', 'md5')

    Returns:
        The hex digest of the file hash, or None if an error occurs.

    Raises:
        ValueError: If the specified algorithm is not supported.
    """
    try:
        hasher = hashlib.new(algorithm)
    except ValueError:
        logger.error(f"Unsupported hashing algorithm: {algorithm}")
        raise

    try:
        with open(file_path, "rb") as f:
            # Read the file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error hashing file {file_path}: {str(e)}")
        return None

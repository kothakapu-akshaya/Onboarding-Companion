#!/usr/bin/env python3
"""File management utilities for backfill operations.

Handles downloading files from object storage and temporary file management.
"""

import logging
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models.record import Record
from app.utils.hetzner_storage import get_storage_client


class FileManager:
    """Manages file operations for backfill processes.

    Responsibilities:
    - Download files from object storage to temporary locations
    - Clean up temporary files
    - Handle file path extraction from URLs
    """

    def __init__(self) -> None:
        """Initialize the file manager with storage client."""
        self.storage_client = get_storage_client()
        self.logger = logging.getLogger(self.__class__.__name__)

    def download_file_to_temp(
        self, record: Record, class_name: str = "FileManager"
    ) -> str | None:
        """Download a file from object storage to a temporary location.

        Args:
            record: Record containing file information
            class_name: Name of the calling class for temp file naming

        Returns:
            Path to temporary file, or None if download failed
        """
        if not record.file_url:
            self.logger.warning(f"Record {record.uid} has no file_url")
            return None

        try:
            # Extract bucket and object key from file_url.
            # file_url may be a full URL (https://endpoint/bucket/object_key)
            # or a relative path (bucket/object_key or object_key).
            parsed_url = urlparse(record.file_url)
            path = parsed_url.path.lstrip("/")

            if parsed_url.scheme in ("http", "https"):
                # Full URL: first path segment is the bucket name
                parts = path.split("/", 1)
                if len(parts) == 2:
                    bucket_name, object_key = parts
                else:
                    bucket_name = self.storage_client.bucket_name
                    object_key = path
            else:
                # Relative path: strip configured bucket prefix if present
                bucket_name = self.storage_client.bucket_name
                object_key = path
                if object_key.startswith(f"{bucket_name}/"):
                    object_key = object_key[len(f"{bucket_name}/") :]

            if not object_key:
                self.logger.error(
                    f"Could not extract object key from {record.file_url}"
                )
                return None

            # Create temporary file
            file_extension = (
                Path(record.file_name or object_key).suffix
                if record.file_name
                else ""
            )
            if not file_extension:
                # Try to determine extension from object key
                file_extension = Path(object_key).suffix

            # Create temp file with proper extension
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=file_extension,
                prefix=f"{class_name.lower()}_{record.uid}_",
            )
            temp_path = temp_file.name
            temp_file.close()

            self.logger.info(f"Downloading {object_key} to {temp_path}")

            # Download file from object storage
            self.storage_client.client.fget_object(
                bucket_name=bucket_name,
                object_name=object_key,
                file_path=temp_path,
            )

            # Verify file was downloaded and has content
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                self.logger.info(
                    f"Successfully downloaded {object_key} "
                    f"({os.path.getsize(temp_path)} bytes)"
                )
                return temp_path
            else:
                self.logger.error(
                    f"Downloaded file {temp_path} is empty or doesn't exist"
                )
                return None

        except Exception as e:
            self.logger.error(
                f"Failed to download file for record {record.uid}: {e}"
            )
            return None

    def cleanup_temp_file(self, file_path: str) -> None:
        """Clean up temporary file.

        Args:
            file_path: Path to temporary file to delete
        """
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                self.logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            self.logger.warning(
                f"Failed to clean up temporary file {file_path}: {e}"
            )

    def get_object_key_from_url(self, file_url: str) -> str | None:
        """Extract object key from file URL.

        Args:
            file_url: Full URL to the file

        Returns:
            Object key string, or None if extraction failed
        """
        try:
            parsed_url = urlparse(file_url)
            object_key = parsed_url.path.lstrip("/")

            # Remove bucket name from object key if it's included in the path
            bucket_name = self.storage_client.bucket_name
            if object_key.startswith(f"{bucket_name}/"):
                object_key = object_key[len(f"{bucket_name}/") :]

            return object_key
        except Exception as e:
            self.logger.error(f"Failed to parse URL {file_url}: {e}")
            return None

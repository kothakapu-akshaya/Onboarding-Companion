"""Hetzner Object Storage utility functions using MinIO client.

Hetzner Object Storage is S3-compatible, so we use the MinIO Python SDK.
"""

import logging
import mimetypes
import os
import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Any, BinaryIO, Union
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import HTTPException
from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

# Type alias for MinIO metadata - use the exact type expected by MinIO
MetadataType = dict[str, Union[str, list[str], tuple[str]]]


class ProgressLogs(Thread):
    """Progress logging class for file uploads using MinIO interface."""

    def __init__(self, filename: str | None = None):
        """Initialize progress logger.

        Args:
            filename: Name of the file being uploaded
        """
        Thread.__init__(self)
        self.daemon = True

        self.filename = filename
        self.total_length = 0
        self.current_size = 0
        self.last_logged_percentage = 0
        self.initial_time = time.time()

        self.start()

    def set_meta(self, total_length: int, object_name: str):
        """Set metadata for the upload. Called by MinIO before uploading.

        Args:
            total_length: Total length of the object in bytes
            object_name: Object name being uploaded
        """
        self.total_length = total_length
        self.object_name = object_name
        self.filename = object_name if not self.filename else self.filename
        logger.info(
            f"Starting upload for {self.filename} ({total_length} bytes)"
        )

    def update(self, size: int):
        """Update progress. Called by MinIO during upload.

        Args:
            size: Number of bytes transferred in this update
        """
        if not isinstance(size, int):
            raise ValueError(
                f"{type(size)} type cannot be displayed. "
                "Please change it to int."
            )

        self.current_size += size

        if self.total_length > 0:
            percentage = int((self.current_size / self.total_length) * 100)

            # Log every 10% progress
            if percentage >= self.last_logged_percentage + 10:
                elapsed_time = time.time() - self.initial_time
                logger.info(
                    f"Upload progress for {self.filename}: {percentage}% "
                    f"({self.current_size}/{self.total_length} bytes) - "
                    f"{elapsed_time:.1f}s elapsed"
                )
                self.last_logged_percentage = percentage

    def run(self):
        """Thread run method - not used in our logging implementation."""
        pass


class HetznerStorageClient:
    """Hetzner Object Storage client using MinIO SDK."""

    def __init__(self):
        """Initialize the Hetzner storage client."""
        if not all(
            [
                settings.MINIO_ENDPOINT,
                settings.MINIO_ACCESS_KEY,
                settings.MINIO_SECRET_KEY,
            ]
        ):
            raise ValueError(
                "Missing required Hetzner Object Storage credentials. "
                "Please set HZ_OBJ_ENDPOINT, HZ_OBJ_ACCESS_KEY, and "
                "HZ_OBJ_SECRET_KEY in your .env file."
            )

        # Remove protocol from endpoint if present
        endpoint = settings.MINIO_ENDPOINT
        if not endpoint:
            raise ValueError("HZ_OBJ_ENDPOINT is required but not set")

        endpoint = endpoint.replace("https://", "").replace("http://", "")

        self.client = Minio(
            endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )

        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create it if it doesn't."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.info(f"Creating bucket: {self.bucket_name}")
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Successfully created bucket: {self.bucket_name}")
            else:
                logger.debug(f"Bucket {self.bucket_name} already exists")
        except S3Error as e:
            logger.error(f"Error creating bucket {self.bucket_name}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to access or create storage bucket: {str(e)}",
            )

    def generate_object_key(self, filename: str, prefix: str = "") -> str:
        """Generate a unique object key for storage.

        Args:
            filename: Original filename
            prefix: Optional prefix for organizing files
                (e.g., 'audio/', 'video/')

        Returns:
            Unique object key
        """
        # Extract file extension
        file_ext = os.path.splitext(filename)[1].lower()

        # Generate unique filename with timestamp and UUID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid4())[:8]
        unique_filename = f"{timestamp}_{unique_id}{file_ext}"

        # Combine with prefix
        if prefix and not prefix.endswith("/"):
            prefix += "/"

        return f"{prefix}{unique_filename}"

    def upload_file(
        self,
        file_path: str,
        object_key: str | None = None,
        prefix: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upload a file to Hetzner Object Storage.

        Args:
            file_path: Path to the file to upload
            object_key: Custom object key, if None will be auto-generated
            prefix: Prefix for organizing files (e.g., 'audio/', 'video/')
            metadata: Optional metadata to attach to the object

        Returns:
            Dictionary with upload information
        """
        try:
            # Validate file path
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=400, detail=f"File not found: {file_path}"
                )

            # Get file information
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)

            # Check file size
            if file_size > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"File size {file_size} bytes exceeds maximum allowed "
                        f"size of {settings.MAX_FILE_SIZE} bytes"
                    ),
                )

            # Determine content type based on file extension
            content_type = self._get_content_type(filename)

            # Generate object key if not provided
            if not object_key:
                object_key = self.generate_object_key(filename, prefix)

            # Prepare metadata - convert to MinIO format
            upload_metadata: MetadataType = {
                "original-filename": filename,
                # "content-type": content_type, # check this
                "upload-timestamp": datetime.now().isoformat(),
            }

            if metadata:
                # Ensure all metadata values are strings for MinIO
                string_metadata = {k: str(v) for k, v in metadata.items()}
                upload_metadata.update(string_metadata)

            # Create progress logger
            progress_logger = ProgressLogs(filename)

            # Upload file
            logger.info(
                f"Uploading file {filename} as {object_key} to bucket "
                f"{self.bucket_name}"
            )

            result = self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                file_path=file_path,
                content_type=content_type,
                metadata=upload_metadata,
                progress=progress_logger,
            )

            # Get object URL
            object_url = self.get_object_url(object_key)

            logger.info(
                f"Successfully uploaded file {filename} to {object_key}"
            )

            return {
                "success": True,
                "object_key": object_key,
                "bucket_name": self.bucket_name,
                "original_filename": filename,
                "file_size": file_size,
                "content_type": content_type,
                "object_url": object_url,
                "etag": result.etag,
                "version_id": result.version_id,
                "upload_timestamp": datetime.now().isoformat(),
                "metadata": upload_metadata,
            }

        except S3Error as e:
            logger.error(f"S3 error uploading file {file_path}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Storage upload failed: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading file {file_path}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Upload failed: {str(e)}"
            )

    def _get_content_type(self, filename: str) -> str:
        """Determine content type based on file extension.

        Args:
            filename: Name of the file

        Returns:
            MIME content type
        """
        # Get content type from mimetypes
        content_type, _ = mimetypes.guess_type(filename)

        # Default to octet-stream if no type is detected
        return content_type or "application/octet-stream"

    def upload_file_data(
        self,
        file_data: BinaryIO,
        object_key: str,
        file_size: int,
        content_type: str = "application/octet-stream",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Upload raw file data to Hetzner Object Storage.

        Args:
            file_data: Binary file data
            object_key: Object key for storage
            file_size: Size of the file in bytes
            content_type: MIME type of the file
            metadata: Optional metadata to attach to the object

        Returns:
            Dictionary with upload information
        """
        try:
            # Prepare metadata - convert to MinIO format
            # note: `content-type` is intentionally excluded from user
            # metadata; it is sent as the real Content-Type header via the
            # `content_type` argument. Including it as metadata causes an S3
            # SignatureDoesNotMatch on PUT for compatible servers.
            upload_metadata: MetadataType = {
                "upload-timestamp": datetime.now().isoformat(),
            }

            if metadata:
                # Ensure all metadata values are strings for MinIO
                string_metadata = {k: str(v) for k, v in metadata.items()}
                upload_metadata.update(string_metadata)

            # Create progress logger
            progress_logger = ProgressLogs(object_key)

            logger.info(
                f"Uploading data as {object_key} to bucket {self.bucket_name}"
            )

            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_key,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=upload_metadata,
                progress=progress_logger,
            )

            # Get object URL
            object_url = self.get_object_url(object_key)

            logger.info(f"Successfully uploaded data to {object_key}")

            return {
                "success": True,
                "object_key": object_key,
                "bucket_name": self.bucket_name,
                "file_size": file_size,
                "content_type": content_type,
                "object_url": object_url,
                "etag": result.etag,
                "version_id": result.version_id,
                "upload_timestamp": datetime.now().isoformat(),
                "metadata": upload_metadata,
            }

        except S3Error as e:
            logger.error(f"S3 error uploading data to {object_key}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Storage upload failed: {str(e)}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error uploading data to {object_key}: {e}"
            )
            raise HTTPException(
                status_code=500, detail=f"Upload failed: {str(e)}"
            )

    def get_object_url(self, object_key: str) -> str:
        """Get the public URL for an object.

        Args:
            object_key: Object key in storage

        Returns:
            Public URL for the object
        """
        if not settings.MINIO_PUBLIC_ENDPOINT:
            raise ValueError("HZ_OBJ_PUBLIC_ENDPOINT is required but not set")

        protocol = "https" if settings.MINIO_USE_SSL else "http"
        return f"{protocol}://{settings.MINIO_ENDPOINT}/{self.bucket_name}/{object_key}"

    def get_presigned_url(
        self,
        object_key: str,
        expires: timedelta = timedelta(hours=1),
        method: str = "GET",
    ) -> str:
        """Generate a presigned URL for temporary access to an object.

        Args:
            object_key: Object key in storage
            expires: Expiration time for the URL
            method: HTTP method (GET, PUT, DELETE, etc.)

        Returns:
            Presigned URL
        """
        try:
            if method.upper() == "GET":
                url = self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=object_key,
                    expires=expires,
                )
            elif method.upper() == "PUT":
                url = self.client.presigned_put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_key,
                    expires=expires,
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            return url

        except S3Error as e:
            logger.error(
                f"Error generating presigned URL for {object_key}: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate access URL: {str(e)}",
            )

    def delete_object(self, object_key: str) -> bool:
        """Delete an object from storage.

        Args:
            object_key: Object key to delete

        Returns:
            True if successful
        """
        try:
            self.client.remove_object(self.bucket_name, object_key)
            logger.info(f"Successfully deleted object: {object_key}")
            return True

        except S3Error as e:
            logger.error(f"Error deleting object {object_key}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file: {str(e)}"
            )

    def list_objects(
        self, prefix: str = "", max_keys: int = 1000
    ) -> list[dict[str, Any]]:
        """List objects in the bucket with optional prefix filter.

        Args:
            prefix: Prefix to filter objects
            max_keys: Maximum number of objects to return

        Returns:
            List of object information dictionaries
        """
        try:
            objects = []
            for obj in self.client.list_objects(
                bucket_name=self.bucket_name, prefix=prefix, recursive=True
            ):
                if len(objects) >= max_keys:
                    break

                # Skip objects without proper names
                if not obj.object_name:
                    continue

                objects.append(
                    {
                        "object_key": obj.object_name,
                        "size": obj.size,
                        "etag": obj.etag,
                        "last_modified": obj.last_modified.isoformat()
                        if obj.last_modified
                        else None,
                        "is_dir": obj.is_dir,
                        "object_url": self.get_object_url(obj.object_name),
                    }
                )

            return objects

        except S3Error as e:
            logger.error(f"Error listing objects with prefix {prefix}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to list objects: {str(e)}"
            )


# Global instance
_storage_client: HetznerStorageClient | None = None


def get_storage_client() -> HetznerStorageClient:
    """Get or create the global storage client instance."""
    global _storage_client

    if _storage_client is None:
        _storage_client = HetznerStorageClient()

    return _storage_client


# Convenience functions for direct usage
def upload_file_to_hetzner(
    file_path: str, prefix: str = "", metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Convenience function to upload a file to Hetzner storage.

    Args:
        file_path: Path to the file to upload
        prefix: Prefix for organizing files
        metadata: Optional metadata

    Returns:
        Upload result dictionary
    """
    client = get_storage_client()
    return client.upload_file(file_path, prefix=prefix, metadata=metadata)


def get_file_url(
    object_key: str, presigned: bool = False, expires_hours: int | float = 1
) -> str:
    """Convenience function to get a file URL.

    Args:
        object_key: Object key
        presigned: Whether to generate a presigned URL
        expires_hours: Expiration time in hours (can be fractional)

    Returns:
        File URL
    """
    client = get_storage_client()

    if presigned:
        return client.get_presigned_url(
            object_key, expires=timedelta(hours=expires_hours)
        )
    else:
        return client.get_object_url(object_key)


def get_object_key_from_url(
    url: str, bucket_name: str = settings.MINIO_BUCKET_NAME
) -> str | None:
    """Parses a URL to extract the object key, given the bucket name."""
    if not url or not bucket_name:
        return None
    try:
        parsed_url = urlparse(url)
        path = parsed_url.path
        bucket_prefix = f"/{bucket_name}/"
        if path.startswith(bucket_prefix):
            return path[len(bucket_prefix) :]
        return None
    except Exception:
        return None

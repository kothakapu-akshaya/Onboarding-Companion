"""Utility for managing chunked file uploads."""

import logging
import os
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class ChunkManager:
    """Manages chunked file uploads using file system storage."""

    def __init__(self, storage_path: str = "/tmp/chunks/"):
        """Initialize ChunkManager.

        Args:
            storage_path: Base directory for storing chunks
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.staging_path = Path("/tmp/staging/")
        self.staging_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"ChunkManager initialized with storage path: {self.storage_path}"
        )

    def save_chunk(
        self,
        upload_uuid: str,
        chunk_index: int,
        total_chunks: int,
        chunk_data: bytes,
    ) -> bool:
        """Save a chunk to the file system.

        Args:
            upload_uuid: Unique identifier for the upload session
            chunk_index: Index of the chunk (0-based)
            total_chunks: Total number of chunks expected
            chunk_data: Binary data of the chunk

        Returns:
            bool: True if chunk saved successfully, False otherwise
        """
        try:
            # Create upload directory
            upload_dir = self.storage_path / upload_uuid
            upload_dir.mkdir(exist_ok=True)

            # Create chunk filename
            chunk_filename = f"chunk_{chunk_index}_{total_chunks}.chunk"
            chunk_path = upload_dir / chunk_filename

            # Write chunk data
            with open(chunk_path, "wb") as f:
                f.write(chunk_data)

            logger.info(
                f"Saved chunk {chunk_index}/{total_chunks} "
                f"for upload {upload_uuid}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to save chunk {chunk_index} "
                f"for upload {upload_uuid}: {e}"
            )
            return False

    def combine_chunks(self, upload_uuid: str, filename: str) -> str | None:
        """Combine all chunks into a final file.

        Args:
            upload_uuid: Unique identifier for the upload session
            filename: Original filename for the combined file

        Returns:
            str: Path to the combined file, or None if failed
        """
        try:
            upload_dir = self.storage_path / upload_uuid

            if not upload_dir.exists():
                logger.error(f"Upload directory not found: {upload_dir}")
                return None

            # Get all chunk files and sort them by index
            chunk_files = []
            for chunk_file in upload_dir.glob("chunk_*_*.chunk"):
                try:
                    # Parse chunk filename to get index and total
                    parts = chunk_file.stem.split("_")
                    if len(parts) >= 3:
                        chunk_index = int(parts[1])
                        int(parts[2])
                        chunk_files.append((chunk_index, chunk_file))
                except (ValueError, IndexError):
                    logger.warning(f"Invalid chunk filename: {chunk_file}")
                    continue

            if not chunk_files:
                logger.error(f"No valid chunk files found in {upload_dir}")
                return None

            # Sort by chunk index
            chunk_files.sort(key=lambda x: x[0])

            # Check if we have all chunks
            expected_chunks = chunk_files[0][1].stem.split("_")[
                2
            ]  # Get total from first chunk
            if len(chunk_files) != int(expected_chunks):
                logger.error(
                    f"Missing chunks. Expected {expected_chunks}, "
                    f"found {len(chunk_files)}"
                )
                return None

            # Create temporary file for combined data
            with tempfile.NamedTemporaryFile(
                delete=False,
                dir=self.staging_path,
                prefix=f"{upload_uuid}_",
                suffix=os.path.splitext(filename)[1],
            ) as temp_file:
                combined_path = temp_file.name

                # Combine all chunks
                for chunk_index, chunk_file in chunk_files:
                    with open(chunk_file, "rb") as f:
                        temp_file.write(f.read())

                logger.info(
                    f"Successfully combined {len(chunk_files)} chunks "
                    f"into {combined_path}"
                )
                return combined_path

        except Exception as e:
            logger.error(
                f"Failed to combine chunks for upload {upload_uuid}: {e}"
            )
            return None

    def cleanup_chunks(self, upload_uuid: str) -> bool:
        """Remove chunk directory and all its contents.

        Args:
            upload_uuid: Unique identifier for the upload session

        Returns:
            bool: True if cleanup successful, False otherwise
        """
        try:
            upload_dir = self.storage_path / upload_uuid

            if upload_dir.exists():
                shutil.rmtree(upload_dir)
                logger.info(f"Cleaned up chunks for upload {upload_uuid}")
                return True
            else:
                logger.warning(
                    f"Upload directory not found for cleanup: {upload_dir}"
                )
                return (
                    True  # Consider this a success since the goal is achieved
                )

        except Exception as e:
            logger.error(
                f"Failed to cleanup chunks for upload {upload_uuid}: {e}"
            )
            return False

    def get_missing_chunks(
        self, upload_uuid: str, total_chunks: int
    ) -> list[int]:
        """Check which chunks are missing from the upload.

        Args:
            upload_uuid: Unique identifier for the upload session
            total_chunks: Total number of chunks expected

        Returns:
            List[int]: List of missing chunk indices
        """
        try:
            upload_dir = self.storage_path / upload_uuid

            if not upload_dir.exists():
                # If directory doesn't exist, all chunks are missing
                return list(range(total_chunks))

            # Get existing chunk files
            existing_chunks = set()
            for chunk_file in upload_dir.glob("chunk_*_*.chunk"):
                try:
                    parts = chunk_file.stem.split("_")
                    if len(parts) >= 2:
                        chunk_index = int(parts[1])
                        existing_chunks.add(chunk_index)
                except (ValueError, IndexError):
                    continue

            # Find missing chunks
            missing_chunks = []
            for i in range(total_chunks):
                if i not in existing_chunks:
                    missing_chunks.append(i)

            if missing_chunks:
                logger.info(
                    f"Missing chunks for upload {upload_uuid}: {missing_chunks}"
                )
            else:
                logger.info(f"All chunks present for upload {upload_uuid}")

            return missing_chunks

        except Exception as e:
            logger.error(
                f"Failed to check missing chunks for upload {upload_uuid}: {e}"
            )
            return list(
                range(total_chunks)
            )  # Assume all chunks missing on error

    def validate_chunk_sequence(
        self, upload_uuid: str, total_chunks: int
    ) -> bool:
        """Validate that all chunks are present and in sequence.

        Args:
            upload_uuid: Unique identifier for the upload session
            total_chunks: Total number of chunks expected

        Returns:
            bool: True if all chunks are present and valid, False otherwise
        """
        missing_chunks = self.get_missing_chunks(upload_uuid, total_chunks)
        return len(missing_chunks) == 0

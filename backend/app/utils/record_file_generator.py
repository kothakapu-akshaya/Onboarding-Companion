#!/usr/bin/env python3
"""Record File Generator utility for files with names matching record UIDs.

This utility generates sample files and uploads them to Hetzner storage
using the record's UID as the base filename.
"""

import asyncio
import logging
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

# Add the app directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from uuid import UUID

from sqlmodel import Session, select

from app.db.session import engine
from app.models.record import MediaType, Record
from app.utils.hetzner_storage import get_storage_client

logger = logging.getLogger(__name__)


class RecordFileGenerator:
    """Utility class for generating/uploading files with UID-based names."""

    def __init__(self):
        """Initialize the file generator."""
        self.storage_client = get_storage_client()

    def generate_sample_content(
        self, media_type: MediaType, file_size_kb: int = 10
    ) -> bytes:
        """Generate sample content based on media type.

        Args:
            media_type: Type of media to generate
            file_size_kb: Approximate size in KB for the generated content

        Returns:
            Sample content as bytes
        """
        # Calculate target size in bytes
        target_size = file_size_kb * 1024

        if media_type == MediaType.text:
            # Generate text content
            base_text = (
                "This is sample Indic languages corpus data for testing. " * 50
            )
            content = base_text
            while len(content.encode("utf-8")) < target_size:
                timestamp = datetime.now().isoformat()
                content += (
                    f"\nLine {len(content.split())} - "
                    f"Sample text content with timestamp {timestamp}"
                )
            return content.encode("utf-8")[:target_size]

        elif media_type == MediaType.audio:
            # Generate mock audio file content (fake MP3 header + data)
            mp3_header = b"\xff\xfb\x90\x00"  # Basic MP3 frame header
            content = mp3_header + b"SAMPLE_AUDIO_DATA_" * (target_size // 18)
            return content[:target_size]

        elif media_type == MediaType.video:
            # Generate mock video file content (fake MP4 header + data)
            mp4_header = b"\x00\x00\x00\x20\x66\x74\x79\x70"  # Basic MP4 header
            content = mp4_header + b"SAMPLE_VIDEO_DATA_" * (target_size // 18)
            return content[:target_size]

        elif media_type == MediaType.image:
            # Generate mock image content (fake JPEG header + data)
            jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # Basic JPEG header
            content = jpeg_header + b"SAMPLE_IMAGE_DATA_" * (target_size // 18)
            return content[:target_size]

        elif media_type == MediaType.document:
            # Generate mock document content (fake PDF header + data)
            pdf_header = b"%PDF-1.4\n"  # Basic PDF header
            content = pdf_header + b"SAMPLE_DOCUMENT_DATA_" * (
                target_size // 21
            )
            return content[:target_size]

        else:
            # Generic binary content
            return b"SAMPLE_BINARY_DATA_" * (target_size // 19)

    def get_file_extension(self, media_type: MediaType) -> str:
        """Get appropriate file extension for media type.

        Args:
            media_type: Type of media

        Returns:
            File extension including the dot
        """
        extensions = {
            MediaType.text: ".txt",
            MediaType.audio: ".mp3",
            MediaType.video: ".mp4",
            MediaType.image: ".jpg",
            MediaType.document: ".pdf",
        }
        return extensions.get(media_type, ".bin")

    def generate_filename_from_uid(
        self, record_uid: UUID, media_type: MediaType
    ) -> str:
        """Generate filename using record UID as base name.

        Args:
            record_uid: The record's UID
            media_type: Type of media for appropriate extension

        Returns:
            Filename in format: {uid}{extension}
        """
        extension = self.get_file_extension(media_type)
        return f"{str(record_uid)}{extension}"

    async def create_and_upload_file_for_record(
        self,
        record_uid: UUID,
        media_type: MediaType,
        file_size_kb: int = 10,
        custom_metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a file and upload it with the record UID as filename.

        Args:
            record_uid: The record's UID to use as filename base
            media_type: Type of media to generate
            file_size_kb: Size of file to generate in KB
            custom_metadata: Additional metadata to attach

        Returns:
            Upload result dictionary
        """
        try:
            # Generate content and filename
            content = self.generate_sample_content(media_type, file_size_kb)
            filename = self.generate_filename_from_uid(record_uid, media_type)

            # Determine content type
            content_types = {
                MediaType.text: "text/plain",
                MediaType.audio: "audio/mpeg",
                MediaType.video: "video/mp4",
                MediaType.image: "image/jpeg",
                MediaType.document: "application/pdf",
            }
            content_type = content_types.get(
                media_type, "application/octet-stream"
            )

            # Prepare metadata
            metadata = {
                "record_uid": str(record_uid),
                "media_type": media_type.value,
                "generated": "true",
                "generated_at": datetime.now().isoformat(),
                "file_size_kb": str(file_size_kb),
            }

            if custom_metadata:
                metadata.update(custom_metadata)

            # Create file object and upload using storage client directly
            file_obj = BytesIO(content)
            # Use media_type.value (e.g., "document" for document media type)
            folder_name = media_type.value
            object_key = f"{folder_name}/{filename}"

            result = self.storage_client.upload_file_data(
                file_data=file_obj,
                object_key=object_key,
                file_size=len(content),
                content_type=content_type,
                metadata=metadata,
            )

            logger.info(
                f"Successfully uploaded file for record {record_uid}: "
                f"{result['object_key']}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to create and upload file for record {record_uid}: {e}"
            )
            raise

    async def update_record_with_file_info(
        self, record_uid: UUID, upload_result: dict[str, Any]
    ) -> bool:
        """Update a record with the uploaded file information.

        Args:
            record_uid: The record's UID
            upload_result: Result from file upload

        Returns:
            True if successful
        """
        try:
            with Session(engine) as session:
                record = session.get(Record, record_uid)
                if not record:
                    logger.error(f"Record {record_uid} not found")
                    return False

                # Update record with file information
                record.file_url = upload_result["object_url"]
                # Extract filename from object_key
                # (e.g., "text/uuid.txt" -> "uuid.txt")
                object_key = upload_result["object_key"]
                filename = (
                    object_key.split("/")[-1]
                    if "/" in object_key
                    else object_key
                )
                record.file_name = filename
                record.file_size = upload_result["file_size"]
                record.status = "uploaded"
                record.updated_at = datetime.now()

                session.add(record)
                session.commit()
                session.refresh(record)

                logger.info(
                    f"Updated record {record_uid} with file information"
                )
                return True

        except Exception as e:
            logger.error(
                f"Failed to update record {record_uid} with file info: {e}"
            )
            return False

    async def process_record_with_file(
        self,
        record_uid: UUID,
        file_size_kb: int = 10,
        custom_metadata: dict[str, str] | None = None,
        update_record: bool = True,
    ) -> dict[str, Any]:
        """Process record: generate file, upload, and optionally update record.

        Args:
            record_uid: The record's UID
            file_size_kb: Size of file to generate
            custom_metadata: Additional metadata
            update_record: Whether to update the record with file info

        Returns:
            Combined result with upload and update info
        """
        try:
            # Get record to determine media type
            with Session(engine) as session:
                record = session.get(Record, record_uid)
                if not record:
                    raise ValueError(f"Record {record_uid} not found")

                media_type = record.media_type

            # Create and upload file
            upload_result = await self.create_and_upload_file_for_record(
                record_uid=record_uid,
                media_type=media_type,
                file_size_kb=file_size_kb,
                custom_metadata=custom_metadata,
            )

            # Update record if requested
            update_success = True
            if update_record:
                update_success = await self.update_record_with_file_info(
                    record_uid, upload_result
                )

            return {
                "record_uid": str(record_uid),
                "upload_result": upload_result,
                "record_updated": update_success,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Failed to process record {record_uid}: {e}")
            return {
                "record_uid": str(record_uid),
                "error": str(e),
                "success": False,
            }

    async def bulk_process_records(
        self,
        record_uids: list[UUID],
        file_size_kb: int = 10,
        update_records: bool = True,
    ) -> list[dict[str, Any]]:
        """Process multiple records with file generation and upload.

        Args:
            record_uids: List of record UIDs to process
            file_size_kb: Size of files to generate
            update_records: Whether to update records with file info

        Returns:
            List of results for each record
        """
        results = []

        for record_uid in record_uids:
            try:
                result = await self.process_record_with_file(
                    record_uid=record_uid,
                    file_size_kb=file_size_kb,
                    update_record=update_records,
                )
                results.append(result)

                # Small delay to avoid overwhelming the storage service
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Failed to process record {record_uid}: {e}")
                results.append(
                    {
                        "record_uid": str(record_uid),
                        "error": str(e),
                        "success": False,
                    }
                )

        return results

    def get_records_without_files(self, limit: int = 100) -> list[UUID]:
        """Get records that don't have associated files yet.

        This includes records that have local files instead of Hetzner storage.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of record UIDs without proper Hetzner storage files
        """
        try:
            with Session(engine) as session:
                # Get all records first
                all_records = session.exec(select(Record)).all()

                # Filter records that need Hetzner storage files
                records_needing_files = []
                for record in all_records:
                    if (
                        record.file_url is None
                        or record.file_url == ""
                        or record.file_url.startswith("/files/")
                    ):
                        records_needing_files.append(record)
                        if len(records_needing_files) >= limit:
                            break

                return [
                    record.uid
                    for record in records_needing_files
                    if record.uid is not None
                ]

        except Exception as e:
            logger.error(f"Failed to get records without files: {e}")
            return []


async def auto_generate_files_for_pending_records(
    limit: int = 50, file_size_kb: int = 15
) -> dict[str, Any]:
    """Automatically generate files for records that don't have them yet.

    Args:
        limit: Maximum number of records to process
        file_size_kb: Size of files to generate

    Returns:
        Summary of the operation
    """
    generator = RecordFileGenerator()

    # Get records without files
    record_uids = generator.get_records_without_files(limit)

    if not record_uids:
        return {
            "message": "No records without files found",
            "processed": 0,
            "results": [],
        }

    print(f"Found {len(record_uids)} records without files. Processing...")

    # Process them
    results = await generator.bulk_process_records(
        record_uids=record_uids, file_size_kb=file_size_kb, update_records=True
    )

    # Summary
    successful = len([r for r in results if r.get("success", False)])
    failed = len(results) - successful

    return {
        "message": f"Processed {len(results)} records",
        "successful": successful,
        "failed": failed,
        "results": results,
    }


if __name__ == "__main__":
    # Example usage
    async def main():  # noqa: D103
        print("🎯 Record File Generator - Creating files with record UID names")
        print("=" * 70)

        # Auto-generate files for records without them
        print("🔍 Looking for records without files...")
        result = await auto_generate_files_for_pending_records(
            limit=10, file_size_kb=20
        )

        print("\n📊 Summary:")
        print(f"   Message: {result['message']}")
        print(f"   Successful: {result.get('successful', 0)}")
        print(f"   Failed: {result.get('failed', 0)}")

        if result.get("results"):
            print("\n📋 Details:")
            for res in result["results"][:5]:  # Show first 5 results
                uid_short = res["record_uid"][:8]
                if res.get("success"):
                    upload_info = res.get("upload_result", {})
                    key = upload_info.get("object_key", "N/A")
                    print(f"   ✅ {uid_short}... -> {key}")
                else:
                    error = res.get("error", "Unknown error")
                    print(f"   ❌ {uid_short}... -> {error}")

        print("\n✨ File generation completed!")

    asyncio.run(main())

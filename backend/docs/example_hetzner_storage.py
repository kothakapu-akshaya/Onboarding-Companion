#!/usr/bin/env python3
"""Example usage of the Hetzner Object Storage utility.

This script demonstrates how to use the storage client in different scenarios.
"""

import asyncio
import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.utils.hetzner_storage import (
    HetznerStorageClient,
    upload_file_to_hetzner,
)


async def example_basic_usage():
    """Example: Basic file upload and management."""
    print("📝 Example 1: Basic File Upload")
    print("-" * 40)

    # Create some sample content
    content = b"This is a sample text file for demonstration."

    # Create a temporary file
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".txt", delete=False
    ) as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        # Upload the file
        result = await upload_file_to_hetzner(
            file_path=temp_file_path,
            prefix="examples/",
            metadata={
                "uploaded_by": "example_script",
                "category": "documentation",
            },
        )

        print("✅ File uploaded successfully!")
        print(f"   Object Key: {result['object_key']}")
        print(f"   Public URL: {result['object_url']}")
        print(f"   File Size: {result['file_size']} bytes")

        return result["object_key"]

    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except Exception:
            pass


async def example_file_management(object_key: str):
    """Example: File management operations."""
    print("\n🔧 Example 2: File Management")
    print("-" * 40)

    try:
        # Initialize client for direct operations
        client = HetznerStorageClient()

        # Get file URL
        public_url = client.get_object_url(object_key)
        print(f"🔗 Public URL: {public_url}")

        # Generate a presigned URL
        presigned_url = client.get_presigned_url(
            object_key, expires=timedelta(hours=1)
        )
        print(f"🔗 Presigned URL (1h): {presigned_url[:100]}...")

        # List objects with the same prefix
        prefix = "/".join(object_key.split("/")[:-1]) + "/"
        objects = client.list_objects(prefix=prefix, max_keys=10)
        print(f"📂 Files in prefix '{prefix}': {len(objects)}")

    except Exception as e:
        print(f"❌ File management failed: {e}")


async def example_media_organization():
    """Example: Organizing files by media type."""
    print("\n📱 Example 3: Media Type Organization")
    print("-" * 40)

    # Sample files for different media types
    media_files = [
        {
            "content": b"Sample audio file content",
            "filename": "sample.mp3",
            "media_type": "audio",
            "content_type": "audio/mpeg",
        },
        {
            "content": b"Sample video file content",
            "filename": "sample.mp4",
            "media_type": "video",
            "content_type": "video/mp4",
        },
        {
            "content": b"Sample image file content",
            "filename": "sample.jpg",
            "media_type": "image",
            "content_type": "image/jpeg",
        },
    ]

    uploaded_keys = []

    for media in media_files:
        try:
            # Create temporary file for each media type
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=os.path.splitext(media["filename"])[1],
                delete=False,
            ) as temp_file:
                temp_file.write(media["content"])
                temp_file_path = temp_file.name

            try:
                # Upload with media type prefix
                result = await upload_file_to_hetzner(
                    file_path=temp_file_path,
                    prefix=f"{media['media_type']}/",
                    metadata={
                        "media_type": media["media_type"],
                        "example": "media_organization",
                    },
                )

                uploaded_keys.append(result["object_key"])
                print(
                    f"✅ {media['media_type'].title()} uploaded: "
                    f"{result['object_key']}"
                )

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

        except Exception as e:
            print(f"❌ Failed to upload {media['filename']}: {e}")

    return uploaded_keys


async def example_bulk_operations():
    """Example: Bulk file operations."""
    print("\n📦 Example 4: Bulk Operations")
    print("-" * 40)

    try:
        client = HetznerStorageClient()

        # List all files with 'examples/' prefix
        objects = client.list_objects(prefix="examples/", max_keys=20)
        print(f"📂 Found {len(objects)} files in examples/ folder:")

        for obj in objects:
            print(f"   - {obj['object_key']} ({obj['size']} bytes)")

        # List audio files
        audio_objects = client.list_objects(prefix="audio/", max_keys=10)
        print(f"🎵 Found {len(audio_objects)} audio files:")

        for obj in audio_objects:
            print(f"   - {obj['object_key']}")

    except Exception as e:
        print(f"❌ Bulk operations failed: {e}")


async def cleanup_examples(object_keys: list):
    """Clean up example files."""
    print("\n🧹 Cleanup: Removing Example Files")
    print("-" * 40)

    client = HetznerStorageClient()
    for key in object_keys:
        try:
            success = client.delete_object(key)
            if success:
                print(f"✅ Deleted: {key}")
            else:
                print(f"❌ Failed to delete: {key}")
        except Exception as e:
            print(f"❌ Error deleting {key}: {e}")


async def main():
    """Run all examples."""
    print("🎯 Hetzner Object Storage Usage Examples")
    print("=" * 60)

    all_keys = []

    # Basic upload
    key1 = await example_basic_usage()
    if key1:
        all_keys.append(key1)

        # File management
        await example_file_management(key1)

    # Media organization
    media_keys = await example_media_organization()
    all_keys.extend(media_keys)

    # Bulk operations
    await example_bulk_operations()

    # Ask user if they want to clean up
    print(f"\n❓ Clean up example files? ({len(all_keys)} files)")
    response = input("Enter 'y' to delete example files: ").lower().strip()

    if response == "y":
        await cleanup_examples(all_keys)
    else:
        print("📝 Example files left in storage:")
        for key in all_keys:
            print(f"   - {key}")

    print("\n✨ Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())

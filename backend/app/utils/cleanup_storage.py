#!/usr/bin/env python3
"""Simple script to list and delete all objects from Hetzner Object Storage.

This is a standalone utility for cleaning up storage during development/testing.

Usage:
    python cleanup_storage.py list        # List all objects
    python cleanup_storage.py delete      # Delete all (with confirmation)
    python cleanup_storage.py delete --force  # Delete without confirmation
"""

import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.utils.hetzner_storage import get_storage_client


def list_all_objects():
    """List all objects in the storage bucket."""
    print(f"📦 Listing all objects in bucket: {settings.MINIO_BUCKET_NAME}")
    print("=" * 70)

    try:
        client = get_storage_client()
        objects = client.list_objects(prefix="", max_keys=10000)

        if not objects:
            print("✅ No objects found in storage.")
            return []

        print(f"Found {len(objects)} objects:")
        print()

        total_size = 0
        for i, obj in enumerate(objects, 1):
            size_mb = obj["size"] / (1024 * 1024)
            total_size += obj["size"]

            print(f"{i:3d}. {obj['object_key']}")
            print(f"     Size: {size_mb:.2f} MB")
            print(f"     URL: {obj['object_url']}")
            print(f"     Modified: {obj['last_modified']}")
            print()

        total_size_mb = total_size / (1024 * 1024)
        print(f"📊 Total: {len(objects)} objects, {total_size_mb:.2f} MB")

        return objects

    except Exception as e:
        print(f"❌ Error listing objects: {e}")
        return []


def delete_all_objects(force=False):
    """Delete all objects in the storage bucket."""
    print(
        f"🗑️  Preparing to delete all objects from bucket: "
        f"{settings.MINIO_BUCKET_NAME}"
    )
    print("=" * 70)

    try:
        client = get_storage_client()
        objects = client.list_objects(prefix="", max_keys=10000)

        if not objects:
            print("✅ No objects found to delete.")
            return

        print(f"Found {len(objects)} objects to delete:")
        for obj in objects:
            print(f"  - {obj['object_key']}")

        if not force:
            print(
                f"\n⚠️  WARNING: This will permanently delete "
                f"ALL {len(objects)} objects!"
            )
            print("This action cannot be undone.")

            response = input(
                "\nDo you want to continue? (type 'yes' to confirm): "
            )
            if response.lower() != "yes":
                print("❌ Operation cancelled.")
                return

        print(f"\n🗑️  Deleting {len(objects)} objects...")

        deleted_count = 0
        failed_count = 0

        for i, obj in enumerate(objects, 1):
            try:
                success = client.delete_object(obj["object_key"])
                if success:
                    deleted_count += 1
                    print(
                        f"✅ {i:3d}/{len(objects)} Deleted: {obj['object_key']}"
                    )
                else:
                    failed_count += 1
                    print(
                        f"❌ {i:3d}/{len(objects)} Failed: {obj['object_key']}"
                    )
            except Exception as e:
                failed_count += 1
                print(
                    f"❌ {i:3d}/{len(objects)} Error deleting "
                    f"{obj['object_key']}: {e}"
                )

        print("\n📊 Deletion Summary:")
        print(f"   ✅ Successfully deleted: {deleted_count}")
        print(f"   ❌ Failed to delete: {failed_count}")
        print(f"   📦 Total processed: {len(objects)}")

        if deleted_count > 0:
            print("\n🎉 Storage cleanup completed!")

    except Exception as e:
        print(f"❌ Error during deletion: {e}")


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cleanup_storage.py list        # List all objects")
        print(
            "  python cleanup_storage.py delete      # Delete all "
            "(with confirmation)"
        )
        print(
            "  python cleanup_storage.py delete --force  # Delete "
            "without confirmation"
        )
        return

    command = sys.argv[1].lower()

    if command == "list":
        list_all_objects()

    elif command == "delete":
        force = "--force" in sys.argv
        delete_all_objects(force=force)

    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: list, delete")


if __name__ == "__main__":
    print("🧹 Hetzner Storage Cleanup Utility")
    print("=" * 40)
    print(f"Bucket: {settings.MINIO_BUCKET_NAME}")
    print(f"Endpoint: {settings.MINIO_ENDPOINT}")
    print()

    main()

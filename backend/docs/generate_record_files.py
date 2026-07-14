#!/usr/bin/env python3
"""Generate and upload files with record UID-based names to Hetzner storage.

This script creates sample files and uploads them using the record's UID
as the filename.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.record_file_generator import (
    RecordFileGenerator,
    auto_generate_files_for_pending_records,
)


async def generate_file_for_specific_record(
    record_uid_str: str, file_size_kb: int = 15
):
    """Generate a file for a specific record UID."""
    try:
        record_uid = UUID(record_uid_str)
        print(f"🎯 Generating file for record: {record_uid}")
        print("-" * 50)

        generator = RecordFileGenerator()
        result = await generator.process_record_with_file(
            record_uid=record_uid, file_size_kb=file_size_kb, update_record=True
        )

        if result.get("success"):
            upload_info = result.get("upload_result", {})
            print("✅ File generated successfully!")
            print(f"   Record UID: {record_uid}")
            print(f"   Filename: {upload_info.get('original_filename', 'N/A')}")
            print(f"   Object Key: {upload_info.get('object_key', 'N/A')}")
            print(f"   File Size: {upload_info.get('file_size', 0)} bytes")
            print(f"   URL: {upload_info.get('object_url', 'N/A')}")
            print(f"   Record Updated: {result.get('record_updated', False)}")
        else:
            print(
                f"❌ Failed to generate file: "
                f"{result.get('error', 'Unknown error')}"
            )

    except ValueError as e:
        print(f"❌ Invalid UUID format: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def generate_files_for_multiple_records(
    record_uid_strs: list, file_size_kb: int = 15
):
    """Generate files for multiple record UIDs."""
    try:
        record_uids = [UUID(uid_str) for uid_str in record_uid_strs]
        print(f"🎯 Generating files for {len(record_uids)} records")
        print("-" * 50)

        generator = RecordFileGenerator()
        results = await generator.bulk_process_records(
            record_uids=record_uids,
            file_size_kb=file_size_kb,
            update_records=True,
        )

        successful = 0
        failed = 0

        for result in results:
            if result.get("success"):
                successful += 1
                upload_info = result.get("upload_result", {})
                print(
                    f"✅ {result['record_uid'][:8]}... -> "
                    f"{upload_info.get('object_key', 'N/A')}"
                )
            else:
                failed += 1
                print(
                    f"❌ {result['record_uid'][:8]}... -> "
                    f"{result.get('error', 'Unknown error')}"
                )

        print(f"\n📊 Summary: {successful} successful, {failed} failed")

    except ValueError as e:
        print(f"❌ Invalid UUID format: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def auto_generate_files(limit: int = 20, file_size_kb: int = 15):
    """Auto-generate files for records without them."""
    print(f"🔍 Auto-generating files for up to {limit} records without files")
    print("-" * 60)

    result = await auto_generate_files_for_pending_records(
        limit=limit, file_size_kb=file_size_kb
    )

    print(f"📊 {result['message']}")
    print(f"   Successful: {result.get('successful', 0)}")
    print(f"   Failed: {result.get('failed', 0)}")

    if result.get("results"):
        print("\n📋 Details:")
        for res in result["results"][:10]:  # Show first 10 results
            if res.get("success"):
                upload_info = res.get("upload_result", {})
                filename = upload_info.get("original_filename", "N/A")
                print(f"   ✅ {res['record_uid'][:8]}... -> {filename}")
            else:
                print(
                    f"   ❌ {res['record_uid'][:8]}... -> "
                    f"{res.get('error', 'Unknown error')}"
                )


async def list_records_without_files(limit: int = 20):
    """List records that don't have files yet."""
    print(f"📋 Records without files (showing up to {limit}):")
    print("-" * 50)

    generator = RecordFileGenerator()
    record_uids = generator.get_records_without_files(limit)

    if not record_uids:
        print("✅ All records have associated files!")
    else:
        print(f"Found {len(record_uids)} records without files:")
        for i, uid in enumerate(record_uids, 1):
            print(f"   {i:2d}. {uid}")


async def main():
    """Main entry point for record file generation."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate files with record UID-based names for Hetzner storage"
        )
    )

    parser.add_argument(
        "command",
        choices=["single", "multiple", "auto", "list"],
        help="Command to execute",
    )

    parser.add_argument(
        "--uid", "-u", help="Record UID for single file generation"
    )

    parser.add_argument(
        "--uids", nargs="+", help="Multiple record UIDs for bulk generation"
    )

    parser.add_argument(
        "--size",
        "-s",
        type=int,
        default=15,
        help="File size in KB (default: 15)",
    )

    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=20,
        help="Limit for auto-generation or listing (default: 20)",
    )

    args = parser.parse_args()

    print("🎯 Record File Generator with UID-based Names")
    print("=" * 60)

    if args.command == "single":
        if not args.uid:
            print("❌ Error: --uid is required for single file generation")
            return
        await generate_file_for_specific_record(args.uid, args.size)

    elif args.command == "multiple":
        if not args.uids:
            print("❌ Error: --uids is required for multiple file generation")
            return
        await generate_files_for_multiple_records(args.uids, args.size)

    elif args.command == "auto":
        await auto_generate_files(args.limit, args.size)

    elif args.command == "list":
        await list_records_without_files(args.limit)

    print("\n✨ Operation completed!")


if __name__ == "__main__":
    asyncio.run(main())

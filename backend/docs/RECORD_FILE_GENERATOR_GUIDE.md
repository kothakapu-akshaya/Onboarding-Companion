# Record File Generator - UID-based File Creation

This utility creates and uploads files to Hetzner Object Storage with filenames that match the record UIDs from the database. This ensures a direct mapping between database records and their associated files.

## Features

- **UID-based Naming**: Files are named using the record's UUID (e.g., `12345678-1234-5678-9012-123456789012.mp3`)
- **Media Type Support**: Generates appropriate content and extensions for text, audio, video, image, and document files
- **Automatic Organization**: Files are organized by media type in storage (`audio/`, `video/`, `image/`, `text/`, `document/`)
- **Database Integration**: Automatically updates records with file information after upload
- **Bulk Processing**: Can process multiple records simultaneously
- **Auto-discovery**: Finds records without files and generates them automatically

## File Naming Convention

Files are named using the record's UID with appropriate extensions:

```
{record_uid}{extension}
```

**Examples:**
- Text: `12345678-1234-5678-9012-123456789012.txt`
- Audio: `12345678-1234-5678-9012-123456789012.mp3`
- Video: `12345678-1234-5678-9012-123456789012.mp4`
- Image: `12345678-1234-5678-9012-123456789012.jpg`

## Storage Organization

Files are organized in Hetzner Object Storage with the following structure:

```
corpus-data/
├── audio/
│   ├── 12345678-1234-5678-9012-123456789012.mp3
│   └── 87654321-4321-8765-2109-cba987654321.mp3
├── video/
│   ├── abcdef12-3456-7890-abcd-ef1234567890.mp4
│   └── fedcba09-8765-4321-09ba-876543210fed.mp4
├── image/
│   └── 11111111-2222-3333-4444-555555555555.jpg
└── text/
    └── 99999999-8888-7777-6666-555555555555.txt
```

## Usage

### Command Line Interface

The `generate_record_files.py` script provides a command-line interface:

#### Generate file for a single record:
```bash
./generate_record_files.py single --uid 12345678-1234-5678-9012-123456789012 --size 25
```

#### Generate files for multiple records:
```bash
./generate_record_files.py multiple --uids 12345678-1234-5678-9012-123456789012 87654321-4321-8765-2109-cba987654321 --size 20
```

#### Auto-generate files for records without them:
```bash
./generate_record_files.py auto --limit 50 --size 30
```

#### List records without files:
```bash
./generate_record_files.py list --limit 20
```

### Python API

You can also use the utility programmatically:

#### Import the module:
```python
from app.utils.record_file_generator import (
    RecordFileGenerator,
    auto_generate_files_for_pending_records,
)
```

#### Generate file for a single record:
```python
import asyncio
from uuid import UUID

async def main():
    record_uid = UUID('12345678-1234-5678-9012-123456789012')
    generator = RecordFileGenerator()
    result = await generator.process_record_with_file(
        record_uid=record_uid,
        file_size_kb=25,
        update_record=True
    )
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        print(f"File URL: {result['upload_result']['object_url']}")

asyncio.run(main())
```

#### Auto-generate files for pending records:
```python
import asyncio

async def main():
    result = await auto_generate_files_for_pending_records(
        limit=50,
        file_size_kb=20
    )
    print(f"Processed: {result['successful']} successful, {result['failed']} failed")

asyncio.run(main())
```

#### Use the class directly for advanced operations:
```python
import asyncio
from uuid import UUID
from app.utils.record_file_generator import RecordFileGenerator

async def main():
    generator = RecordFileGenerator()
    
    # Find records without files
    record_uids = generator.get_records_without_files(limit=10)
    
    # Process them in bulk
    results = await generator.bulk_process_records(
        record_uids=record_uids,
        file_size_kb=15,
        update_records=True
    )
    
    for result in results:
        if result.get('success'):
            print(f"✅ {result['record_uid'][:8]}...")
        else:
            print(f"❌ {result['record_uid'][:8]}... - {result.get('error')}")

asyncio.run(main())
```

## Generated File Content

The utility generates sample content appropriate for each media type:

### Text Files (.txt)
- UTF-8 encoded text content
- Includes sample Indic languages corpus data
- Multiple lines with timestamps
- Configurable size

### Audio Files (.mp3)
- Mock MP3 format with basic frame header
- Binary content simulating audio data
- Appropriate for testing audio processing workflows

### Video Files (.mp4)
- Mock MP4 format with container header
- Binary content simulating video data
- Suitable for video processing pipeline testing

### Image Files (.jpg)
- Mock JPEG format with file header
- Binary content simulating image data
- Compatible with image processing systems

## Configuration

The utility uses the same Hetzner Object Storage configuration as the main application:

```env
HZ_OBJ_ENDPOINT=hel1.your-objectstorage.com
HZ_OBJ_ACCESS_KEY=your_access_key
HZ_OBJ_SECRET_KEY=your_secret_key
HZ_OBJ_BUCKET_NAME=corpus-data
HZ_OBJ_USE_SSL=true
```

## Database Integration

### Record Updates

When `update_record=True` (default), the utility automatically updates the database record with:

- `file_url`: Public URL of the uploaded file
- `file_name`: Original filename (UID-based)
- `file_size`: Actual size of the uploaded file
- `status`: Set to "uploaded"
- `updated_at`: Current timestamp

### Metadata

Each uploaded file includes metadata:

```python
{
    "record_uid": "12345678-1234-5678-9012-123456789012",
    "media_type": "audio",
    "generated": "true",
    "generated_at": "2025-06-03T19:30:45.123456",
    "file_size_kb": "25"
}
```

## Error Handling

The utility includes comprehensive error handling:

- **Database Connection**: Graceful handling of database connectivity issues
- **Storage Upload**: Retry logic and detailed error reporting for upload failures
- **File Generation**: Validation of content generation and size limits
- **UUID Validation**: Proper validation of record UID formats
- **Record Existence**: Verification that records exist before processing

## Performance Considerations

### Bulk Processing
- Small delays between uploads to avoid overwhelming the storage service
- Configurable batch sizes for large datasets
- Progress reporting for long-running operations

### File Sizes
- Default file size: 15KB (configurable)
- Recommended range: 1KB - 100KB for testing
- Respects the application's MAX_FILE_SIZE setting

### Concurrency
- Uses async/await for non-blocking operations
- Suitable for integration with FastAPI applications
- Can be run alongside web server operations

## Examples

### Real-world Usage Scenarios

#### 1. Initial Data Population
```bash
# Generate files for all records without them
./generate_record_files.py auto --limit 1000 --size 50
```

#### 2. Testing Specific Records
```bash
# Test with specific record UIDs
./generate_record_files.py multiple --uids \
  12345678-1234-5678-9012-123456789012 \
  87654321-4321-8765-2109-cba987654321 \
  --size 25
```

#### 3. Development Environment Setup
```bash
# Quick setup with smaller files
./generate_record_files.py auto --limit 20 --size 10
```

#### 4. Quality Assurance Testing
```bash
# Generate larger files for QA testing
./generate_record_files.py auto --limit 100 --size 100
```

## Integration with Records API

The generated files work seamlessly with the existing records API:

```python
# The upload endpoint will use the generated files
@router.post("/upload", response_model=RecordRead)
async def upload_record_file(...):
    # Files created by this utility are already in the correct format
    # and location for the API to reference
```

## Monitoring and Logging

The utility provides detailed logging:

- File generation progress
- Upload success/failure details
- Database update results
- Error conditions and recovery attempts

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.INFO)

# Run with detailed output
generator = RecordFileGenerator()
```

## Best Practices

1. **Start Small**: Begin with small file sizes (10-20KB) for testing
2. **Monitor Storage**: Keep track of storage usage and costs
3. **Regular Cleanup**: Remove test files when no longer needed
4. **Backup Strategy**: Ensure proper backup of generated data
5. **Validation**: Verify file uploads and database updates after bulk operations

## Troubleshooting

### Common Issues

#### "No records found"
- Ensure the database contains records
- Check database connection configuration
- Verify record creation has completed

#### "Upload failed"
- Verify Hetzner Object Storage credentials
- Check network connectivity
- Ensure bucket exists and is accessible

#### "Invalid UUID format"
- Verify record UID format is correct
- Use proper UUID string representation
- Check for extra whitespace or characters

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run operations with full debug output
```

## Security Considerations

- Generated files contain only sample data (not sensitive information)
- Files are uploaded to configured storage with proper access controls
- Metadata includes generation timestamps for audit purposes
- Database updates maintain referential integrity

This utility provides a complete solution for creating and managing files with record UID-based names, ensuring perfect alignment between your database records and their associated files in Hetzner Object Storage.

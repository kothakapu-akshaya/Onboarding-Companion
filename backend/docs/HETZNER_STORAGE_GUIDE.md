# Hetzner Object Storage Integration

This utility provides seamless integration with Hetzner Object Storage using the MinIO Python SDK. Hetzner Object Storage is S3-compatible, making it easy to use existing S3 tools and libraries.

## Features

- ✅ **File Upload**: Upload files with automatic key generation and metadata
- ✅ **File Management**: Check existence, get info, and delete files
- ✅ **URL Generation**: Generate public and presigned URLs
- ✅ **Bulk Operations**: List and manage multiple files
- ✅ **Error Handling**: Comprehensive error handling with proper HTTP status codes
- ✅ **Size Validation**: Automatic file size validation against configured limits
- ✅ **Media Organization**: Organize files by type using prefixes
- ✅ **Metadata Support**: Attach custom metadata to uploaded files

## Setup

### 1. Environment Variables

Add the following variables to your `.env` file:

```bash
# Hetzner Object Storage Configuration
HZ_OBJ_ENDPOINT="your-hetzner-endpoint.com"
HZ_OBJ_ACCESS_KEY="your-access-key"
HZ_OBJ_SECRET_KEY="your-secret-key"
HZ_OBJ_BUCKET_NAME="corpus-data"
HZ_OBJ_USE_SSL="true"
```

### 2. Dependencies

The MinIO client is already included in the project dependencies:

```toml
dependencies = [
    # ... other dependencies
    "minio",
    # ...
]
```

## Usage

### Basic Upload

```python
from app.utils.hetzner_storage import upload_file_to_hetzner

async def upload_file(file_path: str):
    result = await upload_file_to_hetzner(
        file_path=file_path,
        prefix="documents/",
        metadata={
            "uploaded_by": "user_123",
            "category": "important"
        }
    )
    return result
```

### Direct Client Usage

```python
from app.utils.hetzner_storage import HetznerStorageClient

# Initialize client
client = HetznerStorageClient()

# Check if file exists
exists = client.object_exists("documents/myfile.pdf")

# Get file information
info = client.get_object_info("documents/myfile.pdf")

# Generate presigned URL (1 hour expiry)
url = client.get_presigned_url("documents/myfile.pdf", expires=timedelta(hours=1))

# Delete file
success = client.delete_object("documents/myfile.pdf")
```

### File Organization

Organize files by media type or category using prefixes:

```python
# Audio files
await upload_file_to_hetzner(audio_file_path, prefix="audio/")

# Video files
await upload_file_to_hetzner(video_file_path, prefix="video/")

# User uploads
await upload_file_to_hetzner(user_file_path, prefix=f"users/{user_id}/")

# Category-based organization
await upload_file_to_hetzner(file_path, prefix=f"categories/{category_name}/")
```

## API Integration

### FastAPI Endpoint Example

```python
from fastapi import APIRouter, UploadFile, File, Form
from app.utils.hetzner_storage import upload_file_to_hetzner
import tempfile
import os

router = APIRouter()

@router.post("/upload")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    category: str = Form(...),
    user_id: str = Form(...)
):
    """Upload file to Hetzner Object Storage."""
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            result = await upload_file_to_hetzner(
                file_path=temp_file_path,
                prefix=f"{category}/",
                metadata={
                    "user_id": user_id,
                    "category": category,
                    "upload_time": datetime.now().isoformat()
                }
            )

            return {
                "success": True,
                "file_url": result["object_url"],
                "object_key": result["object_key"],
                "file_size": result["file_size"]
            }

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Records Integration

The utility is already integrated into the records API:

```python
# In app/api/v1/endpoints/records.py

@router.post("/upload", response_model=RecordRead)
async def upload_record(
    file: UploadFile = File(...),
    title: str = Form(...),
    media_type: MediaType = Form(...),
    # ... other fields
):
    # File upload to Hetzner
    upload_result = await upload_file_to_hetzner(
        file=file,
        prefix=f"{media_type.value}/",
        metadata={
            "title": title,
            "media_type": media_type.value
        }
    )

    # Create record with file info
    record = Record(
        title=title,
        media_type=media_type,
        file_url=upload_result["object_url"],
        file_name=file.filename,
        file_size=upload_result["file_size"],
        status="uploaded"
    )
    # ... save to database
```

## Configuration Options

### File Size Limits

```python
# In app/core/config.py
MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB default
```

### Allowed File Extensions

```python
ALLOWED_AUDIO_EXTENSIONS: set[str] = {".mp3", ".wav", ".m4a", ".ogg"}
ALLOWED_VIDEO_EXTENSIONS: set[str] = {".mp4", ".avi", ".mov", ".mkv"}
ALLOWED_IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".gif"}
```

## Error Handling

The utility provides comprehensive error handling:

```python
try:
    result = await upload_file_to_hetzner(file)
except HTTPException as e:
    # Handle specific HTTP errors
    if e.status_code == 413:
        print("File too large")
    elif e.status_code == 500:
        print("Storage error")
except Exception as e:
    # Handle unexpected errors
    print(f"Unexpected error: {e}")
```

## Testing

### Run Tests

```bash
# Test the storage utility
python test_hetzner_storage.py

# Run examples
python example_hetzner_storage.py
```

### Test Coverage

The test script covers:

- ✅ Configuration validation
- ✅ Client initialization
- ✅ File upload/download
- ✅ Object existence checks
- ✅ Metadata handling
- ✅ URL generation
- ✅ File deletion
- ✅ Large file validation
- ✅ Bulk operations

## Security Considerations

### Access Control

- Use presigned URLs for temporary access
- Set appropriate expiry times
- Validate file types and sizes
- Sanitize file names

### Metadata Security

```python
# Safe metadata (avoid sensitive data)
metadata = {
    "category": "public_documents",
    "upload_time": datetime.now().isoformat(),
    "file_type": "pdf"
}

# Avoid sensitive data in metadata
# ❌ metadata = {"user_password": "secret123"}
```

## Performance Tips

### Upload Optimization

1. **Use appropriate prefixes** for organization
2. **Set reasonable file size limits**
3. **Use metadata for filtering** instead of downloading files
4. **Cache file URLs** when possible

### Bulk Operations

```python
# Efficient listing with pagination
objects = client.list_objects(prefix="audio/", max_keys=100)

# Use presigned URLs for browser uploads
presigned_url = client.get_presigned_url(object_key, method="PUT")
```

## Monitoring and Logging

The utility includes comprehensive logging:

```python
import logging

# Configure logging level
logging.getLogger("app.utils.hetzner_storage").setLevel(logging.INFO)
```

Log levels:

- `INFO`: Successful operations
- `WARNING`: Non-critical issues (e.g., file deletion failures)
- `ERROR`: Critical errors requiring attention

## Troubleshooting

### Common Issues

1. **"Missing credentials"**

   - Check `.env` file has all required variables
   - Verify variable names match exactly

2. **"Bucket access denied"**

   - Verify access key has bucket permissions
   - Check bucket name is correct

3. **"SSL certificate errors"**

   - Set `HZ_OBJ_USE_SSL="false"` for testing
   - Verify endpoint URL format

4. **"File upload fails"**
   - Check file size against `MAX_FILE_SIZE`
   - Verify file is not corrupted
   - Check network connectivity

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test configuration
from app.core.config import settings
print(f"Endpoint: {settings.MINIO_ENDPOINT}")
print(f"Bucket: {settings.MINIO_BUCKET_NAME}")
```

## Production Considerations

### Environment Variables

```bash
# Production .env
HZ_OBJ_ENDPOINT="your-production-endpoint.com"
HZ_OBJ_ACCESS_KEY="prod-access-key"
HZ_OBJ_SECRET_KEY="prod-secret-key"
HZ_OBJ_BUCKET_NAME="corpus-production"
HZ_OBJ_USE_SSL="true"
MAX_FILE_SIZE=104857600  # 100MB
```

### Backup Strategy

- Enable versioning on your bucket
- Set up lifecycle policies for old files
- Monitor storage usage and costs
- Implement regular backup verification

### Scaling Considerations

- Use CDN for frequently accessed files
- Implement file deduplication if needed
- Monitor API rate limits
- Consider multi-region setup for high availability

## API Reference

### HetznerStorageClient

#### Methods

- `__init__()` - Initialize client with credentials
- `upload_file(file, object_key, prefix, metadata)` - Upload file
- `delete_object(object_key)` - Delete file
- `object_exists(object_key)` - Check if file exists
- `get_object_info(object_key)` - Get file metadata
- `get_object_url(object_key)` - Get public URL
- `get_presigned_url(object_key, expires, method)` - Get presigned URL
- `list_objects(prefix, max_keys)` - List files

### Convenience Functions

- `upload_file_to_hetzner(file, prefix, metadata)` - Upload file
- `get_file_url(object_key, presigned, expires_hours)` - Get URL

For deletion, use the `HetznerStorageClient.delete_object()` method directly.

## License

This utility is part of the Indic languages Corpus Collections API project.

# Chunked File Upload Specification

## 📋 Overview

This document outlines the implementation of chunked file upload functionality for the records API. The system allows large files to be uploaded in smaller chunks and then reassembled on the server before being processed through the existing Hetzner storage system.

## 🎯 Requirements

- **Chunk-based uploads**: Files uploaded in configurable chunk sizes (10MB maximum per chunk)
- **File system storage**: Chunks stored in `/tmp/chunks/{uuid}/` directory
- **No database storage**: Chunks stored only in file system for performance
- **Backward compatibility**: Existing upload endpoint continues to work
- **Automatic cleanup**: Remove chunk directories after successful upload
- **Error handling**: Handle missing chunks and upload failures gracefully

## 🏗️ Architecture

### Chunk Storage Structure

```
/tmp/chunks/
├── {upload_uuid}/
│   ├── chunk_0_10.chunk
│   ├── chunk_1_10.chunk
│   ├── chunk_2_10.chunk
│   └── ...
```

### API Endpoints

1. `POST /api/v1/records/upload/chunk` - Upload individual chunk
2. `POST /api/v1/records/upload` - Finalize chunked upload (requires upload_uuid)

## 📝 Implementation Plan

### Phase 1: Core Implementation

#### Step 1: Create Chunk Management Utility

**File**: `app/utils/chunk_manager.py`

- Create `ChunkManager` class with essential methods:
  - `save_chunk(uuid, chunk_index, total_chunks, chunk_data)` - save to `/tmp/chunks/{uuid}/chunk_{index}_{total}.chunk`
  - `combine_chunks(uuid, filename)` - combine all chunks into final file
  - `cleanup_chunks(uuid)` - remove chunk directory
  - `get_missing_chunks(uuid, total_chunks)` - check which chunks exist

#### Step 2: Add Chunk Upload Endpoint

**File**: `app/api/v1/endpoints/records.py`

- Add `@router.post("/upload/chunk")` endpoint:
  - Accept chunk data, filename, chunk_index, total_chunks, upload_uuid
  - Frontend generates and sends upload_uuid in every chunk call
  - Enforce 10MB maximum chunk size limit
  - Save chunk to file system using provided upload_uuid
  - Return success status

#### Step 3: Modify Existing Upload Endpoint

**File**: `app/api/v1/endpoints/records.py`

- Modify `@router.post("/upload")` endpoint:
  - Add required `upload_uuid` parameter
  - Combine chunks from `/tmp/chunks/{uuid}/`
  - Use existing file processing logic
  - Clean up chunk directory after success
  - This endpoint is specifically for chunked uploads

## ✅ Todo List

### Core Implementation

- [ ] Create `app/utils/chunk_manager.py` with ChunkManager class
- [ ] Implement `save_chunk()` method
- [ ] Implement `combine_chunks()` method
- [ ] Implement `cleanup_chunks()` method
- [ ] Implement `get_missing_chunks()` method
- [ ] Add chunk upload endpoint to records.py
- [ ] Modify existing upload endpoint to require upload_uuid
- [ ] Add chunk storage path configuration

### Error Handling

- [ ] Handle missing chunks gracefully
- [ ] Implement chunk size validation (10MB maximum)
- [ ] Add file size limits
- [ ] Handle upload timeout scenarios
- [ ] Add proper error responses

### Security & Validation

- [ ] Add authentication to chunk endpoints
- [ ] Validate chunk parameters
- [ ] Sanitize UUID and filename inputs
- [ ] Implement rate limiting for chunk uploads

### Testing

- [ ] Create unit tests for ChunkManager
- [ ] Test chunk upload endpoint
- [ ] Test chunk combination functionality
- [ ] Test error scenarios
- [ ] Test backward compatibility

### Documentation

- [ ] Update API documentation
- [ ] Add usage examples
- [ ] Document error codes
- [ ] Add troubleshooting guide

### Cleanup & Maintenance

- [ ] Implement automatic cleanup for orphaned chunks
- [ ] Add cleanup job for chunks older than 24 hours
- [ ] Monitor disk usage for chunk storage

## 🔧 Configuration

### Required Settings

```python
# app/core/config.py
CHUNK_STORAGE_PATH = "/tmp/chunks/"
CHUNK_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB maximum per chunk
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
CHUNK_CLEANUP_HOURS = 24
```

## 🚀 Usage Example

### Frontend Implementation

```javascript
const CHUNK_SIZE = 10 * 1024 * 1024; // 10 MB maximum

async function uploadFile(file) {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  const uploadUuid = crypto.randomUUID(); // Generate UUID on frontend

  for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
    const start = chunkIndex * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const chunk = file.slice(start, end);

    const formData = new FormData();
    formData.append("chunk", chunk);
    formData.append("filename", file.name);
    formData.append("chunk_index", chunkIndex);
    formData.append("total_chunks", totalChunks);
    formData.append("upload_uuid", uploadUuid); // Send UUID with every chunk

    const response = await fetch("/api/v1/records/upload/chunk", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Chunk ${chunkIndex} upload failed`);
    }
  }

  // Finalize upload
  const finalizeData = new FormData();
  finalizeData.append("upload_uuid", uploadUuid);
  finalizeData.append("title", "My File");
  finalizeData.append("category_id", "category-uuid");
  finalizeData.append("user_id", "user-uuid");
  finalizeData.append("media_type", "video");

  await fetch("/api/v1/records/upload", {
    method: "POST",
    body: finalizeData,
  });
}
```

## 📊 Benefits

- **Performance**: Direct file I/O, no database overhead
- **Simplicity**: File system storage only, minimal complexity
- **Scalability**: Handles large files efficiently
- **Reliability**: File system operations are atomic
- **Compatibility**: Maintains existing API functionality

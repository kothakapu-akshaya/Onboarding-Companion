# Duration Seconds Feature Specification

## 📋 Overview

This document outlines the implementation of the `duration_seconds` field for the Record model. This field stores the duration of media files (primarily audio and video) in seconds and is auto-calculated during file upload/generation.

## 🎯 Requirements

- **Read-only field**: Users cannot set duration manually
- **Auto-calculated**: Duration is extracted from uploaded files or estimated for generated files
- **Optional**: Field can be null for records without duration (e.g., text files, images)
- **Non-negative**: Duration must be >= 0 seconds
- **Media-specific**: Most relevant for audio and video files

## ✅ Completed Work

### Step 1: Database Model Changes ✅

**File**: `app/models/record.py`

- Added `duration_seconds: Optional[int] = Field(default=None, ge=0)` to Record model
- Added descriptive comment: `# Duration in seconds (auto-calculated, read-only)`
- Added validation with `ge=0` for non-negative values

### Step 2: Pydantic Schema Updates ✅

**File**: `app/schemas/__init__.py`

- Added `duration_seconds: Optional[int] = Field(None, ge=0)` to `RecordRead` schema only
- **NOT** added to `RecordBase`, `RecordCreate`, or `RecordUpdate` schemas
- Ensures field is only present in GET responses, not in POST/PUT requests
- Added comment: `# Duration in seconds (read-only)`

### Step 3: Database Migration ✅

**File**: `alembic/versions/118966d219d7_add_duration_seconds_to_record.py`

- Created Alembic migration to add `duration_seconds` column
- **Revision ID**: `118966d219d7`
- **Down Revision**: `aafaf157ff08`
- **Migration Logic**:

  ```python
  def upgrade() -> None:
      op.add_column('record', sa.Column('duration_seconds', sa.Integer(), nullable=True))

  def downgrade() -> None:
      op.drop_column('record', 'duration_seconds')
  ```

## 🔄 Remaining Steps

### Step 4: API Endpoint Updates

**File**: `app/api/v1/endpoints/records.py`

#### 4.1 GET Endpoints (Automatic)

- All existing GET endpoints will automatically include `duration_seconds` in responses
- No code changes needed - handled by `RecordRead` schema

#### 4.2 POST/PUT Endpoints (Automatic)

- All existing POST/PUT endpoints will automatically ignore `duration_seconds` if provided
- No code changes needed - field not in input schemas

#### 4.3 File Upload Endpoint Enhancement

**Endpoint**: `POST /records/upload`

- Add duration calculation logic for uploaded files
- Set `duration_seconds` field after successful file upload
- Handle cases where duration cannot be calculated

**Implementation Details**:

```python
# After successful file upload, calculate duration
if media_type in [MediaType.audio, MediaType.video]:
    duration = await calculate_file_duration(uploaded_file)
    record_data.duration_seconds = duration
```

### Step 5: Duration Calculation Utility

**File**: `app/utils/duration_calculator.py` (new file)

#### 5.1 Core Functions

```python
async def calculate_file_duration(file_path: str, media_type: MediaType) -> Optional[int]:
    """Calculate duration of uploaded file in seconds."""

async def extract_audio_duration(file_path: str) -> Optional[int]:
    """Extract duration from audio files (mp3, wav, etc.)."""

async def extract_video_duration(file_path: str) -> Optional[int]:
    """Extract duration from video files (mp4, avi, etc.)."""

def estimate_generated_duration(media_type: MediaType, file_size: int) -> int:
    """Estimate duration for generated files based on type and size."""
```

#### 5.2 Dependencies

- Consider using `ffmpeg-python` or `pydub` for audio/video processing
- Handle common formats: mp3, mp4, wav, avi, mov, etc.
- Graceful error handling for unsupported formats

### Step 6: File Generator Updates

**File**: `app/utils/record_file_generator.py`

#### 6.1 Update `create_and_upload_file_for_record()`

- Add duration calculation for generated files
- Set realistic durations based on media type and content
- Update record with calculated duration

#### 6.2 Duration Estimation Logic

```python
def get_estimated_duration(media_type: MediaType, content_length: int) -> int:
    """Estimate duration based on media type and content."""
    if media_type == MediaType.audio:
        return max(30, content_length // 1000)  # ~1 second per KB
    elif media_type == MediaType.video:
        return max(10, content_length // 5000)  # ~1 second per 5KB
    elif media_type == MediaType.text:
        return None  # Text files don't have duration
    else:
        return None
```

### Step 7: Testing Updates

**Files**: Various test files in `tests/` directory

#### 7.1 Test Data Updates

- Update test data creation to include `duration_seconds`
- Add test cases for different media types and durations

#### 7.2 API Testing

- Test that `duration_seconds` is included in GET responses
- Test that `duration_seconds` is NOT accepted in POST/PUT requests
- Test duration calculation for different file types
- Test error handling for unsupported formats

#### 7.3 Unit Tests

```python
def test_duration_calculation_audio():
    """Test audio file duration calculation."""

def test_duration_calculation_video():
    """Test video file duration calculation."""

def test_duration_estimation_generated():
    """Test duration estimation for generated files."""

def test_duration_validation():
    """Test duration field validation."""
```

### Step 8: Documentation Updates

**Files**: Various documentation files in `docs/`

#### 8.1 API Documentation

- Document that `duration_seconds` is read-only
- Add examples showing duration in GET responses
- Update file upload documentation

#### 8.2 Implementation Guide

- Document duration calculation process
- List supported file formats
- Explain error handling

### Step 9: Optional Enhancements

#### 9.1 Duration-based Filtering

**Endpoint**: `GET /records/`

- Add query parameters for duration filtering:
  - `min_duration: Optional[int]` - Minimum duration in seconds
  - `max_duration: Optional[int]` - Maximum duration in seconds
  - `duration_range: Optional[str]` - Predefined ranges (short, medium, long)

#### 9.2 Duration-based Sorting

- Add sorting options:
  - `sort_by: str = "duration"` - Sort by duration
  - `sort_order: str = "asc"` - Ascending/descending order

#### 9.3 Duration Statistics

**Endpoint**: `GET /records/stats/duration`

- Return duration statistics:
  - Average duration by media type
  - Duration distribution
  - Total duration across all records

## 🔧 Technical Implementation Details

### Database Schema

```sql
ALTER TABLE record ADD COLUMN duration_seconds INTEGER;
```

### API Response Example

```json
{
  "uid": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Sample Audio File",
  "media_type": "audio",
  "duration_seconds": 180,
  "file_url": "https://...",
  "created_at": "2025-07-16T11:30:00Z",
  "updated_at": "2025-07-16T11:30:00Z"
}
```

### Error Handling

- **Unsupported format**: Set `duration_seconds` to `null`
- **Corrupted file**: Set `duration_seconds` to `null`
- **Processing error**: Log error, set `duration_seconds` to `null`

### Performance Considerations

- Duration calculation should be asynchronous for large files
- Consider caching duration values
- Implement timeout for duration extraction

## 🚀 Deployment Checklist

- [ ] Apply database migration: `alembic upgrade head`
- [ ] Deploy updated code with duration calculation logic
- [ ] Test duration calculation with sample files
- [ ] Monitor performance impact of duration extraction
- [ ] Update API documentation
- [ ] Train users on new duration field

## 📝 Notes

- Duration calculation is best effort - some files may not have extractable duration
- Text and image files typically don't have meaningful duration
- Consider adding duration validation based on media type
- Future enhancement: Add duration-based search and analytics

# Extracted Text and Collaborative Corrections Feature

## Overview

This feature extends the records table to support storing text extracted via OCR/ASR/Captioning and allows collaborative user corrections with full audit trails. The implementation integrates with the existing wiki-style versioning system.

## Database Schema Changes

### Records Table Extensions

The `records` table has been extended with one new field:

- `extracted_text` (JSONB, nullable) - Stores extracted text from OCR/ASR/Captioning. All changes are versioned through the existing `RecordHistory` system.

## Data Storage Strategy

### Why JSONB for ASR/OCR/Captioning Data

JSONB was chosen as the optimal storage format for extracted text data due to the diverse and evolving nature of AI extraction outputs:

#### **1. Flexible Structure Across Extraction Types**
- **OCR**: Needs bounding boxes, confidence per word, layout information
- **ASR**: Requires timestamps, speaker identification, confidence scores
- **Captioning**: May include styling, positioning, speaker labels
- **Manual**: User corrections with change tracking and quality metrics

#### **2. Schema Evolution Without Migrations**
- New AI models can add fields (speaker_emotion, text_quality_score) without database changes
- Backwards compatibility maintained as existing fields remain accessible
- Future ML features integrate seamlessly (sentiment analysis, topic classification)

#### **3. Native PostgreSQL Query Performance**
- GIN indexes on JSONB fields enable fast nested searches
- Query segments by timestamp ranges, confidence thresholds, or bounding boxes
- Filter corrections by type, user, or confidence improvement metrics
- Aggregate statistics across nested arrays efficiently

#### **4. Atomic Operations and Consistency**
- Single field updates ensure data consistency during user corrections
- No synchronization issues between separate AI and user text tables
- Version control operates on complete text objects, not fragmented data

#### **5. Storage Efficiency**
- Binary JSON format compresses repetitive metadata structure
- Shared dictionary compression for common field names across records
- Eliminates JOIN operations needed with normalized table approaches

### JSONB Data Integrity and Validation Pipeline

The system implements a comprehensive validation pipeline to ensure JSONB data integrity and prevent corruption:

#### **Multi-Layer Validation Process**
1. **Input Sanitization** - Removes null bytes, control characters, and dangerous Unicode
2. **Unicode Normalization** - NFKC normalization prevents homograph attacks
3. **JSON Serialization Testing** - Every field tested with `json.dumps()` before storage
4. **Key Sanitization** - Blocks reserved keys (`__proto__`, `constructor`) and sanitizes names
5. **Length Limits** - Enforced limits prevent oversized data (transcription: 50KB, metadata: 10KB)
6. **PII Detection** - Automatic warnings for potential personal information patterns

#### **Validation Rules by Field Type**
```python
# Text Content (transcription, notes)
- Unicode normalization (NFKC)
- Control character removal (preserves \n, \t, \r)
- Script injection prevention
- Length limits with graceful truncation

# Confidence Scores
- Range validation (0.0-1.0)
- Precision rounding to 4 decimal places

# Language Codes
- ISO 639-1/639-3 format validation
- Case normalization and locale support

# Timestamps/Segments
- Temporal consistency validation
- Non-overlapping segment enforcement
- Numeric range validation

# Metadata Objects
- Recursive key sanitization
- Reserved key blocking
- JSON serializability testing
- Size limit enforcement (10KB per object)
```

#### **JSONB Safety Guarantees**
- **Corruption Prevention**: All data validated before PostgreSQL storage
- **Query Safety**: Sanitized keys prevent injection attacks via JSONB queries
- **UTF-8 Compliance**: Unicode normalization ensures valid encoding
- **Version Consistency**: Validation applied at every version update
- **Rollback Safety**: Previous versions remain valid after sanitization updates

### Integration with Existing Version System

**No new tables are created.** The implementation leverages the existing comprehensive versioning infrastructure:

- `RecordHistory` - Tracks all changes with full snapshots and field-level diffs
- `RecordVersion` - Maintains version counters and change statistics
- `RecordFieldHistory` - Granular field-level change tracking
- `RecordSnapshot` - Periodic full record snapshots
- `RecordRestore` - Rollback capabilities

## Data Flow

```
1. System Processing (First version is AI extracted)
   ┌─────────────────┐
   │ OCR/ASR/Caption │
   │   Processing    │
   └─────────┬───────┘
             │ Extracts text
             ▼
   ┌─────────────────┐
   │ extracted_text  │ ← First version is AI extracted (change_source='ai_processing')
   │ Field Version 1 │   Immutable AI baseline for this field
   └─────────────────┘

2. User Corrections (Field Version 2+)
   ┌─────────────────┐
   │     Users       │
   │   View & Edit   │
   └─────────┬───────┘
             │ Makes corrections
             ▼
   ┌─────────────────┐      ┌──────────────────┐
   │ extracted_text  │ ────→│ RecordHistory    │
   │ Field Version 2+│      │ (existing audit  │
   │(change_source=  │      │ trail system)    │
   │ 'user_edit')    │      └──────────────────┘
   └─────────────────┘               │
                            ┌──────────────────┐
                            │ RecordVersion    │
                            │ (version counter)│
                            └──────────────────┘
```

## API Endpoints (Updated)

### 1. Save AI Extracted Text
**POST** `/api/v1/records/{record_id}/extracted_text`

**Description:** Save AI-generated extracted text as first AI version (system/admin only). Checks field-specific history to allow AI text on records with existing edit history.

**Access:** Admin, System roles only

**Request Body:**
```json
{
  "transcription": "यह एक टेस्ट रिकॉर्डिंग है।",
  "confidence": 0.95,
  "language": "hindi",
  "extraction_type": "asr",
  "segments": [
    {"start": 0.0, "end": 2.5, "text": "यह एक टेस्ट"},
    {"start": 2.5, "end": 5.0, "text": "रिकॉर्डिंग है।"}
  ]
}
```

**Response:**
```json
{
  "message": "AI extracted text saved successfully",
  "record_id": "uuid",
  "version": 1
}
```

### 2. Get Record Text
**GET** `/api/v1/records/{record_id}/text?version={version}`

**Description:** Retrieve current and AI baseline text with version access

**Access:** Any authenticated user

**Query Parameters:**
- `version` (optional) - Get specific version (default: latest)

**Response:**
```json
{
  "record_id": "uuid",
  "extracted_text": {
    "transcription": "यह एक परीक्षण रिकॉर्डिंग है।",
    "extraction_type": "manual",
    "corrections_made": ["टेस्ट -> परीक्षण"]
  },
  "version_info": {
    "current_version": 3,
    "total_changes": 5,
    "last_updated": "2025-09-25T18:00:00Z"
  },
  "last_updated": "2025-09-25T18:00:00Z"
}
```

### 3. Update Extracted Text (User Corrections)
**PATCH** `/api/v1/records/{record_id}/extracted_text?expected_version={version}`

**Description:** Update extracted text with user corrections (creates Version 2+)

**Access:** Any authenticated user

**Query Parameters:**
- `expected_version` (optional) - Expected version for optimistic locking

**Request Body:**
```json
{
  "transcription": "यह एक परीक्षण रिकॉर्डिंग है।",
  "extraction_type": "manual",
  "corrections_made": ["टेस्ट -> परीक्षण"],
  "corrected_by": "user_annotation"
}
```

**Response:**
```json
{
  "message": "Corrected text updated successfully",
  "record_id": "uuid",
  "new_version": 4,
  "history_entry_id": "uuid",
  "version_info": {
    "current_version": 4,
    "total_changes": 6,
    "last_updated": "2025-09-25T18:05:00Z"
  }
}
```

### 4. Get Text History (Uses Existing Endpoints)
**GET** `/api/v1/records/{record_id}/history?change_source=user_edit&skip={skip}&limit={limit}`

**Description:** Retrieve text extraction and correction history using existing RecordHistory endpoints

**Access:** Any authenticated user

**Query Parameters:**
- `change_source=ai_processing` - Filter for AI extraction (Version 1)
- `change_source=user_edit` - Filter for user corrections (Version 2+)
- `skip` (optional) - Number of entries to skip
- `limit` (optional) - Number of entries to return

**Alternative History Endpoints:**
- **GET** `/api/v1/records/{record_id}/field/extracted_text/history` - Field-specific history
- **GET** `/api/v1/records/{record_id}/version-summary` - Get version summary
- **GET** `/api/v1/records/{record_id}/diff?from_version={from}&to_version={to}` - Compare versions
- **GET** `/api/v1/records/{record_id}/version/{version}` - Get specific version

**Response:** (Uses existing RecordHistory response format)
```json
{
  "record_id": "uuid",
  "history": [
    {
      "id": "history_entry_uuid",
      "version_number": 3,
      "change_type": "updated",
      "change_source": "user_edit",
      "changed_by": "uuid",
      "change_reason": "Text correction via collaborative editing",
      "field_changes": {
        "users_corrected_text": {
          "old_value": "previous text content",
          "new_value": "corrected text content",
          "change_type": "updated"
        }
      },
      "created_at": "2025-09-25T18:00:00Z"
    }
  ],
  "pagination": {
    "skip": 0,
    "limit": 50,
    "total_count": 15,
    "has_more": false
  }
}
```

## Advantages of This Approach

### 1. **Architectural Simplicity**
- Single field eliminates data duplication and sync issues
- Natural progression from AI baseline → user corrections
- Version numbering across all text changes
- Clean data model with version-based access patterns

### 2. **Rich Audit Trail**
- Full field-level change tracking with change source distinction
- Complete version snapshots at each edit
- Structured diffs between any two versions
- Change source classification (ai_processing → user_edit progression)

### 3. **Advanced Features Available**
- **Version Access**: Get any version (AI baseline or specific correction)
- **Diff Comparison**: Compare AI baseline vs corrected versions
- **Restoration**: Roll back to any previous version
- **Approval Workflow**: Can add approval requirements for corrections

### 4. **Performance Optimized**
- Single field queries with indexed version access
- Efficient history retrieval through existing infrastructure
- Optimized diff calculations between versions

### 5. **Comprehensive Metrics**
- User edit statistics with AI baseline comparison
- Change pattern analysis across version progression
- Quality metrics comparing AI confidence vs user corrections

## Migration Commands

```bash
# Run the migration to add extracted text field
uv run alembic upgrade head
```

## JSONB Structure Examples by Extraction Type

### OCR (Optical Character Recognition)
```json
{
  "transcription": "లండన్‌లో నివసిస్తున్న విదేశీ పౌరుల సంఖ్య పెరిగింది",
  "confidence": 0.92,
  "language": "telugu",
  "extraction_type": "ocr",
  "model_name": "tesseract-5.3.0",
  "processing_date": "2025-09-26T10:30:00Z",
  "segments": [
    {
      "text": "లండన్‌లో",
      "confidence": 0.95,
      "bounding_box": {"x": 45, "y": 120, "width": 80, "height": 25},
      "page": 1
    },
    {
      "text": "నివసిస్తున్న విదేశీ పౌరుల",
      "confidence": 0.89,
      "bounding_box": {"x": 130, "y": 120, "width": 120, "height": 25},
      "page": 1
    }
  ],
  "metadata": {
    "document_type": "newspaper",
    "dpi": 300,
    "preprocessing": "deskew,denoise"
  }
}
```

### ASR (Automatic Speech Recognition)
```json
{
  "transcription": "ఇది తెలుగు భాషలో మాట్లాడిన పరీక్షా రికార్డింగ్",
  "confidence": 0.94,
  "language": "telugu",
  "extraction_type": "asr",
  "model_name": "whisper-large-v3",
  "processing_date": "2025-09-26T10:30:00Z",
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "ఇది ఒక పరీక్షా",
      "confidence": 0.96,
      "speaker": "speaker_1"
    },
    {
      "start": 2.5,
      "end": 5.8,
      "text": "రికార్డింగ్ తెలుగు భాషలో",
      "confidence": 0.92,
      "speaker": "speaker_1"
    },
    {
      "start": 5.8,
      "end": 7.2,
      "text": "మాట్లాడబడింది",
      "confidence": 0.95,
      "speaker": "speaker_1"
    }
  ],
  "metadata": {
    "audio_quality": "high",
    "sample_rate": 16000,
    "channels": 1,
    "background_noise_level": 0.12,
    "speaker_count": 1
  }
}
```

### Caption Generation
```json
{
  "transcription": "వ్యక్తి కంప్యూటర్‌పై పని చేస్తూ స్క్రీన్‌పై కోడ్ వ్రాస్తున్నాడు",
  "confidence": 0.88,
  "language": "telugu",
  "extraction_type": "caption",
  "model_name": "blip2-flan-t5-xl",
  "processing_date": "2025-09-26T10:30:00Z",
  "segments": [
    {
      "start": 0.0,
      "end": 3.0,
      "text": "వ్యక్తి కంప్యూటర్‌పై పని చేస్తున్నాడు",
      "confidence": 0.91,
      "region": {"x": 100, "y": 50, "width": 400, "height": 300}
    },
    {
      "start": 3.0,
      "end": 6.0,
      "text": "స్క్రీన్‌పై కోడ్ వ్రాస్తున్నాడు",
      "confidence": 0.85,
      "region": {"x": 200, "y": 100, "width": 500, "height": 200}
    }
  ],
  "metadata": {
    "video_resolution": "1920x1080",
    "frame_rate": 30,
    "total_frames": 180,
    "objects_detected": ["person", "computer", "keyboard", "monitor"]
  }
}
```

### Manual/User Corrections
```json
{
  "transcription": "లండన్‌లో నివసిస్తున్న విదేశీ పౌరుల సంఖ్య పెరిగింది",
  "extraction_type": "manual",
  "language": "telugu",
  "quality_score": 0.98,
  "corrections_made": [
    "లదన్ -> లండన్",
    "నవసిస్తున్న -> నివసిస్తున్న",
    "విదేసీ -> విదేశీ",
    "సంఖ్య -> సంఖ్య",
    "పెరిగిది -> పెరిగింది"
  ],
  "correction_type": "spelling_grammar",
  "corrected_by": "manual",
  "notes": "Fixed OCR errors in Telugu text",
  "metadata": {
    "validation_timestamp": "2025-09-26T11:15:00Z",
    "correction_count": 5,
    "has_quality_score": true,
    "is_user_correction": true,
    "original_extraction_type": "ocr",
    "improvement_metrics": {
      "confidence_improvement": 0.06,
      "accuracy_score": 0.98
    }
  }
}
```

## Example Usage Scenarios

### Version Access and History
```json
// Get current version with AI baseline comparison
GET /api/v1/records/{id}/text

// Get specific version
GET /api/v1/records/{id}/text?version=1

// Get AI extraction history
GET /api/v1/records/{id}/history?change_source=ai_processing

// Get user correction history
GET /api/v1/records/{id}/history?change_source=user_edit

// Get field-specific history
GET /api/v1/records/{id}/field/extracted_text/history

// Compare versions
GET /api/v1/records/{id}/diff?from_version=1&to_version=3

// Restore to previous version
POST /api/v1/records/{id}/restore
{
  "target_version": 2,
  "fields_to_restore": ["extracted_text"],
  "restore_reason": "Reverted incorrect changes"
}
```

## Testing

Updated test suite covers:
- ✅ ExtractedText schema with version-based access
- ✅ AI text extraction with change_source='ai_processing'
- ✅ User corrections with change_source='user_edit'
- ✅ Version-based optimistic locking (optional)
- ✅ Field-level change tracking through existing system
- ✅ Text history via existing RecordHistory endpoints
- ✅ Access control and comprehensive error handling

## Benefits of This Approach

1. **Code Reuse**: Leverages existing, battle-tested versioning infrastructure
2. **Consistency**: Same patterns and APIs for all record changes
3. **Advanced Features**: Version comparison, restoration, and approval workflows
4. **Performance**: Optimized queries with existing snapshot strategies
5. **Maintainability**: Simple data model using existing versioning system
6. **Future-Proof**: Easy to extend with approval workflows, quality metrics, or AI comparison features

This approach provides all the original requirements while integrating seamlessly with the existing versioning infrastructure.

## JSONB Query Performance and Examples

### PostgreSQL JSONB Indexing Strategy

```sql
-- GIN index for full-text search within transcriptions
CREATE INDEX idx_records_extracted_text_transcription
ON records USING GIN ((extracted_text->>'transcription') gin_trgm_ops);

-- GIN index for metadata searches
CREATE INDEX idx_records_extracted_text_metadata
ON records USING GIN (extracted_text);

-- Specific indexes for common query patterns
CREATE INDEX idx_records_extraction_type
ON records USING BTREE ((extracted_text->>'extraction_type'));

CREATE INDEX idx_records_confidence_score
ON records USING BTREE (((extracted_text->>'confidence')::numeric));

CREATE INDEX idx_records_language
ON records USING BTREE ((extracted_text->>'language'));
```

### Common Query Patterns

#### **1. Find Records by Confidence Range**
```sql
-- Find all records with ASR confidence above 0.9
SELECT id, extracted_text->>'transcription', extracted_text->>'confidence'
FROM records
WHERE extracted_text->>'extraction_type' = 'asr'
  AND (extracted_text->>'confidence')::numeric > 0.9;
```

#### **2. Search Within Segments by Time Range**
```sql
-- Find segments in ASR recordings between 10-30 seconds
SELECT id,
       jsonb_path_query_array(extracted_text, '$.segments[*] ? (@.start >= 10 && @.end <= 30)')
FROM records
WHERE extracted_text->>'extraction_type' = 'asr'
  AND extracted_text ? 'segments';
```

#### **3. Find Records with User Corrections**
```sql
-- Get all manually corrected texts with correction count
SELECT id,
       extracted_text->>'transcription',
       jsonb_array_length(extracted_text->'corrections_made') as correction_count,
       extracted_text->'metadata'->>'correction_count'
FROM records
WHERE extracted_text ? 'corrections_made'
  AND jsonb_array_length(extracted_text->'corrections_made') > 0;
```

#### **4. OCR Bounding Box Queries**
```sql
-- Find OCR text segments in specific page regions
SELECT id,
       jsonb_path_query_array(
         extracted_text,
         '$.segments[*] ? (@.bounding_box.x >= 100 && @.bounding_box.x <= 500)'
       ) as matching_segments
FROM records
WHERE extracted_text->>'extraction_type' = 'ocr'
  AND extracted_text ? 'segments';
```

#### **5. Full-Text Search Across Transcriptions**
```sql
-- Search for Telugu words in transcriptions
SELECT id,
       extracted_text->>'transcription',
       extracted_text->>'language',
       ts_rank(to_tsvector('simple', extracted_text->>'transcription'),
               plainto_tsquery('simple', 'తెలుగు భాష')) as relevance
FROM records
WHERE extracted_text->>'transcription' @@ plainto_tsquery('simple', 'తెలుగు భాష')
ORDER BY relevance DESC;
```

#### **6. Aggregation Queries**
```sql
-- Get confidence statistics by extraction type
SELECT extracted_text->>'extraction_type' as method,
       COUNT(*) as total_records,
       AVG((extracted_text->>'confidence')::numeric) as avg_confidence,
       MIN((extracted_text->>'confidence')::numeric) as min_confidence,
       MAX((extracted_text->>'confidence')::numeric) as max_confidence
FROM records
WHERE extracted_text ? 'confidence'
GROUP BY extracted_text->>'extraction_type';

-- Count corrections by language
SELECT extracted_text->>'language' as language,
       AVG(jsonb_array_length(extracted_text->'corrections_made')) as avg_corrections,
       COUNT(*) as records_with_corrections
FROM records
WHERE extracted_text ? 'corrections_made'
GROUP BY extracted_text->>'language';
```

### Performance Optimization Tips

#### **1. Query Optimization**
- Use specific JSONB operators (`->>`, `->`, `?`) instead of casting
- Leverage GIN indexes for containment queries (`@>`, `?`)
- Use path queries (`jsonb_path_query`) for complex nested searches

#### **2. Index Selection Strategy**
```sql
-- For exact matches on extraction type
WHERE extracted_text->>'extraction_type' = 'asr'

-- For range queries on confidence
WHERE (extracted_text->>'confidence')::numeric BETWEEN 0.8 AND 1.0

-- For array containment checks
WHERE extracted_text->'metadata' @> '{"is_user_correction": true}'

-- For text search within transcriptions
WHERE extracted_text->>'transcription' ILIKE '%తెలుగు%'
```

#### **3. Query Planning Examples**
```sql
-- Efficient: Uses GIN index
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM records
WHERE extracted_text ? 'corrections_made';

-- Efficient: Uses BTREE index
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM records
WHERE extracted_text->>'language' = 'telugu';

-- Less efficient: Requires sequential scan
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM records
WHERE jsonb_array_length(extracted_text->'segments') > 10;
```

### Real-World Usage Patterns

#### **Analytics Dashboard Queries**
```sql
-- Weekly correction activity
SELECT DATE_TRUNC('week', updated_at) as week,
       COUNT(*) FILTER (WHERE extracted_text ? 'corrections_made') as corrected_records,
       AVG(jsonb_array_length(extracted_text->'corrections_made')) as avg_corrections_per_record
FROM records
WHERE updated_at >= NOW() - INTERVAL '30 days'
GROUP BY week
ORDER BY week;

-- Language-specific accuracy trends
SELECT extracted_text->>'language' as language,
       AVG((extracted_text->>'confidence')::numeric) as avg_confidence,
       AVG((extracted_text->'metadata'->>'accuracy_score')::numeric) as avg_accuracy
FROM records
WHERE extracted_text ? 'confidence'
GROUP BY extracted_text->>'language'
HAVING COUNT(*) > 10;
```
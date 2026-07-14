# Record History System - Detailed Data Flow

## Overview
The record history system provides comprehensive audit trails for all record modifications. Here's how data flows between the history tables when a record is changed.

## Data Flow Sequence

### 1. Record Creation Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    API Request  │    │     RECORD      │    │ RECORD_VERSION  │
│   (POST /record)│    │                 │    │                 │
│                 │───►│ uid: new-uuid   │───►│ record_id: FK   │
│ title: "..."    │    │ title: "..."    │    │ current_ver: 1  │
│ description: ...│    │ description: ...│    │ total_changes: 0│
│ user_id: user-1 │    │ user_id: user-1 │    │ last_changed_by │
│                 │    │ created_at: now │    │ created_at: now │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ RECORD_HISTORY  │
                       │                 │
                       │ record_id: FK   │
                       │ version_num: 1  │
                       │ change_type:    │
                       │   "created"     │
                       │ change_source:  │
                       │   "user_edit"   │
                       │ changed_by: FK  │
                       │ record_snapshot:│
                       │   {full_record} │
                       │ field_changes:  │
                       │   {}            │
                       └─────────────────┘
```

### 2. Record Update Flow (PATCH)
```
                    ┌─────────────────────────────────────────────────────┐
                    │              UPDATE PROCESS                         │
                    └─────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Request   │    │ Change Detection│    │    RECORD       │    │ RECORD_VERSION  │
│ (PATCH /record) │    │                 │    │                 │    │                 │
│                 │───►│ Compare:        │───►│ title: "new"    │───►│ current_ver: 2  │
│ title: "new"    │    │ old: "old"      │    │ description:... │    │ total_changes:1 │
│ description:... │    │ new: "new"      │    │ updated_at: now │    │ last_changed_by │
│                 │    │                 │    │                 │    │ last_updated:now│
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                                              │
                                │         ┌─────────────────┐                  │
                                │         │ RECORD_HISTORY  │                  │
                                │         │                 │                  │
                                └────────►│ record_id: FK   │◄─────────────────┘
                                          │ version_num: 2  │
                                          │ change_type:    │
                                          │   "updated"     │
                                          │ change_source:  │
                                          │   "user_edit"   │
                                          │ changed_by: FK  │
                                          │ record_snapshot:│
                                          │   {full_record} │
                                          │ field_changes:  │
                                          │   {"title": {   │
                                          │     "old": "old"│
                                          │     "new": "new"│
                                          │   }}            │
                                          └─────────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │RECORD_FIELD_HIST│
                                          │                 │
                                          │ record_hist_id  │
                                          │ record_id: FK   │
                                          │ field_name:     │
                                          │   "title"       │
                                          │ old_value: "old"│
                                          │ new_value: "new"│
                                          │ change_reason:  │
                                          │   "User edit"   │
                                          │ confidence: 1.0 │
                                          └─────────────────┘
```

### 3. Snapshot Creation Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Trigger       │    │ RECORD_SNAPSHOT │    │    RECORD       │
│ - Major version │    │                 │    │                 │
│ - Daily backup  │───►│ record_id: FK   │◄───│ Current state   │
│ - Pre-review    │    │ snapshot_ver: 5 │    │ All fields      │
│ - Manual        │    │ full_record_data│    │                 │
│                 │    │   {complete}    │    │                 │
│                 │    │ snapshot_type:  │    │                 │
│                 │    │   "major_ver"   │    │                 │
│                 │    │ created_by: FK  │    │                 │
│                 │    │ created_at: now │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 4. Restore Operation Flow
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Restore Request │    │ RECORD_RESTORE  │    │ RECORD_HISTORY  │
│                 │    │                 │    │                 │
│ restore_to: v3  │───►│ record_id: FK   │───►│ Query version 3 │
│ reason: "error" │    │ restored_from: 5│    │ Get snapshot    │
│ fields: ["title"]│    │ restored_to: 3  │    │ Get field data  │
│                 │    │ restored_by: FK │    │                 │
│                 │    │ restore_reason  │    │                 │
│                 │    │ restored_fields │    │                 │
│                 │    │ partial: true   │    │                 │
│                 │    │ requires_appr.  │    │                 │
│                 │    │ approval_status │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │     RECORD      │    │ New RECORD_HIST │
                       │                 │    │                 │
                       │ title: restored │    │ version_num: 6  │
                       │ other fields:   │    │ change_type:    │
                       │   unchanged     │    │  "admin_override│
                       │ updated_at: now │    │ change_source:  │
                       │                 │    │  "admin_action" │
                       │                 │    │ field_changes:  │
                       │                 │    │  restoration    │
                       └─────────────────┘    └─────────────────┘
```

## Detailed Table Interactions

### Primary Data Relationships

#### 1. Record → Record_History (1:Many)
```
RECORD.uid ────────► RECORD_HISTORY.record_id
```
**Purpose**: Every record change creates a new history entry
**Cascade**: When record deleted, all history preserved for audit

#### 2. Record_History → Record_Field_History (1:Many)
```
RECORD_HISTORY.uid ────────► RECORD_FIELD_HISTORY.record_history_id
```
**Purpose**: Each history entry can have multiple field-level changes
**Data Flow**:
- History entry created first
- Then individual field changes are recorded
- Links granular changes to specific version

#### 3. Record → Record_Version (1:1)
```
RECORD.uid ────────► RECORD_VERSION.record_id (UNIQUE)
```
**Purpose**: Quick access to current version info without scanning history
**Update Pattern**: Updated on every record change

#### 4. Record → Record_Snapshot (1:Many)
```
RECORD.uid ────────► RECORD_SNAPSHOT.record_id
```
**Purpose**: Periodic full-state captures for efficient diff operations
**Trigger Conditions**:
- Every 10th version (major_version)
- Daily automated backup
- Before review process
- Manual admin request

#### 5. User Relationships
```
USER.id ────────► RECORD_HISTORY.changed_by
USER.id ────────► RECORD_VERSION.last_changed_by
USER.id ────────► RECORD_SNAPSHOT.created_by
USER.id ────────► RECORD_RESTORE.restored_by
USER.id ────────► RECORD_RESTORE.approved_by
```

## Change Detection Algorithm

### Field-by-Field Comparison
```
┌─────────────────────────────────────────────────┐
│              CHANGE DETECTION                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. Get current record state                    │
│     current_record = get_record(id)             │
│                                                 │
│  2. Apply incoming changes                      │
│     new_data = merge(current_record, patch)     │
│                                                 │
│  3. Compare field-by-field                     │
│     for field in record_fields:                 │
│       if current[field] != new_data[field]:     │
│         changes[field] = {                      │
│           "old": current[field],                │
│           "new": new_data[field],               │
│           "type": detect_change_type(field)     │
│         }                                       │
│                                                 │
│  4. Only proceed if changes detected            │
│     if changes:                                 │
│       create_history_entry()                   │
│       create_field_history_entries()           │
│       update_version_info()                    │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Version Management

### Version Number Sequence
```
Record Created ────► Version 1 (RECORD_HISTORY.version_number = 1)
      │
      ▼
First Edit ────────► Version 2 (RECORD_HISTORY.version_number = 2)
      │
      ▼
Second Edit ───────► Version 3 (RECORD_HISTORY.version_number = 3)
      │
      ▼
Admin Override ────► Version 4 (RECORD_HISTORY.version_number = 4)
      │
      ▼
System Update ─────► Version 5 (RECORD_HISTORY.version_number = 5)
```

### Version Info Updates
```
RECORD_VERSION table maintains:
├── current_version: Always = MAX(RECORD_HISTORY.version_number)
├── total_changes: COUNT(*) from RECORD_HISTORY
├── user_edit_changes: COUNT(*) WHERE change_source = 'user_edit'
├── admin_changes: COUNT(*) WHERE change_source = 'admin_action'
└── system_changes: COUNT(*) WHERE change_source = 'system_process'
```

## Query Patterns

### Common History Queries

#### 1. Get Record History Timeline
```sql
SELECT
  rh.version_number,
  rh.change_type,
  rh.change_source,
  u.name as changed_by_name,
  rh.created_at,
  rh.change_reason
FROM record_history rh
JOIN user u ON rh.changed_by = u.id
WHERE rh.record_id = 'record-uuid'
ORDER BY rh.version_number DESC;
```

#### 2. Get Field Change History
```sql
SELECT
  rfh.field_name,
  rfh.old_value,
  rfh.new_value,
  rfh.change_reason,
  rh.version_number,
  rh.created_at
FROM record_field_history rfh
JOIN record_history rh ON rfh.record_history_id = rh.uid
WHERE rfh.record_id = 'record-uuid'
  AND rfh.field_name = 'title'
ORDER BY rh.version_number DESC;
```

#### 3. Version Comparison
```sql
-- Get state at version 3
SELECT record_snapshot
FROM record_history
WHERE record_id = 'record-uuid'
  AND version_number = 3;

-- Get state at version 5
SELECT record_snapshot
FROM record_history
WHERE record_id = 'record-uuid'
  AND version_number = 5;
```

## Performance Optimizations

### Indexing Strategy
```
PRIMARY INDEXES:
├── record_history(record_id, version_number) [UNIQUE]
├── record_field_history(record_id, field_name, created_at)
├── record_version(record_id) [UNIQUE]
└── record_snapshot(record_id, snapshot_version)

QUERY OPTIMIZATION:
├── Composite indexes for common query patterns
├── JSONB indexes on record_snapshot for field access
└── Partial indexes on approval_status for pending restores
```

### Data Archival
```
SNAPSHOT STRATEGY:
├── Keep detailed history for last 100 versions
├── Create snapshots every 10 versions
├── Archive old field_history after 1 year
└── Maintain version table permanently for quick lookups
```

This data flow ensures complete auditability while maintaining query performance through strategic indexing and snapshot management.
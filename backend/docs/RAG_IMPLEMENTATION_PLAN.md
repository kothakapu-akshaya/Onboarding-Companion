# RAG Implementation Plan: NotebookLM-Style Retrieval for Corpus App

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Why Not Traditional RAG?](#why-not-traditional-rag)
3. [Chosen Architecture](#chosen-architecture)
4. [System Design](#system-design)
5. [User Flow](#user-flow)
6. [API Design](#api-design)
7. [Data Models](#data-models)
8. [Implementation Phases](#implementation-phases)
9. [Cost Analysis](#cost-analysis)
10. [Future Enhancements](#future-enhancements)

---

## Executive Summary

This document outlines the implementation plan for adding **Retrieval-Augmented Generation (RAG)** capabilities to the Corpus Server App — an Indic Languages platform supporting 22+ Indian languages with text, audio, video, image, and document records.

### Core Philosophy

Build a **NotebookLM-style RAG system** where:
- Users select records they want to query
- The system prepares those records (extracts text if needed, generates a metadata index)
- Users ask questions and get AI-generated answers with citations
- **Users bring their own API keys** for LLM generation
- **Zero continuous embedding costs** — no pre-computed vectors for the entire corpus

### Key Metrics

| Metric | Value |
|--------|-------|
| API calls per record | 2 (one-time index + per-query generation) |
| Cost per record index | ~₹0.50 (one-time) |
| Cost per query | ~₹1-2 (user pays via their API key) |
| Implementation time | 5-7 days |
| New code estimate | ~1,200 lines |

---

## Why Not Traditional RAG?

### Traditional RAG Approach

The standard RAG pipeline follows this flow:

```
User Query → Embed Query → Vector Search → Retrieve Chunks → LLM Generate → Response
```

This requires:
1. **Pre-computing embeddings** for every record in the corpus
2. **Storing vectors** in a vector database (pgvector, Pinecone, Milvus)
3. **Continuous compute** to keep embeddings updated as new records are added
4. **Ongoing costs** regardless of whether records are ever queried

### Why It Doesn't Fit Our Use Case

| Concern | Traditional RAG | Our Context |
|---------|----------------|-------------|
| **Cost Model** | Embed ALL records upfront | Only 20-30% of records get queried — 70-80% embedding cost is wasted |
| **User API Keys** | System manages embeddings; user only generates | Users want to control their own LLM usage and costs |
| **Content Type** | Works best on clean, structured text | Corpus has ASR transcriptions, OCR text, multilingual content with variable quality |
| **Scale** | 10,000+ records × $0.02/1K tokens = ~$200+ just for embeddings | Metadata index = ~₹0.50/record (200 tokens vs 1,000+ for embeddings) |
| **Maintenance** | Re-embed on every record update | Metadata index regenerates on-demand, only when needed |
| **Flexibility** | Fixed embedding model; hard to switch | User chooses their own LLM (Qwen, GPT-4, Gemini, etc.) |

### Alternatives We Evaluated

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Full-Text Search (BM25/pg_trgm)** | Zero cost, fast, simple | Loses semantic understanding, keyword-only matching | Too basic for NotebookLM experience |
| **PageIndex (VectifyAI)** | Reasoning-based, no vectors, high quality | Designed for structured PDFs with headings; struggles with unstructured ASR/OCR text | Inspiration, not direct adoption |
| **GraphRAG** | Cross-document reasoning, knowledge graphs | High complexity (20-30 days), expensive graph construction, overkill for current needs | Future enhancement possibility |
| **Agentic RAG** | Multi-step reasoning, tool use | High latency, prone to loops, expensive sequential LLM calls | Future enhancement possibility |
| **Metadata + Reasoning (Chosen)** | Semantic quality, per-query cost, works with unstructured text, user-controlled | Requires one LLM call for indexing, slightly slower than vector search | **Best fit for our needs** |

### The Chosen Approach: Metadata-Guided Reasoning Retrieval

Instead of embedding everything upfront, we:

1. **Generate a lightweight metadata index** per record (summary, topics, entities, themes)
2. **Store it as JSONB** in PostgreSQL (~2KB per record)
3. **At query time**, the user's LLM reasons over metadata indices to find relevant records
4. **Retrieve full text** only for the selected records
5. **Generate the answer** with citations

This is inspired by PageIndex's reasoning-based retrieval but adapted for our corpus's unstructured content.

---

## Chosen Architecture

### High-Level Flow

```
┌──────────────────────────────────────────────────────────────┐
│  PREPARATION PHASE (First time a record is used for RAG)    │
│  API Call #1: Metadata Index Generation (One-time, cached)  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  User selects record → Check extracted_text                  │
│                                                              │
│  ├── Has extracted_text → Generate metadata index directly  │
│  │                                                           │
│  └── No extracted_text → Trigger OCR/ASR pipeline           │
│       ↓                                                      │
│       Wait for completion → Generate metadata index          │
│                                                              │
│  Metadata Index (stored in record.semantic_metadata):       │
│  {                                                           │
│    "summary": "2-3 sentence overview",                      │
│    "topics": ["harvest", "folk song", "festival"],          │
│    "entities": {                                             │
│      "people": [...], "places": [...], "events": [...]      │
│    },                                                        │
│    "key_concepts": [...],                                   │
│    "themes": [...],                                         │
│    "suggested_queries": [...]                               │
│  }                                                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  QUERY PHASE (Per query, uses user's API key)               │
│  API Call #2: Response Generation                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  User asks question → LLM reasons over metadata indices     │
│       ↓                                                      │
│  LLM identifies relevant records by ID                      │
│       ↓                                                      │
│  System fetches full extracted_text for relevant records    │
│       ↓                                                      │
│  LLM generates answer with citations from actual text       │
│       ↓                                                      │
│  Response: {answer, sources[], follow_up_suggestions[]}    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **On-Demand, Not Pre-Computed**
   - Metadata index is generated only when a user first uses a record for RAG
   - No wasted compute on records nobody queries

2. **User-Controlled Costs**
   - Users provide their own LLM API key
   - They choose which model to use (Qwen, GPT-4, Gemini, etc.)
   - System doesn't manage generation costs

3. **Works with Unstructured Content**
   - ASR transcriptions (no headings, conversational text)
   - OCR text (variable quality, mixed languages)
   - User-generated content (no fixed structure)

4. **Transparent and Auditable**
   - Metadata index is human-readable JSONB
   - Users can inspect what the system "knows" about a record
   - Suggested queries help users discover content

5. **Incremental and Scalable**
   - Start with text records only
   - Expand to audio/video as OCR/ASR pipeline is ready
   - Add hybrid vector search later if needed

---

## System Design

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                             │
│  /api/v1/rag/prepare-record                                │
│  /api/v1/rag/query                                          │
│  /api/v1/rag/knowledge-map/{record_id}                     │
│  /api/v1/rag/preparation-status/{record_id}                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │ MetadataIndexer      │  │ ReasoningRetrieval       │    │
│  │                      │  │                          │    │
│  │ - generate_metadata  │  │ - retrieve_by_reasoning  │    │
│  │ - extract_entities   │  │ - rerank_candidates      │    │
│  │ - classify_content   │  │ - extract_relevant_text  │    │
│  │ - suggest_queries    │  │ - generate_answer        │    │
│  └──────────────────────┘  └──────────────────────────┘    │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │ TextChunker          │  │ LLMService               │    │
│  │                      │  │                          │    │
│  │ - chunk_by_segments  │  │ - call_with_user_key     │    │
│  │ - chunk_by_tokens    │  │ - parse_structured_out   │    │
│  │ - merge_overlaps     │  │ - rate_limit             │    │
│  └──────────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer                                │
│                                                             │
│  Records Table (existing, augmented):                      │
│  - extracted_text (JSONB)                                   │
│  - semantic_metadata (JSONB) ← NEW                         │
│  - semantic_index_status ← NEW                              │
│                                                             │
│  TextChunks Table (NEW, optional optimization):            │
│  - record_id, chunk_index, text_content, metadata          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   Async Layer (Celery)                     │
│                                                             │
│  Tasks:                                                     │
│  - generate_record_metadata_index(record_id, api_key)      │
│  - chain_ocr_to_metadata_indexing(record_id, ocr_task_id)  │
│  - retry_failed_indexing(record_id)                        │
└─────────────────────────────────────────────────────────────┘
```

### Metadata Index Structure

The metadata index is the core data structure that enables reasoning-based retrieval. It captures the semantic essence of a record in ~200-500 tokens.

**Example for a Telugu folk song audio transcription:**

```json
{
  "record_id": "550e8400-e29b-41d4-a716-446655440000",
  "indexed_at": "2025-04-08T10:30:00Z",
  "index_version": 1,
  "metadata": {
    "summary": "A collection of 12 Telugu folk songs recorded during Sankranti festival celebrations in Krishna district. The songs describe paddy harvest rituals, cattle worship, community feasts, and intergenerational knowledge transfer. Primary singer is an elderly woman (age ~70) with group participation from village farmers.",
    
    "topics": [
      "harvest festival",
      "Sankranti",
      "folk songs",
      "paddy cultivation",
      "cattle worship",
      "community celebration",
      "agricultural cycle"
    ],
    
    "entities": {
      "people": ["farmers", "elders", "village priest", "women harvesters"],
      "places": ["Krishna district", "Godavari delta", "village temple"],
      "events": ["Sankranti", "Mattu Pongal", "Bhogi festival"],
      "cultural_elements": ["paddy harvest rituals", "cattle decoration", "community feast", "rangoli competition"],
      "natural_elements": ["paddy", "cattle", "sun", "monsoon", "soil"]
    },
    
    "key_concepts": [
      {
        "concept": "agricultural gratitude",
        "mentions": 8,
        "context": "Songs repeatedly thank nature, ancestors, and cattle for the harvest. Expresses worldview of human-nature interdependence.",
        "related_topics": ["cattle worship", "nature reverence", "ancestral respect"]
      },
      {
        "concept": "intergenerational transmission",
        "mentions": 5,
        "context": "Elders teaching harvest songs to children, describing farming practices through oral tradition.",
        "related_topics": ["oral tradition", "elder respect", "cultural preservation"]
      },
      {
        "concept": "community bonding",
        "mentions": 6,
        "context": "Harvest described as collective activity, emphasizing shared labor, shared celebration, and mutual support.",
        "related_topics": ["community feast", "shared labor", "village unity"]
      }
    ],
    
    "themes": [
      "gratitude to nature and ancestors",
      "community celebration over individual achievement",
      "cyclical time and agricultural rhythms",
      "oral tradition as knowledge preservation"
    ],
    
    "content_classification": {
      "content_type": "folk_literature",
      "sub_type": "harvest_songs",
      "language_register": "colloquial_telugu",
      "formality": "informal",
      "narrative_perspective": "first_person_plural",
      "emotional_tone": "celebratory_grateful"
    },
    
    "suggested_queries": [
      "What agricultural practices are described in these songs?",
      "How is cattle worship performed according to these recordings?",
      "What role do elders play in harvest traditions?",
      "What natural elements are personified in the songs?",
      "How do these songs describe community cooperation?",
      "What festivals are mentioned and how are they celebrated?"
    ],
    
    "language_distribution": {
      "primary": "telugu",
      "secondary": null,
      "dialect_notes": "Krishna district colloquial, some Sanskrit loanwords in ritual contexts"
    },
    
    "temporal_references": {
      "time_period_described": "contemporary (recorded 2024)",
      "seasonal_references": ["harvest season (January)", "monsoon preparation"],
      "historical_references": "mentions traditional practices 'since ancestors'"
    }
  }
}
```

**Why This Structure Works:**

- **Summary** gives the LLM a quick overview for relevance matching
- **Topics** enable keyword-style matching without full embeddings
- **Entities** allow specific entity-based queries ("What places are mentioned?")
- **Key Concepts** capture deeper semantic meaning with context
- **Themes** enable abstract/philosophical queries
- **Suggested Queries** guide users toward answerable questions
- **Classifications** enable filtering by content type, tone, register

### Text Chunking Strategy

When full text needs to be retrieved, we chunk it intelligently:

**Approach 1: Segment-Aware Chunking (Preferred)**

If `extracted_text` has segment structure (from ASR/OCR), use those boundaries:

```
extracted_text.segments = [
  {text: "...", start_time: 0, end_time: 15, page_index: 1},
  {text: "...", start_time: 15, end_time: 30, page_index: 1},
  ...
]

Chunking: Group 3-5 segments per chunk (respects natural boundaries)
Result: Chunk 1 = segments 1-5, Chunk 2 = segments 6-10, etc.
```

**Approach 2: Token-Based Chunking (Fallback)**

For plain text without segments:

```
Text: "Long transcription without clear boundaries..."

Chunking: Split every ~500 tokens with 50 token overlap
Result: Chunk 1 = tokens 1-500, Chunk 2 = tokens 450-950, etc.
```

---

## User Flow

### Scenario 1: Record with Existing Extracted Text

```
Step 1: User browses corpus, finds interesting record
        → "Sankranti Folk Songs Collection" (audio, has ASR transcription)

Step 2: User clicks "Use for RAG" / "Ask Questions About This"

Step 3: System checks → extracted_text exists
        → Immediately generates metadata index (API Call #1)
        → Returns: "Record ready for querying!"

Step 4: User asks: "What are the main harvest themes?"

Step 5: System:
        a. Sends metadata index + query to user's LLM (API Call #2)
        b. LLM reasons and identifies relevant sections
        c. Retrieves full text for those sections
        d. Generates answer with citations

Step 6: User gets:
        {
          "answer": "The main harvest themes include...",
          "sources": [
            {"excerpt": "...", "time_range": "2:30-3:15"},
            {"excerpt": "...", "time_range": "5:00-5:45"}
          ],
          "follow_up_suggestions": [
            "What instruments accompany these songs?",
            "How do these compare to harvest songs from other regions?"
          ]
        }

Step 7: User asks follow-up: "What instruments are mentioned?"
        → Reuses metadata index (no API Call #1)
        → Only API Call #2 for new answer
```

### Scenario 2: Record Without Extracted Text

```
Step 1: User finds a scanned document (image of a Telugu poem)
        → No extracted_text yet

Step 2: User clicks "Use for RAG"

Step 3: System checks → NO extracted_text
        → Triggers OCR pipeline (async, existing system)
        → Returns: "Processing document... Estimated 2-3 minutes"

Step 4: User can:
        a. Poll status: GET /rag/preparation-status/{record_id}
        b. Come back later and check

Step 5: OCR completes → System auto-generates metadata index
        → Notification: "Record is ready for RAG!"

Step 6: User queries (same as Scenario 1)
```

### Scenario 3: Multi-Record Querying

```
Step 1: User selects 3 related records:
        - Sankranti Folk Songs (audio)
        - Harvest Festival Documentary (video)
        - Farmer Interview (audio)

Step 2: System prepares all 3 (metadata indices generated/cached)

Step 3: User asks: "What are common themes across these recordings?"

Step 4: System:
        a. Sends ALL 3 metadata indices + query to LLM
        b. LLM identifies cross-record patterns
        c. Retrieves relevant text from all 3 records
        d. Generates synthesized answer

Step 5: User gets:
        {
          "answer": "Across all three recordings, common themes include...",
          "sources": [
            {"record_id": "uuid-1", "excerpt": "..."},
            {"record_id": "uuid-2", "excerpt": "..."},
            {"record_id": "uuid-3", "excerpt": "..."}
          ],
          "cross_record_insights": [
            "All three describe gratitude to nature",
            "Two of three mention cattle worship",
            "Only the interview discusses economic aspects"
          ]
        }
```

---

## API Design

### 1. Prepare Record for RAG

```
POST /api/v1/rag/prepare-record
Authorization: Bearer <jwt>

Request:
{
  "record_id": "550e8400-e29b-41d4-a716-446655440000",
  "api_key": "sk-user-provided-qwen-key"  // Optional. If omitted, user must provide key at query time.
}

Response (immediate, if extracted_text exists):
{
  "status": "ready",
  "record_id": "550e8400-e29b-41d4-a716-446655440000",
  "extracted_text_status": "completed",
  "metadata_index_status": "completed",
  "metadata_preview": {
    "summary": "A collection of 12 Telugu folk songs...",
    "topics_count": 7,
    "suggested_queries": ["What agricultural practices...", ...]
  }
}

Response (if OCR/ASR needed):
{
  "status": "processing",
  "record_id": "550e8400-e29b-41d4-a716-446655440000",
  "extracted_text_status": "processing",
  "metadata_index_status": "pending",
  "task_id": "celery-task-uuid",
  "estimated_completion": "2-3 minutes",
  "status_check_endpoint": "/api/v1/rag/preparation-status/550e8400-e29b-41d4-a716-446655440000"
}
```

### 2. Query Prepared Records

```
POST /api/v1/rag/query
Authorization: Bearer <jwt>

Request:
{
  "record_ids": [
    "550e8400-e29b-41d4-a716-446655440000"
  ],
  "query": "What are the main harvest themes described in these songs?",
  "api_key": "sk-user-provided-qwen-key",  // Required
  "model": "qwen-max",  // Optional, defaults to system-configured model
  "top_k": 5,  // Number of relevant chunks to retrieve
  "language": "telugu",  // Optional, influences response language
  "include_follow_ups": true  // Optional, generates follow-up suggestions
}

Response:
{
  "answer": "The main harvest themes described in these songs center around three key areas:\n\n1. **Paddy Cultivation Rituals**: The songs describe the complete agricultural cycle from ploughing to storage, with special rituals at each stage...\n\n2. **Cattle Worship**: Multiple songs express gratitude to cattle, describing their decoration with turmeric, garlands, and the Mattu Pongal celebration...\n\n3. **Community Cooperation**: Harvest is portrayed as collective labor, with entire villages participating in shared activities...",
  
  "sources": [
    {
      "record_id": "550e8400-e29b-41d4-a716-446655440000",
      "record_title": "Sankranti Folk Songs Collection",
      "excerpt": "Bring the paddy home, thank the earth that bore it, thank the cattle that pulled the plough...",
      "location": {
        "type": "time_range",
        "start": "2:30",
        "end": "3:15"
      },
      "relevance_score": 0.95
    },
    {
      "record_id": "550e8400-e29b-41d4-a716-446655440000",
      "record_title": "Sankranti Folk Songs Collection",
      "excerpt": "Elder explained: 'Without the bull, no harvest. We worship them because they are our partners...'",
      "location": {
        "type": "time_range",
        "start": "5:00",
        "end": "5:45"
      },
      "relevance_score": 0.89
    }
  ],
  
  "follow_up_suggestions": [
    "What specific rituals are performed during cattle worship?",
    "How do these songs describe the relationship between farmers and nature?",
    "What role do women play in the harvest celebrations described?",
    "Are there any songs that describe the economic aspects of harvest?"
  ],
  
  "metadata": {
    "records_queried": 1,
    "records_with_relevant_content": 1,
    "total_chunks_analyzed": 15,
    "relevant_chunks_retrieved": 5,
    "model_used": "qwen-max",
    "generation_time_ms": 3200
  }
}
```

### 3. Get Knowledge Map

```
GET /api/v1/rag/knowledge-map/{record_id}
Authorization: Bearer <jwt>

Response:
{
  "record_id": "550e8400-e29b-41d4-a716-446655440000",
  "record_title": "Sankranti Folk Songs Collection",
  "metadata_index": {
    "summary": "...",
    "topics": [...],
    "entities": {...},
    "key_concepts": [...],
    "themes": [...],
    "suggested_queries": [...]
  },
  "usage_stats": {
    "times_queried": 12,
    "popular_queries": [
      {"query": "What are the main harvest themes?", "count": 5},
      {"query": "How is cattle worship performed?", "count": 3}
    ]
  }
}
```

### 4. Check Preparation Status

```
GET /api/v1/rag/preparation-status/{record_id}
Authorization: Bearer <jwt>

Response (processing):
{
  "record_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "extracted_text": {
    "status": "processing",
    "progress": "65%",
    "task_type": "asr_transcription"
  },
  "metadata_index": {
    "status": "pending",
    "note": "Will begin after text extraction completes"
  },
  "estimated_completion": "1-2 minutes remaining"
}

Response (ready):
{
  "record_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready",
  "extracted_text": {
    "status": "completed",
    "completed_at": "2025-04-08T10:28:00Z"
  },
  "metadata_index": {
    "status": "completed",
    "completed_at": "2025-04-08T10:30:00Z",
    "summary_preview": "A collection of 12 Telugu folk songs..."
  }
}
```

---

## Data Models

### New Fields Added to Existing Record Model

```python
# app/models/record.py (additions)

class Record(SQLModel, table=True):
    # ... existing fields ...
    
    # NEW: RAG-specific fields
    semantic_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column("semantic_metadata", JSONB),
        description="Lightweight metadata index for reasoning-based retrieval"
    )
    
    semantic_index_status: str = Field(
        default="not_started",  # not_started | pending | indexing | indexed | failed
        sa_column=Column("semantic_index_status", String(20), default="not_started"),
        description="Status of metadata index generation"
    )
    
    semantic_index_attempts: int = Field(
        default=0,
        sa_column=Column("semantic_index_attempts", Integer, default=0),
        description="Number of indexing attempts (for retry logic)"
    )
    
    last_indexed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column("last_indexed_at", DateTime(timezone=True)),
        description="When metadata index was last successfully generated"
    )
    
    rag_query_count: int = Field(
        default=0,
        sa_column=Column("rag_query_count", Integer, default=0),
        description="Total times this record has been queried via RAG"
    )
```

### New TextChunk Model (Optional Optimization)

```python
# app/models/text_chunk.py

class TextChunk(SQLModel, table=True):
    """
    Pre-chunked text for faster retrieval.
    Optional: can also chunk on-the-fly during query.
    """
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    record_id: UUID = Field(foreign_key="record.id", index=True)
    chunk_index: int = Field(description="Order of chunk within record")
    
    text_content: str = Field(description="The actual text content for this chunk")
    
    chunk_metadata: dict = Field(
        default_factory=dict,
        sa_column=Column("chunk_metadata", JSONB),
        description={
            "page_index": 1,  # For OCR documents
            "start_time": "2:30",  # For ASR transcriptions
            "end_time": "3:15",
            "segment_indices": [5, 6, 7],  # Which segments this chunk contains
            "token_count": 480,
            "language": "telugu"
        }
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## Implementation Phases

### Phase 1: Database Migration & Models (Day 1)

**Objective**: Set up database schema for RAG functionality.

**Tasks**:
1. Create Alembic migration for new columns on `records` table:
   - `semantic_metadata` (JSONB)
   - `semantic_index_status` (VARCHAR)
   - `semantic_index_attempts` (INTEGER)
   - `last_indexed_at` (TIMESTAMP)
   - `rag_query_count` (INTEGER)

2. Create `text_chunks` table (optional, can be done later):
   - `id`, `record_id`, `chunk_index`, `text_content`, `chunk_metadata`, `created_at`

3. Add indexes:
   - GIN index on `semantic_metadata` for JSONB queries
   - B-Tree index on `semantic_index_status` for filtering

**Deliverables**:
- Migration file
- Updated SQLModel definitions

---

### Phase 2: Metadata Indexing Service (Days 2-3)

**Objective**: Build the service that generates metadata indices for records.

**Tasks**:
1. Create `MetadataIndexer` service:
   - Method to generate metadata from `extracted_text`
   - Prompt engineering for structured JSON output
   - Validation and error handling
   - Support for multiple LLM providers (Qwen, OpenAI, etc.)

2. Create Celery tasks:
   - `generate_record_metadata_index(record_id, api_key)`
   - `chain_ocr_to_metadata_indexing(record_id, ocr_task_id)`
   - `retry_failed_indexing(record_id)`

3. Integrate with existing OCR/ASR pipeline:
   - Add callback/chain to trigger metadata indexing after OCR/ASR completes
   - Handle failures gracefully (retry logic, status updates)

**Example Prompt for Metadata Generation**:

```
You are an expert analyst analyzing content from the Indian languages corpus.

Analyze the following text and return a structured understanding.

TEXT:
{extracted_text_first_2000_chars}

Return ONLY a valid JSON object with these exact keys:
{
  "summary": "A 2-3 sentence summary of what this text is about",
  "topics": ["List of 5-10 key topics as short phrases"],
  "entities": {
    "people": ["Types of people mentioned (e.g., farmers, elders, children)"],
    "places": ["Geographic locations, landmarks, regions mentioned"],
    "events": ["Events, festivals, occasions mentioned"],
    "cultural_elements": ["Cultural practices, traditions, rituals described"],
    "natural_elements": ["Animals, plants, natural features mentioned"]
  },
  "key_concepts": [
    {
      "concept": "Name of a key concept (2-3 words)",
      "mentions": approximate_count,
      "context": "Brief description of how this concept appears in the text",
      "related_topics": ["related topic 1", "related topic 2"]
    }
  ],
  "themes": ["List of 3-5 underlying themes or messages"],
  "content_classification": {
    "content_type": "One of: folk_literature, conversation, news, educational, story, song, interview, other",
    "language_register": "One of: formal, colloquial, literary, dialect",
    "emotional_tone": "One of: celebratory, informative, narrative, instructional, reflective"
  },
  "suggested_queries": [
    "6-8 specific questions that can be answered from this text",
    "Make them diverse: factual, analytical, and thematic"
  ]
}

Return ONLY the JSON. No explanation, no markdown, no additional text.
```

**Deliverables**:
- `app/services/metadata_indexer.py`
- `app/tasks/rag_tasks.py`
- Integration with OCR/ASR pipeline

---

### Phase 3: Reasoning Retrieval Service (Days 4-5)

**Objective**: Build the service that retrieves relevant content using LLM reasoning.

**Tasks**:
1. Create `ReasoningRetrievalService`:
   - Method to fetch metadata indices for candidate records
   - Method to construct reasoning prompt
   - Method to call user's LLM with their API key
   - Method to parse LLM's response (relevant record IDs)
   - Method to fetch and chunk full text for relevant records
   - Method to generate final answer with citations

2. Create `TextChunker` service:
   - Segment-aware chunking (uses existing `extracted_text.segments`)
   - Token-based fallback chunking
   - Overlap management for context continuity

3. Create `LLMService`:
   - Abstract interface for LLM calls
   - Support for user-provided API keys
   - Rate limiting and error handling
   - Structured output parsing

**Example Reasoning Prompt**:

```
You are an expert researcher analyzing content from an Indic languages corpus.

QUESTION: {user_query}

You have access to the following records from the corpus. Each record has a metadata summary and key concepts.

Identify which records are MOST relevant to the question, and which specific aspects of each record should be examined in detail.

RECORDS:
{
  "record_id_1": {
    "title": "...",
    "summary": "...",
    "topics": [...],
    "key_concepts": [...],
    "themes": [...]
  },
  "record_id_2": { ... },
  ...
}

Return ONLY a valid JSON object with these keys:
{
  "relevant_record_ids": ["list of record IDs that are relevant, ordered by relevance"],
  "reasoning": "Brief explanation of why these records are relevant",
  "specific_aspects_to_examine": {
    "record_id_1": ["Which concepts/topics from this record to look for"],
    "record_id_2": [...]
  },
  "answer_hints": ["Key points that should be addressed in the final answer"]
}

Return ONLY the JSON. No explanation, no markdown.
```

**Example Answer Generation Prompt**:

```
You are an expert researcher answering a question using content from an Indic languages corpus.

QUESTION: {user_query}

RELEVANT CONTEXT:
{
  "record_1": {
    "title": "...",
    "relevant_excerpts": [
      {"text": "...", "location": "page 3 / 2:30-3:15"},
      {"text": "...", "location": "page 5 / 5:00-5:45"}
    ]
  },
  "record_2": { ... }
}

Answer the question using ONLY the provided context. Follow these rules:
1. Be specific and cite exact quotes where possible.
2. Acknowledge if context is insufficient for any part of the answer.
3. If multiple records contribute, synthesize them (don't just list).
4. Include page/time references so the user can verify.
5. If the question is in an Indic language, answer in that language.

Answer:
```

**Deliverables**:
- `app/services/reasoning_retrieval.py`
- `app/services/text_chunker.py`
- `app/services/llm_service.py`

---

### Phase 4: API Endpoints (Day 6)

**Objective**: Expose RAG functionality through REST API.

**Tasks**:
1. Create `app/api/v1/endpoints/rag.py`:
   - `POST /prepare-record`
   - `POST /query`
   - `GET /knowledge-map/{record_id}`
   - `GET /preparation-status/{record_id}`

2. Add request/response validation schemas
3. Add authentication and rate limiting
4. Add error handling (record not prepared, invalid API key, LLM errors)

**Deliverables**:
- `app/api/v1/endpoints/rag.py`
- `app/schemas/rag.py`
- Router registration in `app/api/v1/router.py`

---

### Phase 5: Testing & Documentation (Day 7)

**Objective**: Ensure reliability and usability.

**Tasks**:
1. Unit tests:
   - Metadata generation (mock LLM calls)
   - Reasoning retrieval (mock LLM calls)
   - Text chunking
   - Error handling

2. Integration tests:
   - Full prepare → query flow
   - OCR/ASR → metadata indexing chain
   - Multi-record querying

3. Documentation:
   - API documentation (OpenAPI/Swagger)
   - User guide for frontend integration
   - Developer guide for extending RAG

**Deliverables**:
- Test files in `tests/test_rag/`
- Updated API documentation

---

## Cost Analysis

### Cost Per Record (One-Time)

| Operation | Tokens | Cost (Qwen) | Notes |
|-----------|--------|-------------|-------|
| Metadata index generation | 200-500 input + 300 output | ~₹0.50 | One-time, cached for reuse |

### Cost Per Query (User Pays)

| Operation | Tokens | Cost (Qwen max) | Notes |
|-----------|--------|-----------------|-------|
| Reasoning over metadata | 1,000-2,000 input + 200 output | ~₹1.00 | Per query |
| Answer generation | 2,000-4,000 input + 500 output | ~₹2.00 | Per query |
| **Total per query** | | **~₹3.00** | User's API key |

### Example Scenarios

**Scenario A: User queries 1 record, 10 times**
- Metadata index: ₹0.50 (one-time)
- 10 queries × ₹3.00 = ₹30.00
- **Total: ₹30.50**

**Scenario B: User queries 5 records, 20 times**
- 5 metadata indices: 5 × ₹0.50 = ₹2.50
- 20 queries × ₹3.00 = ₹60.00
- **Total: ₹62.50**

**Scenario C: Traditional RAG comparison (100 records, 10 queries)**
- Pre-compute embeddings: 100 × ₹2.00 = ₹200.00 (all records, whether queried or not)
- 10 queries: ₹3.00 each = ₹30.00
- **Total: ₹230.00** (vs ₹30.50 for our approach — **87% savings**)

### Cost Scaling

| Active Records | Our Approach | Traditional RAG | Savings |
|----------------|--------------|-----------------|---------|
| 100 | ₹50 | ₹200 | 75% |
| 1,000 | ₹500 | ₹2,000 | 75% |
| 10,000 | ₹5,000 | ₹20,000 | 75% |

*Assumes 20% of records are actually queried (typical for corpus apps)*

---

## Future Enhancements

### 1. Hybrid Semantic Search (Optional)

Add vector embeddings as an optional enhancement:

```
User opts-in → Generate embedding for metadata index → Store in pgvector
Query time → Combine reasoning + vector similarity → Better recall
```

This doesn't replace reasoning retrieval — it augments it for users who want maximum accuracy.

### 2. Conversation Memory

Maintain context across follow-up queries:

```
Query 1: "What are the harvest themes?"
Query 2: "What about in the second record specifically?"
  → System remembers context from Query 1
  → Applies filter to record 2 only
```

Implementation: Store conversation history in Redis, include in reasoning prompt.

### 3. Collection/Notebook Feature

Allow users to group records into "notebooks":

```
Notebook: "Telugu Harvest Traditions"
Records: [record_1, record_2, record_3, record_4]

User queries the notebook → LLM synthesizes across all records
```

Implementation: New `Notebook` model with many-to-many relationship to records.

### 4. Export & Citations

Let users export Q&A sessions with full citations:

```
Export Format:
- PDF with embedded citations
- Markdown with source links
- JSON for programmatic use
```

### 5. Analytics Dashboard

Track RAG usage patterns:

- Most queried records
- Popular query themes
- Answer quality metrics
- Cost tracking per user

### 6. Re-Ranking Service

Add a dedicated re-ranking step for better precision:

```
Step 1: Reasoning retrieval retrieves 10 candidates
Step 2: Re-ranker (cross-encoder model) re-ranks by relevance
Step 3: Top 5 passed to answer generation
```

### 7. Multi-Modal RAG

Extend beyond text to support:

- Image understanding (describe visual content)
- Audio analysis (tone, emotion, speaker identification)
- Video analysis (scene descriptions, visual + audio synthesis)

---

## Appendix: Technology Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| **LLM Provider** | Qwen (DashScope) / User's choice | Cost-effective, good Indic language support |
| **Database** | PostgreSQL 15 + JSONB | Existing infrastructure, efficient JSONB queries |
| **Task Queue** | Celery + Redis | Existing infrastructure, reliable async processing |
| **API Framework** | FastAPI + Pydantic | Existing stack, automatic validation |
| **Vector DB** | Not used (reasoning-based) | Eliminates need for pgvector/Pinecone |
| **Caching** | Redis (optional) | Cache metadata indices, conversation history |

---

## Appendix: Glossary

| Term | Definition |
|------|-----------|
| **Metadata Index** | Lightweight JSON summary of a record's content (topics, entities, themes) used for reasoning-based retrieval |
| **Reasoning Retrieval** | Using an LLM to reason over metadata indices and identify relevant records (instead of vector similarity) |
| **Prepare Record** | The process of generating metadata index for a record (one-time, cached) |
| **Knowledge Map** | The metadata index + suggested queries for a record |
| **NotebookLM-Style RAG** | RAG experience where users select sources first, then query them (like Google's NotebookLM) |
| **On-Demand Indexing** | Generating metadata only when a user first uses a record (not pre-computed for all records) |
| **Segment-Aware Chunking** | Splitting text using existing ASR/OCR segment boundaries (better than arbitrary chunking) |

---

*Document Version: 1.0*  
*Last Updated: April 8, 2025*  
*Author: Corpus Development Team*

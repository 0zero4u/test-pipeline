# Research RAG System — Architecture Document

> **Purpose**: Citation-grounded research assistance for humanities/literary analysis  
> **Design Philosophy**: Automatic where stable, inference where ambiguous  
> **Last Updated**: 2026-06-17
> **Status**: Phase 1 Complete (Foundation), Phase 2 Next (Ingestion)

---

## 1. Core Principles

### Primary Directive

```
Evidence first
Reasoning second
Ontology never unless proven necessary
```

### Optimization Targets

- Less code
- Minimal debugging
- Automatic pipelines
- Semantic retrieval
- Citation grounding
- Cross-paper synthesis
- Humanities reasoning

### Explicitly Avoided

- Graph databases
- MCP-first RAG
- Agent orchestration
- Complex ontologies
- Relationship engines
- Retrieval overengineering
- Multi-service infrastructure

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   PDF Files                                                  │
│       ↓                                                      │
│   pymupdf4llm (parse + structure)                                │
│       ↓                                                      │
│   Metadata Extraction (LLM-first, regex fallback)               │
│       ↓                                                      │
│   Section-Aware Chunking (500-900t, tiktoken token counting)     │
│       ↓                                                      │
│   Qwen3 8B via OpenRouter (entity extraction)                │
│       ↓                                                      │
│   Embedding (qwen3-embedding-8b, 4096-dim)                       │
│       ↓                                                      │
│   Chroma (vectors + metadata)                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    QUERY PIPELINE                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   User Query                                                 │
│       ↓                                                      │
│   Query Embedding (same API)                                 │
│       ↓                                                      │
│   Chroma Semantic Retrieval (top-k)                          │
│       ↓                                                      │
│   Evidence Chunks + Metadata                                 │
│       ↓                                                      │
│   deepseek-v4-flash via OpenRouter (synthesis)                   │
│       ↓                                                      │
│   Citation-Grounded Answer                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### Core Components

| Component | Technology | Purpose | Deployment |
|-----------|------------|---------|------------|
| PDF Parser | pymupdf4llm | Parse PDFs to structured markdown | Local (CPU) |
| Metadata Extraction | LLM-first + regex fallback | LLM extract with heuristic fallback on API error | API (OpenRouter) |
| Chunking | Custom section-aware | Split documents preserving context | Local (CPU) |
| Entity Extraction | Qwen3 8B via OpenRouter | Extract people, works, themes | API |
| Embeddings | qwen3-embedding-8b (4096-dim) via OpenRouter | Generate semantic vectors | API |
| Vector DB | Chroma | Store embeddings + metadata | Local (CPU) |
| Synthesis | deepseek-v4-flash via OpenRouter | Cross-paper reasoning | API |

### API Dependencies

| Service | Model | Use Case | Cost Model |
|---------|-------|----------|------------|
| OpenRouter | Qwen3 8B | Entity extraction | Per-token |
| OpenRouter | deepseek-v4-flash | Answer synthesis | Per-token |
| OpenRouter | qwen3-embedding-8b | Query/document vectors | Per-token |

### Local Infrastructure

| Component | Spec | Notes |
|-----------|------|-------|
| RAM | 8-16GB | Sufficient for pymupdf4llm (lighter than Docling) + Chroma |
| CPU | 4-8 cores | Handles overnight ingestion |
| Storage | 10-50GB | PDFs + Chroma database |
| GPU | None required | All heavy compute via API |

---

## 4. Data Schemas

### 4.1 Document Metadata

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Document Metadata",
  "type": "object",
  "properties": {
    "document_id": {
      "type": "string",
      "description": "Unique identifier (UUID or derived from filename)"
    },
    "title": {
      "type": "string",
      "description": "Document title extracted from first page"
    },
    "authors": {
      "type": "array",
      "items": {"type": "string"},
      "description": "List of author names"
    },
    "year": {
      "type": ["integer", "null"],
      "description": "Publication year"
    },
    "journal": {
      "type": "string",
      "description": "Journal or publication name"
    },
    "volume": {
      "type": "string",
      "description": "Volume number"
    },
    "issue": {
      "type": "string",
      "description": "Issue number"
    },
    "doi": {
      "type": ["string", "null"],
      "description": "Digital Object Identifier"
    },
    "source_file": {
      "type": "string",
      "description": "Original PDF filename"
    },
    "metadata_confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Confidence score for extracted metadata"
    },
    "ingestion_date": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of ingestion"
    }
  },
  "required": ["document_id", "title", "source_file", "metadata_confidence"]
}
```

### 4.2 Chunk

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Document Chunk",
  "type": "object",
  "properties": {
    "chunk_id": {
      "type": "string",
      "description": "Unique chunk identifier"
    },
    "document_id": {
      "type": "string",
      "description": "Parent document reference"
    },
    "section_title": {
      "type": "string",
      "description": "Section heading this chunk belongs to"
    },
    "page_start": {
      "type": "integer",
      "minimum": 1,
      "description": "Starting page number"
    },
    "page_end": {
      "type": "integer",
      "minimum": 1,
      "description": "Ending page number"
    },
    "text": {
      "type": "string",
      "description": "Cleaned chunk text content"
    },
    "token_count": {
      "type": "integer",
      "description": "Approximate token count"
    },
    "metadata": {
      "$ref": "#/definitions/DocumentMetadata"
    },
    "entities": {
      "$ref": "#/definitions/EntityExtraction"
    },
    "flags": {
      "type": "object",
      "properties": {
        "quoted_text": {
          "type": "boolean",
          "default": false,
          "description": "Whether chunk contains significant quoted material"
        },
        "has_citations": {
          "type": "boolean",
          "default": false,
          "description": "Whether chunk contains citation markers"
        }
      }
    }
  },
  "required": ["chunk_id", "document_id", "text", "page_start", "page_end"]
}
```

### 4.3 Entity Extraction

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Entity Extraction",
  "type": "object",
  "properties": {
    "people": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Scholars, authors, historical figures"
    },
    "works": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Novels, books, articles, creative works"
    },
    "themes": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Concepts, themes, theoretical frameworks"
    },
    "historical_events": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Major historical events mentioned"
    },
    "references": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "author": {"type": "string"},
          "year": {"type": ["integer", "null"]},
          "title": {"type": "string"},
          "journal": {"type": "string"}
        }
      },
      "description": "Bibliographic references found in chunk"
    }
  }
}
```

### 4.4 Query Response

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Query Response",
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Original user query"
    },
    "answer": {
      "type": "string",
      "description": "Synthesized answer with inline citations"
    },
    "citations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "chunk_id": {"type": "string"},
          "document_id": {"type": "string"},
          "title": {"type": "string"},
          "page": {"type": "integer"},
          "relevance_score": {"type": "number"}
        }
      },
      "description": "Source chunks used in synthesis"
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "Model confidence in answer"
    },
    "reasoning_trace": {
      "type": "string",
      "description": "Optional: how synthesis was performed"
    }
  },
  "required": ["query", "answer", "citations"]
}
```

---

## 5. Ingestion Pipeline

### 5.1 PDF Parsing (pymupdf4llm)

```
Input:  PDF file
Output: Structured markdown with sections, tables, page markers

Process:
1. Load PDF via pymupdf4llm
2. Extract text with layout preservation
3. Identify sections via heading detection
4. Preserve page boundaries
5. Output structured markdown
```

**Configuration:**
- Preserve layout: Yes
- Extract tables: Yes (as markdown)
- Page markers: Insert `<!-- Page N -->` markers
- Header/footer removal: Yes

### 5.2 Metadata Extraction

```
Input:  First page text from pymupdf4llm
Output: JSON metadata object

Extraction Strategy:
1. Primary: LLM call to deepseek-v4-flash via OpenRouter
   - Prompt includes document text, requests structured metadata
   - Returns title, authors, year, journal, volume, issue, DOI
2. Fallback: Regex heuristics applied only on API failure/error
3. Retry: tenacity exponential backoff + jitter (default 2 retries)
```

**Error Handling:**
- LLM API failure: fallback to regex heuristics
- Both fail: partial metadata with warning
- Retry: tenacity exponential backoff + jitter

### 5.3 Section-Aware Chunking

```
Input:  Structured markdown from pymupdf4llm
Output: Array of chunk objects

Algorithm:
1. Split on section headings (H1, H2, H3)
2. For each section:
   a. If section < 500 tokens → merge with next section
   b. If section 500-900 tokens → keep as single chunk
   c. If section > 900 tokens → split at paragraph boundaries
3. Apply 10-15% overlap at chunk boundaries
4. Preserve page markers within chunks
5. Assign chunk IDs (doc_id + sequence)
```

**Chunking Constraints:**
- Minimum: 500 tokens (merge smaller sections)
- Maximum: 900 tokens (split larger sections)
- Overlap: 10-15% for context continuity
- Boundary: Never split mid-sentence
- Preserve: Quoted text, citation markers
- Token counting: tiktoken (cl100k_base) for accuracy

### 5.4 Entity Extraction (Qwen3 8B)

```
Input:  Chunk text
Output: Entity JSON object

Prompt Template:
"You are extracting key entities from academic text.
Extract ONLY:
- People (scholars, authors, historical figures)
- Works (novels, books, articles)
- Themes (concepts, theoretical frameworks)
- Historical events (major occurrences)
- References (bibliographic entries)

Do NOT extract:
- Cities, publishers, addresses
- Minor places
- Every named entity

Return JSON only. No explanation."
```

### 5.5 Embedding Generation

```
Input:  Chunk text
Output: 4096-dimensional vector (qwen3-embedding-8b)

Process:
1. Clean chunk text (remove markdown artifacts)
2. Send to OpenRouter embedding API
3. Receive 4096-dim vector embedding
```

---

## 6. Query Pipeline

### 6.1 Query Processing

```
Input:  User natural language query
Output: Answer with citations

Steps:
1. Generate query embedding (same API as ingestion)
2. Query Chroma for top-k similar chunks (k=5-10)
3. Retrieve chunk text + metadata
4. Send to deepseek-v4-flash with synthesis prompt
5. Return answer with inline citations
```

### 6.2 Synthesis Prompt

```
System: You are a research assistant synthesizing academic evidence.
Only use the provided evidence chunks. Do not add unsupported claims.
Cite sources using [1], [2], etc. format.

User Query: {query}

Evidence:
[1] {chunk_1_text}
    Source: {title}, Page {page}
[2] {chunk_2_text}
    Source: {title}, Page {page}
...

Provide a comprehensive, citation-grounded answer.
```

### 6.3 Response Format

```json
{
  "query": "How does Khushwant Singh portray Partition violence?",
  "answer": "Khushwant Singh's Train to Pakistan portrays Partition violence through...",
  "citations": [
    {
      "chunk_id": "chunk_042",
      "document_id": "singh_train_1956",
      "title": "Train to Pakistan",
      "page": 45,
      "relevance_score": 0.89
    }
  ],
  "confidence": 0.85
}
```

---

## 7. Storage Architecture

### 7.1 Chroma Collections

**Collection: `research_chunks`**

```
{
  "name": "research_chunks",
  "metadata": {
    "hnsw:space": "cosine",
    "hnsw:M": 16,
    "hnsw:construction_ef": 100,
    "hnsw:search_ef": 50
  }
}
```

**Document Structure:**
```
{
  "id": "chunk_001",
  "document": "chunk text here...",
  "embedding": [0.1, 0.2, ...],
  "metadata": {
    "document_id": "singh_train_1956",
    "title": "Train to Pakistan",
    "authors": ["Khushwant Singh"],
    "year": 1956,
    "section_title": "Chapter 3: Violence",
    "page_start": 42,
    "page_end": 45,
    "people": ["Khushwant Singh", "Urvashi Butalia"],
    "works": ["Train to Pakistan"],
    "themes": ["Partition", "violence", "communal conflict"]
  }
}
```

### 7.2 Metadata Store

Local JSON files for document-level metadata:

```
data/
├── metadata/
│   ├── singh_train_1956.json
│   ├── butalia_other_side_2001.json
│   └── ...
├── chunks/
│   ├── singh_train_1956_chunks.json
│   └── ...
└── chroma/
    └── research_db/
```

---

## 8. Observability

### 8.1 Logging

Store only essential information:

```json
{
  "timestamp": "2026-05-29T10:30:00Z",
  "query": "women victimization during Partition",
  "retrieved_chunks": ["chunk_042", "chunk_108", "chunk_215"],
  "page_numbers": [45, 112, 220],
  "answer_length": 850,
  "confidence": 0.82,
  "latency_ms": 2340
}
```

### 8.2 Failure Tracking

```json
{
  "timestamp": "2026-05-29T10:31:00Z",
  "query": "semiotic analysis of Partition narratives",
  "error": "low_confidence",
  "confidence": 0.35,
  "retrieved_chunks": ["chunk_301"],
  "action": "fallback_to_keyword"
}
```

---

## 9. Future Extensions

### 9.1 Add Reranker (When Needed)

**Trigger**: Retrieval quality becomes weak  
**Solution**: BGE reranker via API  
**Integration**: Post-retrieval, pre-synthesis

### 9.2 Add Hybrid Retrieval (When Needed)

**Trigger**: Keyword misses become common  
**Solution**: SQLite FTS5  
**Integration**: Combine semantic + keyword results

### 9.3 Add GROBID (When Needed)

**Trigger**: Metadata/citation extraction quality painful  
**Solution**: pymupdf4llm + GROBID pipeline
**Integration**: Enhanced bibliographic parsing

### 9.4 Add Claim Extraction (When Needed)

**Trigger**: Cross-paper disagreement becomes central  
**Solution**: Qwen3 8B claim extraction  
**Integration**: On-demand comparison

---

## 10. Deployment

### 10.1 Local Development

```bash
# Install dependencies
pip install pymupdf4llm chromadb openai

# Set API keys
export OPENROUTER_API_KEY="..."

# Run ingestion
python ingest.py --input ./pdfs/ --output ./data/

# Start query interface
python query.py --db ./data/chroma/
```

### 10.2 Production (Optional)

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    volumes:
      - ./data:/app/data
      - ./pdfs:/app/pdfs
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
```

---

## Appendix A: Configuration

```yaml
# config.yaml
ingestion:
  parser: pymupdf4llm
  chunk_size_min: 500
  chunk_size_max: 900
  chunk_overlap: 0.12

extraction:
  entity_model: qwen3-8b
  embedding_model: qwen/qwen3-embedding-8b

retrieval:
  top_k: 5
  similarity_threshold: 0.7

synthesis:
  model: deepseek-v4-flash
  max_tokens: 2000
  temperature: 0.3

storage:
  chroma_path: ./data/chroma/
  metadata_path: ./data/metadata/
```

---

## Appendix B: API Cost Estimates

| Operation | Model | Tokens/Call | Cost/1000 Calls |
|-----------|-------|-------------|-----------------|
| Entity Extraction | Qwen3 8B | ~1000 | ~$0.50 |
| Query Synthesis | deepseek-v4-flash | ~3000 | ~$3.00 |
| Embedding | qwen3-embedding-8b | ~500 | ~$0.10 |

**Monthly estimate (100 queries/day):**
- Entity extraction: ~$15/month (during ingestion)
- Query synthesis: ~$90/month
- Embedding: ~$3/month
- **Total: ~$108/month**

---

*Architecture Document v1.0 — Research RAG System*

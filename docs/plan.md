# Research RAG System — Final Project Plan

> **Project**: Citation-grounded research assistance for humanities/literary analysis  
> **Version**: 1.0  
> **Date**: 2026-05-29  
> **Status**: Phase 1 Complete — Ready for Phase 2

---

## Executive Summary

Build a retrieval-augmented generation (RAG) system optimized for humanities research. The system ingests academic PDFs, extracts structured content, and provides citation-grounded answers to research queries.

**Key Differentiators:**
- Humanities-optimized chunking (preserves argumentative continuity)
- Dynamic relationship inference (no static knowledge graph)
- Minimal infrastructure (API-hosted LLMs, local vector DB)
- Citation-grounded answers with source attribution

**Architecture**: OpenRouter APIs + Chroma + Docling  
**GPU Required**: No  
**Monthly Cost**: ~$108 (100 queries/day)

---

## Project Objectives

### Primary Objectives

1. **Ingest 100-1000 academic PDFs** with automated metadata extraction
2. **Provide semantic retrieval** with >80% relevance on research queries
3. **Generate citation-grounded answers** with inline source attribution
4. **Maintain minimal infrastructure** — no GPU, no complex services

### Success Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Ingestion speed | 100 PDFs/hour | Batch processing test |
| Retrieval relevance | >80% | Manual evaluation on 50 queries |
| Answer quality | Citation-grounded | No unsupported claims |
| Query latency | <4 seconds | End-to-end measurement |
| System reliability | 99% uptime | Error rate tracking |

---

## Scope

### In Scope

- PDF parsing and structuring
- Metadata extraction (title, authors, year, journal)
- Section-aware chunking (500-900 tokens)
- Entity extraction (people, works, themes)
- Semantic vector storage (Chroma)
- Query processing and retrieval
- Citation-grounded synthesis (Qwen3 32B)
- Interactive CLI interface
- Basic observability (logging, metrics)

### Out of Scope (Phase 1)

- Graph database / knowledge graph
- Hybrid retrieval (semantic + keyword)
- Reranking pipeline
- GROBID integration
- Web interface
- Multi-user support
- Real-time collaboration
- OCR for scanned PDFs

### Future Extensions (If Needed)

| Extension | Trigger | Effort |
|-----------|---------|--------|
| Reranker | Retrieval quality degrades | 1 week |
| Hybrid retrieval | Keyword misses common | 1 week |
| GROBID | Metadata quality painful | 2 weeks |
| Claim extraction | Cross-paper comparison needed | 1 week |

---

## Technical Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   PDF Files                                                  │
│       ↓                                                      │
│   Docling (parse + structure)                                │
│       ↓                                                      │
│   Metadata Extraction (lightweight heuristics)               │
│       ↓                                                      │
│   Section-Aware Chunking (500-900 tokens)                    │
│       ↓                                                      │
│   Qwen3 8B via OpenRouter (entity extraction)                │
│       ↓                                                      │
│   Embedding API (BGE-base-en-v1.5)                           │
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
│   Qwen3 32B via OpenRouter (synthesis)                       │
│       ↓                                                      │
│   Citation-Grounded Answer                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose | Deployment |
|-----------|------------|---------|------------|
| PDF Parser | Docling | Parse PDFs to structured markdown | Local (CPU) |
| Metadata Extraction | Heuristic regex | Extract title, authors, year, journal | Local (CPU) |
| Chunking | Custom section-aware | Split documents preserving context | Local (CPU) |
| Entity Extraction | Qwen3 8B via OpenRouter | Extract people, works, themes | API |
| Embeddings | BGE-base-en-v1.5 via API | Generate semantic vectors | API |
| Vector DB | Chroma | Store embeddings + metadata | Local (CPU) |
| Synthesis | Qwen3 32B via OpenRouter | Cross-paper reasoning | API |

### Hardware Requirements

| Component | Spec | Notes |
|-----------|------|-------|
| RAM | 8-16GB | Sufficient for Docling + Chroma |
| CPU | 4-8 cores | Handles overnight ingestion |
| Storage | 10-50GB | PDFs + Chroma database |
| GPU | None required | All heavy compute via API |

---

## Implementation Plan

### Phase 1: Foundation (Weeks 1-2) ✓ COMPLETE

**Goal**: Project structure, dependencies, configuration  
**Deliverable**: Runnable skeleton with tests  
**Completed**: 2026-05-29

**Tasks:**
- [x] Initialize Python project (pyproject.toml, src layout)
- [x] Set up dependency management (pip + venv)
- [x] Create config system (YAML with env overrides)
- [x] Design data schemas (Pydantic models)
- [x] Set up logging (structured JSON + console)
- [x] Create test fixtures (13 tests)
- [x] Write README

**Exit Criteria:**
- [x] `pip install -e .` works
- [x] Config loads from YAML
- [x] Schemas validate sample data
- [x] Tests pass (13/13)

---

### Phase 2: Ingestion Pipeline (Weeks 3-4) ✓ COMPLETE

**Goal**: PDF → chunks with metadata  
**Deliverable**: Ingest 10 PDFs, verify chunk quality  
**Completed**: 2026-05-29

**Tasks:**
- [x] Integrate Docling (PDF parsing, section detection)
- [x] Implement metadata extraction (regex/heuristic parser)
- [x] Build section-aware chunker (500-900 tokens, overlap)
- [x] Add chunk validation (size, boundary checks)
- [x] Create ingestion CLI (`research-rag ingest ./pdfs/`)
- [x] Add progress tracking (tqdm)
- [ ] Test on 10 PDFs (manual quality check)

**Exit Criteria:**
- [x] Docling parses PDFs into structured markdown with page markers
- [x] Metadata extracted with heuristic confidence scoring
- [x] Chunks respect 500-900 token boundaries with overlap
- [x] No split mid-sentence (paragraph-aware splitting)
- [x] Page markers preserved in chunks

---

### Phase 3: Vector Storage & Retrieval (Weeks 5-6)

**Goal**: Embed chunks, store in Chroma, retrieve by query  
**Deliverable**: Query returns relevant chunks

**Tasks:**
- [ ] Integrate embedding API (BGE-base-en-v1.5)
- [ ] Set up Chroma collection (schema, indexing)
- [ ] Implement upsert logic (avoid duplicates)
- [ ] Build retrieval function (top-k semantic search)
- [ ] Add metadata filtering (author, year, etc.)
- [ ] Create query CLI (`query.py "search term"`)
- [ ] Test retrieval quality

**Exit Criteria:**
- [ ] All chunks embedded and stored
- [ ] Query returns top-5 relevant chunks
- [ ] Relevance is >80% on test queries
- [ ] Metadata filtering works

---

### Phase 4: Synthesis & Citation (Weeks 7-8)

**Goal**: Generate citation-grounded answers  
**Deliverable**: Query → answer with citations

**Tasks:**
- [ ] Integrate OpenRouter (Qwen3 32B client)
- [ ] Design synthesis prompt (citation format, constraints)
- [ ] Implement answer generation (evidence → answer pipeline)
- [ ] Add citation extraction (parse inline citations)
- [ ] Build response formatter (JSON response structure)
- [ ] Add confidence scoring
- [ ] Test on 20 queries

**Exit Criteria:**
- [ ] Answers are citation-grounded
- [ ] Inline citations match sources
- [ ] No unsupported claims
- [ ] Confidence scores are calibrated

---

### Phase 5: Polish & UX (Weeks 9-10)

**Goal**: Usable interface, error handling, documentation  
**Deliverable**: End-to-end workflow working smoothly

**Tasks:**
- [ ] Build interactive CLI (REPL-style query interface)
- [ ] Add error handling (graceful failures)
- [ ] Implement retry logic (API call retries)
- [ ] Add progress indicators
- [ ] Write user documentation
- [ ] Add example notebooks
- [ ] Performance optimization

**Exit Criteria:**
- [ ] Interactive CLI works end-to-end
- [ ] Errors handled gracefully
- [ ] Documentation complete
- [ ] Examples run without errors

---

### Phase 6: Scale & Optimize (Weeks 11-12)

**Goal**: Handle 100-1000 PDFs, optimize performance  
**Deliverable**: Production-ready system

**Tasks:**
- [ ] Batch ingestion (parallel processing)
- [ ] Chroma optimization (index tuning)
- [ ] Add caching layer (query result caching)
- [ ] Implement observability (logging, metrics)
- [ ] Add incremental updates
- [ ] Performance benchmarking
- [ ] Documentation

**Exit Criteria:**
- [ ] 100 PDFs ingested in <1 hour
- [ ] Query latency <4s
- [ ] Incremental updates work
- [ ] Observability in place

---

## Data Schemas

### Document Metadata

```json
{
  "document_id": "string (required)",
  "title": "string (required)",
  "authors": ["string"],
  "year": "integer | null",
  "journal": "string",
  "volume": "string",
  "issue": "string",
  "doi": "string | null",
  "source_file": "string (required)",
  "metadata_confidence": "number 0-1 (required)",
  "ingestion_date": "datetime"
}
```

### Chunk

```json
{
  "chunk_id": "string (required)",
  "document_id": "string (required)",
  "section_title": "string",
  "page_start": "integer (required)",
  "page_end": "integer (required)",
  "text": "string (required)",
  "token_count": "integer",
  "metadata": "DocumentMetadata",
  "entities": "EntityExtraction",
  "flags": {
    "quoted_text": "boolean",
    "has_citations": "boolean"
  }
}
```

### Entity Extraction

```json
{
  "people": ["string"],
  "works": ["string"],
  "themes": ["string"],
  "historical_events": ["string"],
  "references": [
    {
      "author": "string",
      "year": "integer | null",
      "title": "string",
      "journal": "string"
    }
  ]
}
```

### Query Response

```json
{
  "query": "string (required)",
  "answer": "string (required)",
  "citations": [
    {
      "chunk_id": "string",
      "document_id": "string",
      "title": "string",
      "page": "integer",
      "relevance_score": "number"
    }
  ],
  "confidence": "number 0-1",
  "reasoning_trace": "string"
}
```

---

## Cost Analysis

### API Costs (Monthly Estimate)

| Operation | Model | Tokens/Call | Calls/Day | Monthly Cost |
|-----------|-------|-------------|-----------|--------------|
| Entity Extraction | Qwen3 8B | ~1000 | 50 (ingestion) | $15 |
| Query Synthesis | Qwen3 32B | ~3000 | 100 | $90 |
| Embedding | BGE | ~500 | 150 | $3 |
| **Total** | | | | **$108** |

### Infrastructure Costs

| Item | Cost | Notes |
|------|------|-------|
| Local machine | $0 | Existing hardware |
| Cloud (optional) | $20-50/month | If deploying to VM |
| Storage | $0-5/month | If using cloud storage |

**Total Monthly Cost: $108-163**

---

## Risk Management

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Docling PDF parsing failures | High | Medium | Fallback to PyMuPDF |
| Metadata extraction low quality | Medium | High | Manual review option |
| API rate limits | Medium | Medium | Exponential backoff |
| Chroma performance at scale | Medium | Low | Monitor, optimize |
| Synthesis hallucination | High | Medium | Strict evidence-only prompt |

### Project Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Scope creep | High | Medium | Strict phase gates |
| API cost overruns | Medium | Low | Usage monitoring |
| PDF quality variation | Medium | High | Robust error handling |

---

## Team & Resources

### Development Team

| Role | Responsibility | Time |
|------|----------------|------|
| Lead Developer | Architecture, core implementation | 50% |
| Research Assistant | PDF collection, evaluation | 20% |
| QA/Testing | Quality assurance, validation | 15% |
| Documentation | User docs, examples | 15% |

### External Dependencies

| Dependency | Provider | SLA |
|------------|----------|-----|
| OpenRouter API | OpenRouter | 99.9% |
| Embedding API | Provider | 99.9% |
| Docling | Open source | Community |

---

## Communication Plan

### Weekly Check-ins

- **Monday**: Sprint planning, task assignment
- **Wednesday**: Progress review, blockers
- **Friday**: Demo, retrospective

### Documentation

- **Architecture docs**: Updated each phase
- **User guide**: Completed in Phase 5
- **API reference**: Auto-generated from code

### Stakeholder Updates

- **Bi-weekly**: Progress report to stakeholders
- **Monthly**: Demo of working system

---

## Quality Assurance

### Testing Strategy

| Test Type | Coverage | Frequency |
|-----------|----------|-----------|
| Unit tests | Core functions | Every commit |
| Integration tests | Pipeline stages | Every PR |
| End-to-end tests | Full workflow | Weekly |
| Performance tests | Latency, throughput | Phase 6 |

### Quality Gates

| Gate | Criteria | Phase |
|------|----------|-------|
| Foundation | All tests pass | 1 |
| Ingestion | 10 PDFs working | 2 |
| Retrieval | >80% relevance | 3 |
| Synthesis | Citation-grounded | 4 |
| Polish | CLI smooth | 5 |
| Scale | 100 PDFs working | 6 |

---

## Definition of Done

**The project is complete when:**

1. ✅ 100 PDFs ingested successfully
2. ✅ Queries return relevant chunks (>80% relevance)
3. ✅ Answers are citation-grounded
4. ✅ Interactive CLI works smoothly
5. ✅ Documentation is complete
6. ✅ Latency <4s per query
7. ✅ Monthly cost <$150

---

## Appendices

### Appendix A: API Key Management

```bash
# Environment variables
export OPENROUTER_API_KEY="..."
export EMBEDDING_API_KEY="..."

# Or use .env file
echo "OPENROUTER_API_KEY=..." >> .env
echo "EMBEDDING_API_KEY=..." >> .env
```

### Appendix B: Development Setup

```bash
# Clone repository
git clone <repo-url>
cd research-rag

# Install dependencies
pip install -e ".[dev]"

# Set up pre-commit
pre-commit install

# Run tests
pytest

# Start development
python -m research_rag
```

### Appendix C: Deployment Options

**Option 1: Local Development**
```bash
python -m research_rag
```

**Option 2: Docker**
```bash
docker-compose up -d
```

**Option 3: Cloud VM**
```bash
# SSH into VM
ssh user@vm-ip

# Run as service
systemctl start research-rag
```

---

*Project Plan v1.0 — Research RAG System*

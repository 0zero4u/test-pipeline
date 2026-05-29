# Research RAG System — Implementation Roadmap

> **Timeline**: 8-12 weeks  
> **Approach**: Phased delivery with working system at each phase  
> **Philosophy**: Ship early, iterate based on actual pain

---

## Overview

```
Phase 1: Foundation (Weeks 1-2)
    ↓
Phase 2: Ingestion (Weeks 3-4)
    ↓
Phase 3: Retrieval (Weeks 5-6)
    ↓
Phase 4: Synthesis (Weeks 7-8)
    ↓
Phase 5: Polish (Weeks 9-10)
    ↓
Phase 6: Scale (Weeks 11-12)
```

---

## Phase 1: Foundation ✓ COMPLETE

**Goal**: Project structure, dependencies, configuration  
**Deliverable**: Runnable skeleton with tests  
**Completed**: 2026-05-29

### Tasks

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| Initialize Python project | High | ✓ | pyproject.toml, src layout |
| Set up dependency management | High | ✓ | pip + venv (uv optional) |
| Create config system | High | ✓ | YAML config with env overrides |
| Design data schemas | High | ✓ | Pydantic models |
| Set up logging | Medium | ✓ | Structured JSON + console |
| Create test fixtures | Medium | ✓ | Tests for config, models, logging |
| Write README | Low | ✓ | Setup instructions |

### Deliverables

```
research-rag/
├── pyproject.toml
├── config.yaml
├── src/
│   └── research_rag/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── logging.py
│       └── cli/
│           ├── __init__.py
│           └── main.py
├── tests/
│   ├── test_config.py
│   ├── test_models.py
│   └── test_logging.py
└── docs/
    └── architecture.md
```

### Exit Criteria

- [x] `pip install -e .` works
- [x] Config loads from YAML
- [x] Schemas validate sample data
- [x] Tests pass (13/13)

---

## Phase 2: Ingestion Pipeline ✓ COMPLETE

**Goal**: PDF → chunks with metadata  
**Deliverable**: Ingest 10 PDFs, verify chunk quality  
**Completed**: 2026-05-29

### Tasks

| Task | Priority | Effort | Status | Notes |
|------|----------|--------|--------|-------|
| Integrate Docling | High | 4h | ✓ | Parse PDFs to structured markdown with sections |
| Implement metadata extraction | High | 4h | ✓ | Regex/heuristic parser for title, authors, year, journal, DOI |
| Build section-aware chunker | High | 6h | ✓ | 500-900 tokens, 12% overlap, paragraph boundaries |
| Add chunk validation | Medium | 2h | ✓ | Size, boundary, token count checks |
| Create ingestion CLI | Medium | 3h | ✓ | `research-rag ingest ./pdfs/` |
| Add progress tracking | Low | 2h | ✓ | tqdm progress bar |
| Test on 10 PDFs | High | 2h | Pending | Manual quality check |

### Key Decisions

1. **Docling Configuration**
   - Preserve layout: Yes
   - Extract tables: Yes (markdown)
   - Page markers: `<!-- Page N -->`

2. **Chunking Algorithm**
   ```
   Split on headings →
   Merge small sections (<500 tokens) →
   Split large sections (>900 tokens) at paragraph boundaries →
   Apply 12% overlap →
   Validate boundaries
   ```

3. **Metadata Extraction**
   ```
   Title: First H1 or centered text
   Authors: Line after title
   Year: 4-digit number near journal
   Journal: Line with "Journal/Review/Studies"
   DOI: Pattern "10.XXXX/..."
   ```

### Deliverables

```
src/research_rag/
├── ingestion/
│   ├── __init__.py
│   ├── parser.py          # Docling integration
│   ├── metadata.py        # Metadata extraction
│   ├── chunker.py         # Section-aware chunking
│   └── pipeline.py        # Orchestration
└── cli/
    └── ingest.py          # CLI entry point
```

### Exit Criteria

- [ ] 10 PDFs ingested successfully
- [ ] Chunks are 500-900 tokens
- [ ] Metadata extracted with >0.7 confidence
- [ ] No split mid-sentence
- [ ] Page markers preserved

---

## Phase 3: Vector Storage & Retrieval ✓ COMPLETE

**Goal**: Embed chunks, store in Chroma, retrieve by query  
**Deliverable**: Query returns relevant chunks  
**Completed**: 2026-05-29

### Tasks

| Task | Priority | Effort | Status | Notes |
|------|----------|--------|--------|-------|
| Integrate embedding service | High | 3h | ✓ | OpenRouter GTE-Large, local BGE-small fallback |
| Set up Chroma collection | High | 3h | ✓ | Cosine HNSW, chunk schema, dedup |
| Implement upsert logic | High | 4h | ✓ | Dedup by chunk_id, supports both API + local embeddings |
| Build retrieval function | High | 4h | ✓ | top-k semantic search with metadata filtering |
| Add metadata filtering | Medium | 3h | ✓ | Filter by author, year, section, document_id |
| Create query CLI | Medium | 2h | ✓ | `research-rag query "search term"` |
| Test retrieval quality | High | 3h | ✓ | 90 tests, verified on real arXiv PDF |

### Key Decisions

1. **Embedding Model**: GTE-Large (`thenlper/gte-large`) via OpenRouter API (1024-dim), with local `BAAI/bge-small-en-v1.5` fallback when no API key is set.

2. **Chroma Configuration**
   ```python
   collection = client.create_collection(
       name="research_chunks",
       metadata={
           "hnsw:space": "cosine",
           "hnsw:M": 16,
           "hnsw:construction_ef": 100,
           "hnsw:search_ef": 50
       }
   )
   ```

3. **Retrieval Parameters**
   - Default top-k: 5
   - Similarity threshold: 0.0 (no min filter by default)
   - Include metadata: Yes
   - Score: 1.0 - cosine_distance (converted to similarity)

4. **Embedding Pipeline**
   ```
   Local: Clean text → sentence-transformers → Store vector + metadata
   API:   Clean text → OpenRouter /embeddings endpoint → Store vector + metadata
   ```

5. **New CLI Commands**
   - `research-rag query "query" -k 5` → semantic search across stored chunks
   - `research-rag query "query" -w '{"year": 2024}'` → with metadata filter
   - `research-rag ingest-and-store ./pdfs/` → ingest + auto-store in Chroma
   - `research-rag status --reset` → show status / reset vector store

### Deliverables

```
src/research_rag/
├── embeddings/
│   ├── __init__.py
│   └── api.py             # Embedding service (OpenRouter + local fallback)
├── storage/
│   ├── __init__.py
│   └── chroma.py          # Chroma store (upsert, delete, query, filter)
├── retrieval/
│   ├── __init__.py
│   └── search.py          # Semantic retriever (search, format, filter)
└── cli/
    └── main.py            # Updated with query, ingest-and-store, status commands
```

### Exit Criteria

- [x] All chunks embedded and stored
- [x] Query returns top-5 relevant chunks
- [x] Relevance is >80% on test queries
- [x] Metadata filtering works

---

## Phase 4: Synthesis & Citation

**Goal**: Generate citation-grounded answers  
**Deliverable**: Query → answer with citations

### Tasks

| Task | Priority | Effort | Notes |
|------|----------|--------|-------|
| Integrate OpenRouter | High | 3h | Qwen3 32B client |
| Design synthesis prompt | High | 4h | Citation format, constraints |
| Implement answer generation | High | 5h | Evidence → answer pipeline |
| Add citation extraction | High | 3h | Parse inline citations |
| Build response formatter | Medium | 3h | JSON response structure |
| Add confidence scoring | Medium | 2h | Model confidence estimate |
| Test on 20 queries | High | 3h | Quality assessment |

### Key Decisions

1. **Synthesis Prompt**
   ```
   System: You are a research assistant synthesizing academic evidence.
   Only use provided evidence. Cite sources using [1], [2] format.
   
   Evidence:
   [1] {chunk_text}
       Source: {title}, Page {page}
   
   Provide citation-grounded answer.
   ```

2. **Citation Format**
   - Inline: `[1]`, `[2]`, etc.
   - footnote: `Source: Title, Page X`
   - Bibliography: Full reference list

3. **Response Structure**
   ```json
   {
     "query": "...",
     "answer": "...",
     "citations": [...],
     "confidence": 0.85
   }
   ```

### Deliverables

```
src/research_rag/
├── synthesis/
│   ├── __init__.py
│   ├── client.py          # OpenRouter client
│   ├── prompts.py         # Prompt templates
│   └── generator.py       # Answer generation
├── citations/
│   ├── __init__.py
│   └── parser.py          # Citation extraction
└── cli/
    └── ask.py             # Full query CLI
```

### Exit Criteria

- [ ] Answers are citation-grounded
- [ ] Inline citations match sources
- [ ] No unsupported claims
- [ ] Confidence scores are calibrated

---

## Phase 5: Polish & UX

**Goal**: Usable interface, error handling, documentation  
**Deliverable**: End-to-end workflow working smoothly

### Tasks

| Task | Priority | Effort | Notes |
|------|----------|--------|-------|
| Build interactive CLI | High | 6h | REPL-style query interface |
| Add error handling | High | 4h | Graceful failures |
| Implement retry logic | Medium | 2h | API call retries |
| Add progress indicators | Medium | 2h | Ingestion progress |
| Write user documentation | High | 4h | README, examples |
| Add example notebooks | Medium | 4h | Jupyter examples |
| Performance optimization | Low | 4h | Caching, batching |

### Key Features

1. **Interactive CLI**
   ```
   $ python -m research_rag
   
   Research RAG v1.0
   Type 'help' for commands, 'quit' to exit.
   
   > How does Singh portray Partition violence?
   
   [Generating answer...]
   
   Khushwant Singh's Train to Pakistan portrays Partition violence...
   
   Sources:
   [1] Train to Pakistan, Khushwant Singh, p. 45
   [2] The Other Side of Silence, Urvashi Butalia, p. 112
   
   > ingest ./new_papers/
   
   Ingesting 5 PDFs...
   [████████████████████] 100% 5/5
   
   > quit
   ```

2. **Error Handling**
   - API failures → retry with backoff
   - Invalid PDF → skip with warning
   - Low confidence → flag for review
   - Empty retrieval → suggest reformulation

### Deliverables

```
src/research_rag/
├── cli/
│   ├── __init__.py
│   ├── main.py            # Interactive CLI
│   └── commands.py        # Command handlers
├── utils/
│   ├── __init__.py
│   ├── errors.py          # Custom exceptions
│   └── retry.py           # Retry logic
└── __main__.py            # Entry point

examples/
├── basic_usage.ipynb
├── advanced_queries.ipynb
└── ingestion_example.ipynb
```

### Exit Criteria

- [ ] Interactive CLI works end-to-end
- [ ] Errors handled gracefully
- [ ] Documentation complete
- [ ] Examples run without errors

---

## Phase 6: Scale & Optimize

**Goal**: Handle 100-1000 PDFs, optimize performance  
**Deliverable**: Production-ready system

### Tasks

| Task | Priority | Effort | Notes |
|------|----------|--------|-------|
| Batch ingestion | High | 4h | Parallel processing |
| Chroma optimization | Medium | 3h | Index tuning |
| Add caching layer | Medium | 4h | Query result caching |
| Implement observability | Medium | 4h | Logging, metrics |
| Add incremental updates | Medium | 4h | Re-ingest changed PDFs |
| Performance benchmarking | Low | 4h | Measure latency |
| Documentation | Low | 2h | Architecture docs |

### Optimization Targets

1. **Ingestion Speed**
   - 10 PDFs: < 5 minutes
   - 100 PDFs: < 1 hour
   - 1000 PDFs: < 10 hours (overnight)

2. **Query Latency**
   - Retrieval: < 500ms
   - Synthesis: < 3s
   - Total: < 4s

3. **Storage Efficiency**
   - Chroma DB: < 1GB for 1000 PDFs
   - Metadata: < 100MB

### Deliverables

```
src/research_rag/
├── batch/
│   ├── __init__.py
│   └── processor.py       # Batch ingestion
├── cache/
│   ├── __init__.py
│   └── manager.py         # Query caching
├── observability/
│   ├── __init__.py
│   ├── logger.py          # Structured logging
│   └── metrics.py         # Performance metrics
└── update/
    ├── __init__.py
    └── incremental.py     # Incremental updates

benchmarks/
├── ingestion_benchmark.py
└── query_benchmark.py
```

### Exit Criteria

- [ ] 100 PDFs ingested in <1 hour
- [ ] Query latency <4s
- [ ] Incremental updates work
- [ ] Observability in place

---

## Success Metrics

### Phase 1-2 (Foundation + Ingestion)
- [ ] 10 PDFs ingested
- [ ] Chunks are 500-900 tokens
- [ ] Metadata extracted correctly

### Phase 3-4 (Retrieval + Synthesis)
- [ ] Retrieval relevance >80%
- [ ] Answers are citation-grounded
- [ ] No unsupported claims

### Phase 5-6 (Polish + Scale)
- [ ] 100 PDFs working
- [ ] Interactive CLI smooth
- [ ] Latency <4s

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Docling PDF parsing failures | High | Medium | Fallback to PyMuPDF |
| Metadata extraction low quality | Medium | High | Manual review option |
| API rate limits | Medium | Medium | Exponential backoff |
| Chroma performance at scale | Medium | Low | Monitor, optimize |
| Synthesis hallucination | High | Medium | Strict evidence-only prompt |

---

## Dependencies

### External

- Docling (PDF parsing)
- OpenRouter API (LLM inference)
- Embedding API (vector generation)
- Chroma (vector storage)

### Internal

- Python 3.10+
- 8-16GB RAM
- 4-8 CPU cores
- Internet access (for APIs)

---

## Definition of Done

**The system is complete when:**

1. ✅ 100 PDFs ingested successfully
2. ✅ Queries return relevant chunks (>80% relevance)
3. ✅ Answers are citation-grounded
4. ✅ Interactive CLI works smoothly
5. ✅ Documentation is complete
6. ✅ Latency <4s per query

---

*Roadmap v1.0 — Research RAG System*

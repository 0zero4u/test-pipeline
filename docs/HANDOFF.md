# Handoff: Where We Left Off

> **Date**: 2026-05-29  
> **Branch**: `dev` (Phase 7 complete, Phase 8 next)  
> **Tests**: 198 passing  
> **Status**: E2E verified on 2 real PDFs

---

## What's Done (Phases 1-7)

### Phase 1-6 (on `master`): RAG Pipeline
- PDF parsing (Docling) → metadata extraction → chunking (500-900 tokens)
- Chroma vector storage (GTE-Large 1024d via OpenRouter)
- Semantic retrieval (top-k search)
- Citation-grounded Q&A (deepseek-v4-flash via OpenRouter)
- Citation validation (author/year enrichment)
- Batch ingestion (ThreadPoolExecutor)
- LRU caching, incremental updates, observability, benchmarking
- Interactive REPL (ask, ingest, query, status, help, exit)

### Phase 7 (on `dev`): Chapter Writing Assistance
- `src/research_rag/writing/chapter_writer.py` — Section-by-section generation
- `src/research_rag/writing/mla_formatter.py` — MLA 9th Edition citations
- `src/research_rag/writing/outline.py` — ChapterOutline from plan
- `src/research_rag/writing/state.py` — DissertationState (cross-chapter tracking)
- `src/research_rag/writing/prompts.py` — Academic prose prompts
- REPL `write` command
- 20 tests in `tests/test_writing.py`

---

## E2E Verified (2 PDFs in /tmp/rag_pdfs/)

```
Step 1: ✅ Ingest 2 PDFs → 18 chunks in Chroma (GTE-Large embeddings)
Step 2: ✅ Query "Partition violence" → 5 relevant chunks (score 0.74-0.78)
Step 3: ✅ Ask → 0.95 confidence, 5 citations, full answer
Step 4: ✅ Write chapter → 1,765 words, 13 citations tracked
```

### PDFs used
- `rag_pdf1.pdf` (50K) — "Partition and Communal Violence in Train to Pakistan" — short paper (2 chunks)
- `rag_pdf2.pdf` (100K) — "Key Words: Affective politics..." by Dipak Raj Joshi — longer article (16 chunks)

---

## Known Issues to Fix

### 1. Metadata extraction is broken (HIGH PRIORITY)
**Problem**: Regex heuristics extract wrong authors.
- `rag_pdf1`: Authors = `["Khushwant Singh"]` — that's the novel's author, NOT the paper author
- `rag_pdf2`: Authors = `["Key  Words"]` — completely wrong, grabbed "Key Words" line

**Fix needed**: Improve `_extract_authors()` in `src/research_rag/ingestion/metadata.py`:
- Add smarter line-position heuristics (authors usually appear within 5 lines of title)
- Filter out non-name strings ("Key Words", "Abstract", single words)
- Add validation: at least 2 words, starts with capital, no special chars
- Consider LLM-based metadata extraction as fallback (like rag-pipeline does)

**Impact**: Works Cited shows "Unknown Author" because metadata is wrong.

### 2. Citation parsing in chapter writer
**Fixed**: Regex now handles `[N, p. X]` format (commit `31ed79c`).  
**Remaining**: LLM sometimes uses `(Author Year)` format instead of `[N]` — need to also parse that.

### 3. No .env file in repo (API key management)
**Status**: `.env` created locally with OpenRouter key.  
**Action**: Add `.env.example` template, ensure `.env` is in `.gitignore`.

---

## What's Next (Phase 8 candidates)

### Option A: Fix Metadata Extraction (recommended first)
- Improve regex patterns in `metadata.py`
- Add LLM-based metadata extraction fallback
- Re-ingest PDFs with correct metadata
- Verify Works Cited shows proper authors

### Option B: Chapter Writing Improvements
- Add `--sections` JSON flag to REPL `write` command (already partially implemented)
- Support `(Author Year)` citation format parsing
- Add Works Cited generation command (`research-rag citations`)
- Add chapter export to markdown/Word

### Option C: Real Dissertation Test
- Ingest full research PDFs (not just 2 smallest)
- Write complete Chapter 3 (all 5 sections from chapter_plan.md)
- Verify citation quality and academic prose

### Option D: Merge dev → master
- Phase 7 is stable and tested
- Merge to master for production use

---

## Key Files

```
src/research_rag/
├── ingestion/
│   ├── metadata.py          # NEEDS FIX: author extraction broken
│   ├── parser.py            # Docling PDF parsing
│   ├── chunker.py           # Section-aware chunking
│   └── pipeline.py          # Orchestration + ThreadPoolExecutor
├── retrieval/
│   └── search.py            # Retriever with semantic search
├── synthesis/
│   ├── client.py            # OpenRouter LLM client (lazy init)
│   ├── generator.py         # AnswerGenerator + cache + metrics
│   └── prompts.py           # Synthesis prompts
├── citations/
│   ├── parser.py            # [N] citation parser
│   └── validator.py         # Author/year validation
├── writing/                 # Phase 7 (NEW)
│   ├── chapter_writer.py    # Section-by-section generation
│   ├── mla_formatter.py     # MLA 9th Edition
│   ├── outline.py           # ChapterOutline
│   ├── state.py             # DissertationState
│   └── prompts.py           # Academic prose prompts
├── cache.py                 # LRU query cache
├── metrics.py               # Singleton metrics tracker
├── incremental.py           # SHA-256 change detection
├── benchmark.py             # Performance benchmarking
├── cli/
│   ├── main.py              # Click CLI
│   └── repl.py              # Interactive REPL (has 'write' command)
└── utils/
    ├── errors.py            # Exception hierarchy
    └── retry.py             # Exponential backoff

tests/
├── test_writing.py          # 20 writing tests
├── test_citations.py        # 19 citation tests
├── test_cache.py            # 7 cache tests
├── test_metrics.py          # 7 metrics tests
├── test_incremental.py      # 7 incremental tests
└── ... (198 total)
```

---

## Environment

- **Python**: 3.11.2 (Debian Bookworm)
- **Virtual env**: `.venv/` must be activated
- **Workdir**: `/home/arshhtripathi/test-pipeline`
- **Git**: `dev` branch, up to date with `origin/dev`
- **OpenRouter key**: Set via `.env` file or `OPENROUTER_API_KEY` env var
- **Chroma DB**: `./data/chroma/` (18 chunks from 2 PDFs)
- **Embedding model**: `thenlper/gte-large` (1024d) via OpenRouter API
- **LLM model**: `deepseek/deepseek-v4-flash` via OpenRouter

---

## Commands to Resume

```bash
cd /home/arshhtripathi/test-pipeline
source .venv/bin/activate
export OPENROUTER_API_KEY="sk-or-v1-..."  # Set from .env file

# Run tests
pytest tests/ -v

# Start REPL
research-rag repl

# Quick E2E test
python -c "
from research_rag.config import load_settings
from research_rag.embeddings import EmbeddingService
from research_rag.storage.chroma import ChromaStore
from research_rag.retrieval import Retriever
from research_rag.writing import ChapterWriter, ChapterOutline
from pathlib import Path
settings = load_settings()
embed = EmbeddingService(api_key=settings.openrouter_api_key)
store = ChromaStore(persist_directory=Path(settings.storage.chroma_path), embedding_service=embed)
retriever = Retriever(store=store, top_k=10)
writer = ChapterWriter(retriever=retriever)
outline = ChapterOutline(3, 'Test Chapter')
outline.add_section('3.1 Test', 'Test section', target_words=300)
result = writer.write_chapter(outline)
print(f'{result[\"word_count\"]} words, {len(result[\"citations\"])} citations')
"
```

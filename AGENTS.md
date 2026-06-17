# RESEARCH-RAG Knowledge Base

**Generated:** 2026-06-17
**Commit:** 81558cf
**Branch:** dev3

## OVERVIEW

Citation-grounded RAG system for humanities/literary analysis. Ingests academic PDFs, extracts structured content, answers research queries with MLA/APA inline citations and hallucination detection. Python 3.10+, Pydantic v2, ChromaDB, OpenRouter (deepseek-v4-flash, qwen3-embedding-8b).

## STRUCTURE

```
research-rag/
├── pyproject.toml              # Build/lint/test config
├── config.yaml                 # Runtime config
├── .env.example                # OPENROUTER_API_KEY template
├── src/research_rag/
│   ├── cli/                    # Click CLI + interactive REPL
│   ├── ingestion/              # PDF -> parse -> LLM metadata -> chunk
│   ├── embeddings/             # qwen3-embedding-8b (4096-dim)
│   ├── storage/                # ChromaDB wrapper
│   ├── retrieval/              # Semantic retriever
│   ├── synthesis/              # LLM answer + prompt templates
│   ├── citations/              # Parse -> validate -> format -> audit
│   └── utils/                  # Error hierarchy + tenacity retry
├── tests/                      # pytest, 64+ tests
├── docs/                       # Architecture, plan, roadmap
└── examples/                   # basic_usage.ipynb
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Entry point | `src/research_rag/cli/main.py` | Click group, 6 subcommands |
| Interactive REPL | `src/research_rag/cli/repl.py` | `research-rag repl` |
| Core models | `src/research_rag/models.py` | Chunk, Citation, DocumentMetadata |
| Config schema | `src/research_rag/config.py` | Pydantic Settings, YAML+env |
| PDF ingestion | `src/research_rag/ingestion/` | parser -> LLM metadata -> chunker -> pipeline |
| LLM metadata | `src/research_rag/ingestion/metadata.py` | LLMMetadataExtractor (regex->LLM fallback) |
| Embedding | `src/research_rag/embeddings/api.py` | qwen3-embedding-8b (4096-dim) |
| Chroma ops | `src/research_rag/storage/chroma.py` | CRUD, HNSW config |
| Semantic search | `src/research_rag/retrieval/search.py` | top-k, metadata filtering |
| Answer generation | `src/research_rag/synthesis/generator.py` | 7-step pipeline + optional auditor |
| Citation parser | `src/research_rag/citations/parser.py` | Extracts [N] markers from LLM output |
| Citation validator | `src/research_rag/citations/validator.py` | Author/year enrichment |
| Citation formatter | `src/research_rag/citations/formatter.py` | MLA/APA inline + Works Cited |
| Citation auditor | `src/research_rag/citations/auditor.py` | Hallucination detection (claim vs chunk) |
| Error handling | `src/research_rag/utils/errors.py` | 8 exception classes |
| Retry logic | `src/research_rag/utils/retry.py` | tenacity exponential backoff + jitter |
| Caching | `src/research_rag/cache.py` | diskcache LRU with TTL |
| Metrics | `src/research_rag/metrics.py` | Singleton latency/cache/error tracking |
| Prompt templates | `src/research_rag/synthesis/prompts.py` | Synthesis prompt with citation format rules |

## TWO PIPELINES

**INGESTION:** PDF -> `pymupdf4llm` parse -> regex+LLM metadata (title/author/year) -> section-aware chunking (500-900t, 12% overlap) -> `qwen3-embedding-8b` (4096-dim) -> Chroma HNSW index.

**QUERY:** Query -> Chroma top-k search -> build prompt -> OpenRouter LLM -> `CitationParser` ([N] markers) -> `CitationValidator` (enrich) -> `CitationAuditor` (hallucination check) -> `CitationFormatter` (MLA/APA) -> Works Cited. LRU cache via diskcache.

## KEY COMPONENTS

### Metadata Extraction
- Primary: regex heuristics (title, author, year, journal, DOI)
- Fallback: `LLMMetadataExtractor` calls deepseek-v4-flash via OpenRouter when confidence < 0.7
- Retry: 1 retry on transient API errors
- Multi-word author names supported (e.g. "Dipak Raj Joshi")

### Citation Formatting
- MLA: `(Smith 2021, p. 45)` — 1/2/3+ author variants, `n.d.` for missing year
- APA: `(Smith, 2021, p. 45)` — commas between fields
- Works Cited: deduplicated by document_id, sorted by last name
- Configurable via `CitationFormatter(style="mla")` or `CitationFormatter(style="apa")`

### Hallucination Detection (`CitationAuditor`)
- Extracts claims around [N] markers at 3 granularities (sentence, last-50, last-20 chars)
- Verifies claims against source chunk text via normalized substring matching
- Report-only: never modifies answer or citations
- Returns `hallucination_report` dict alongside answer

### Citation Format Drift Handling
- Parser/formatter/auditor all tolerate `[1, p. 2]` and `[1, pp. 2-3]` variants
- Prompt includes negative examples to enforce bare [N] format
- Backward compatible with standard [1], [1,2], [1-3] formats

## CONVENTIONS

- **Format/lint**: Black (100 chars) + Ruff (E,F,I,N,W,UP). No E501.
- **Types**: All functions annotated (mypy `disallow_untyped_defs`). Python 3.10+ syntax.
- **Tests**: `test_*.py` files, `test_*` functions, plain `assert`. No `conftest.py`.
- **Naming**: snake_case modules/functions, PascalCase classes, UPPER_CASE constants.
- **Config priority**: `.env` > env vars > `config.yaml` (lowest). pydantic-settings.
- **CLI framework**: Click + Rich.
- **Error hierarchy**: `ResearchRAGError` -> `ConfigError/APIError/IngestionError/RetrievalError` -> subclasses.

## ANTI-PATTERNS

- Broad `except Exception` — 12 sites across 9 files
- `type: ignore` in pipeline.py — list initialization pattern
- Encapsulation leak — ChromaStore accesses EmbeddingService private attrs
- Singleton — Metrics uses `__new__` override
- Empty `except: pass` in chroma.py

## COMMANDS

```bash
pip install -e ".[dev]"       # Install + dev deps
pytest tests/ -v              # Run all tests
ruff check src/ tests/        # Lint
black --check src/ tests/     # Format check
mypy src/                     # Type check
research-rag <cmd>            # CLI (ingest, query, ask, status, repl)
```

## QUICK REFERENCE

| Component | Library | Purpose |
|-----------|---------|---------|
| PDF parser | pymupdf4llm | PDF -> markdown (10-250x faster than Docling) |
| Metadata | regex + deepseek-v4-flash | Title/author/year extraction with LLM fallback |
| Chunking | custom section-aware | 500-900t, 12% overlap, page-aware |
| Embedding | qwen3-embedding-8b (4096-dim) | OpenRouter API, local BGE-small fallback |
| Vector DB | ChromaDB | HNSW index, metadata filtering |
| LLM | deepseek-v4-flash | Answer generation + citation grounding |
| Caching | diskcache | LRU with TTL (3600s) |
| Retry | tenacity | Exponential backoff + 25% jitter |
| Citation format | custom (150 lines) | MLA/APA inline + Works Cited |
| Hallucination check | custom (230 lines) | Claim-vs-source substring verification |

## NOTES

- OpenRouter API key required for embeddings + synthesis. Without it: local BGE-small + retrieval-only.
- MLA/APA formatter: `CitationFormatter` converts `[1]` -> `(Author Year, p. #)` with Works Cited.
- Hallucination detection: `CitationAuditor` checks claims against source chunks, report-only.
- PDF parser: `pymupdf4llm` replaces Docling + torch (~500MB saved).
- Caching: `diskcache` (disk-backed LRU with TTL) replaces custom JSON I/O.
- Retry: `tenacity` (exponential backoff + jitter) replaces custom retry decorator.
- Metadata: LLM fallback triggers when regex confidence < 0.7. Retry on API failure.
- All 6 dev phases complete.

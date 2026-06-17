# RESEARCH-RAG Knowledge Base

**Generated:** 2026-06-17
**Commit:** 8d51162
**Branch:** dev3

**Generated:** 2026-06-17
**Commit:** 6b3df2c
**Branch:** master

## OVERVIEW

Citation-grounded RAG system for humanities/literary analysis. Ingests academic PDFs, extracts structured content, answers research queries with inline citations. Python 3.10+, Pydantic v2, ChromaDB, OpenRouter (deepseek-v4-flash).

## STRUCTURE

```
research-rag/
├── pyproject.toml          # Single build/lint/test config
├── config.yaml             # Runtime config (ingestion, retrieval, synthesis)
├── .env.example            # OPENROUTER_API_KEY template
├── src/research_rag/       # All source code
│   ├── cli/                # Click CLI + interactive REPL
│   ├── ingestion/          # PDF → parse → metadata → chunk
│   ├── embeddings/         # OpenRouter API / local BGE-small fallback
│   ├── storage/            # ChromaDB wrapper (upsert, query, filter)
│   ├── retrieval/          # Semantic retriever (top-k, metadata filters)
│   ├── synthesis/          # LLM answer pipeline + prompt templates
│   ├── citations/          # Citation extraction + hallucination validation
│   └── utils/              # Exception hierarchy + retry decorator
├── tests/                  # pytest, 1 test file per module, 149+ tests
├── docs/                   # Architecture, plan, roadmap
└── examples/               # basic_usage.ipynb
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Entry point | `src/research_rag/cli/main.py` | Click group, 6 subcommands |
| Interactive REPL | `src/research_rag/cli/repl.py` | `research-rag repl` |
| Core models | `src/research_rag/models.py` | Chunk, Citation, DocumentMetadata |
| Config schema | `src/research_rag/config.py` | Pydantic Settings, YAML+env overrides |
| PDF ingestion | `src/research_rag/ingestion/` | 4 files: parser → metadata → chunker → pipeline |
| Embedding | `src/research_rag/embeddings/api.py` | OpenRouter GTE-Large / local BGE-small |
| Chroma ops | `src/research_rag/storage/chroma.py` | CRUD, metadata filtering, HNSW config |
| Semantic search | `src/research_rag/retrieval/search.py` | top-k, cross-domain reranking |
| Answer generation | `src/research_rag/synthesis/generator.py` | 6-step pipeline (cache→retrieve→prompt→LLM→parse→validate) |
| Citation validation | `src/research_rag/citations/validator.py` | Author/year enrichment, hallucination detection |
| Error handling | `src/research_rag/utils/errors.py` | 8 exception classes |
| Retry logic | `src/research_rag/utils/retry.py` | Exponential backoff + jitter |
| Caching | `src/research_rag/cache.py` | LRU with disk persistence |
| Metrics | `src/research_rag/metrics.py` | Singleton latency/cache/error tracking |
| Benchmark | `src/research_rag/benchmark.py` | Ingestion speed + query latency |
| Tests | `tests/` | pytest, one test file per module |
| Architecture docs | `docs/architecture.md` | System design, data schemas, pipeline flows |

## TWO PIPELINES

**INGESTION:** PDF → `pymupdf4llm` parse → regex metadata → section-aware chunking (500-900t, 12% overlap) → embedding → Chroma HNSW index. SHA-256 incremental update.

**QUERY:** Query → embedding → Chroma top-k search → `build_synthesis_messages()` → OpenRouter LLM → citation parse + validate → confidence score (30% coverage + 70% relevance). LRU cache.

## CONVENTIONS

- **Format/lint**: Black (100 chars) + Ruff (E,F,I,N,W,UP). No E501 (Black handles).
- **Types**: All functions annotated (mypy `disallow_untyped_defs`). Python 3.10+ `| None` syntax.
- **Tests**: `test_*.py` files, `test_*` functions, plain `assert`. No `conftest.py` (fixtures per-file).
- **Naming**: snake_case modules/functions, PascalCase classes, UPPER_CASE constants.
- **Config priority**: `.env` > env vars > `config.yaml` (lowest). Loaded via pydantic-settings.
- **CLI framework**: Click + Rich (no argparse, no print()).
- **Error hierarchy**: `ResearchRAGError` → `ConfigError/APIError/IngestionError/RetrievalError` → `AuthenticationError/RateLimitError/ServerError`.
- **No CI/CD**: No Docker, no GitHub Actions, no Makefile. All automation via pyproject.toml.

## ANTI-PATTERNS (THIS PROJECT)

- **Broad `except Exception`** — 12 sites across 9 files. Catch specific exceptions instead.
- **`type: ignore` in pipeline.py** — `results = [None] * len(pdf_files)`. Use `results.append()` pattern.
- **Encapsulation leak** — `ChromaStore` accesses `_using_local` / `_get_local_ef()` on `EmbeddingService`. Make these public.
- **Singleton** — `Metrics` uses `__new__` override. Prefer DI for testability.
- **Empty `except: pass`** — `chroma.py:281` swallows NotFoundError silently.
- **Duplicated URL** — `OPENROUTER_BASE_URL` defined in both `embeddings/api.py` and `synthesis/client.py`.

## COMMANDS

```bash
pip install -e ".[dev]"       # Install + dev deps
pytest tests/ -v              # Run all tests
pytest --cov=research_rag     # Coverage
ruff check src/ tests/        # Lint
black --check src/ tests/     # Format check
mypy src/                     # Type check
research-rag <cmd>            # CLI (ingest, query, ask, status, repl)
```

## NOTES

- OpenRouter API key required for embeddings + synthesis. Without it: local BGE-small fallback + retrieval-only mode.
- Caching: `diskcache` (disk-backed LRU with TTL) — replaces custom JSON I/O cache.
- Retry: `tenacity` (exponential backoff + jitter) — replaces custom retry decorator.
- PDF parser: `pymupdf4llm` (10-250x faster, tables/formulas/OCR) — replaces Docling + torch.
- Chroma data persists in `./data/chroma`. Reset via `research-rag status --reset`.
- All 6 dev phases complete (Foundation → Ingestion → Storage/Retrieval → Synthesis → Polish → Scale/Optimize).

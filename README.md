# Research RAG

Citation-grounded research assistance for humanities/literary analysis.

## Status

**Phase 1: Foundation** — Complete ✓  
**Phase 2: Ingestion Pipeline** — Complete ✓  
**Phase 3: Vector Storage & Retrieval** — Complete ✓  
**Phase 4: Synthesis & Citation** — Complete ✓  
**Phase 5: Polish & UX** — Complete ✓  
**Phase 6: Scale & Optimize** — Complete ✓  
**Phase 7: Chapter Writing Assistance** — Complete ✓  
**Phase 8: MLA Citation Support** — Complete ✓  
**Phase 9: GLiNER Metadata Extraction** — Complete ✓

## Overview

A RAG system optimized for humanities research. Ingests academic PDFs, extracts structured content, and provides citation-grounded answers to research queries via an interactive REPL.

## Quick Start

```bash
# Clone and enter project
git clone <repo>
cd research-rag

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install CPU-only PyTorch (required for local embedding fallback)
pip install --index-url https://download.pytorch.org/whl/cpu torch

# Install dependencies
pip install -e ".[dev]"

# Set API key (or create .env file)
export OPENROUTER_API_KEY="sk-or-v1-..."

# Run tests
pytest tests/ -v

# Start interactive REPL
research-rag repl
```

## Usage

### Interactive REPL (recommended)

```text
$ research-rag repl

╭──────────────────────────────────────────╮
│         Research RAG Interactive         │
│        Type 'help' for commands          │
╰──────────────────────────────────────────╯

research-rag> help

Available commands:
  ask "question" -k N     Ask a research question
  ingest ./path/          Ingest PDFs into Chroma
  query "search" -k N     Semantic search
  write N "Title"         Write a chapter from outline
  dissertation ./plan.md  Write full dissertation from plan
  status                  Show system status
  history                 Show query history
  help                    Show this help
  exit / quit             Exit REPL

research-rag> ingest ./papers/
  Processing: 2 PDFs, 18 chunks created ✓

research-rag> ask "What caused Partition violence?"
  Answer: 6 bullet points cited from 5 sources (confidence: 0.90)

research-rag> query "Singh train to pakistan" -k 3
  [0.917] Partition and Communal Violence in Train to Pakistan
  [0.892] Key Words: Affective politics; Bhisham Sahni...
  [0.890] Partition and Communal Violence in Train to Pakistan

research-rag> exit
```

### Individual Commands

```bash
# Ingest PDFs (saves chunks to disk)
research-rag ingest ./pdfs/

# Ingest and auto-store to Chroma
research-rag ingest-and-store ./pdfs/

# Semantic search across stored chunks
research-rag query "partition violence" -k 5

# Filter by year or document
research-rag query "affective politics" -w '{"year":2020}'

# Citation-grounded Q&A (requires API key)
research-rag ask "What does Singh say about state failure?" -k 5

# Show status / reset vector store
research-rag status
research-rag status --reset

# Start interactive REPL
research-rag repl

# Write a chapter from outline
research-rag write 3 "Partition and Violence" --context "Comparative study"

# Write full dissertation from chapter plan
research-rag dissertation ./chapter_plan.md --title "My Thesis" --output dissertation.md
```

## Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Config | Pydantic v2 + YAML + .env | Settings with env/file overrides |
| Models | Pydantic v2 | Data schemas (Chunk, Citation, etc.) |
| CLI | Click + Rich | Command-line + interactive REPL |
| PDF Parser | Docling | Parse PDFs to structured markdown |
| Chunking | Custom section-aware | 500-900 tokens, 12% overlap |
| Metadata | Regex + GLiNER | Title, authors, year, journal extraction |
| NER | GLiNER (gliner_small) | Person, date, organization extraction |
| Embeddings | GTE-Large (OpenRouter) / BGE-small (local) | Semantic vectors |
| Vector DB | Chroma (persistent, cosine HNSW) | Store + search embeddings |
| Synthesis | deepseek/deepseek-v4-flash (OpenRouter) | Citation-grounded answers |
| MLA Formatting | Custom MLA 9th Edition | Journal, book, film, edited volume citations |
| Chapter Writing | DissertationWriter + ChapterWriter | Section-by-section academic generation |
| Caching | LRU with disk persistence | Query result caching |
| Batch Ingestion | ThreadPoolExecutor (4 workers) | Parallel PDF processing |
| Incremental Updates | SHA-256 manifest | Only re-ingest changed PDFs |
| Observability | Singleton Metrics tracker | Latency, cache hit rate, API errors |
| Benchmarking | Custom benchmark module | Ingestion speed + query latency |
| Error Handling | Custom exceptions with retry | Exponential backoff + jitter |

## Hardware

- **RAM**: 8-16GB
- **CPU**: 4-8 cores
- **GPU**: Not required (all heavy compute via API)
- **Storage**: 10-50GB

## Project Structure

```
research-rag/
├── pyproject.toml                  # Project config, dependencies
├── config.yaml                    # Default settings
├── .env.example                   # API key template
├── src/research_rag/
│   ├── config.py                  # Settings (YAML + .env + env vars)
│   ├── models.py                  # Pydantic schemas
│   ├── logging.py                 # Structured logging
│   ├── cli/
│   │   ├── main.py                # Click CLI entry point
│   │   └── repl.py                # Interactive REPL
│   ├── ingestion/
│   │   ├── pipeline.py            # PDF ingestion orchestrator
│   │   ├── parser.py              # Docling integration
│   │   ├── metadata.py            # Metadata extraction
│   │   └── chunker.py             # Section-aware chunking
│   ├── embeddings/
│   │   └── api.py                 # Embedding service (OpenRouter + local)
│   ├── storage/
│   │   └── chroma.py              # Chroma store (upsert, query, filter)
│   ├── retrieval/
│   │   └── search.py              # Semantic retriever
│   ├── synthesis/
│   │   ├── client.py              # OpenRouter LLM client
│   │   ├── prompts.py             # Synthesis prompt templates
│   │   └── generator.py           # Answer generation pipeline
│   ├── citations/
│   │   ├── parser.py              # Inline citation extraction
│   │   └── validator.py           # Citation validation
│   ├── writing/
│   │   ├── chapter_writer.py      # Section-by-section chapter generation
│   │   ├── dissertation_writer.py # Full dissertation orchestration
│   │   ├── mla_formatter.py       # MLA 9th Edition citations
│   │   ├── outline.py             # Chapter outline parsing
│   │   ├── prompts.py             # Academic prose prompts
│   │   └── state.py               # Cross-chapter state tracking
│   └── utils/
│       ├── errors.py              # Custom exception hierarchy
│       └── retry.py               # Exponential backoff decorator
├── tests/                         # 79+ tests
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_metadata.py
│   ├── test_mla_formatter.py
│   ├── test_dissertation_writer.py
│   ├── test_citations.py
│   └── ...
└── examples/
    └── basic_usage.ipynb          # Jupyter notebook
```

## Key Features

- **Citation-grounded answers**: LLM can only use provided evidence. Inline citations [1], [2] with source attribution. No hallucination — says "no direct evidence" when insufficient.
- **GLiNER metadata extraction**: NER model extracts author names, dates, organizations from PDFs. Falls back when regex fails.
- **Chapter writing**: Generate dissertation chapters section-by-section with retrieval and citations.
- **MLA 9th Edition formatting**: Inline citations (Author Page) + Works Cited page. Supports journal articles, books, films, edited volumes.
- **Dissertation orchestration**: Parse `chapter_plan.md` and write full dissertation with cross-chapter state tracking.
- **Interactive REPL**: Multi-turn Q&A with command history, tab completion, Rich-formatted output.
- **Graceful fallback**: Works without API keys (local embeddings via BGE-small, retrieval-only mode without synthesis).
- **Retry with backoff**: Exponential backoff ±25% jitter on API calls. Structured exception hierarchy.
- **Dotenv support**: `OPENROUTER_API_KEY` auto-loaded from `.env` file.
- **Cost-optimized**: ~$17/month for 100 queries/day (deepseek-v4-flash + GTE-Large).

## Configuration

Copy `.env.example` to `.env` and add your OpenRouter API key:

```bash
cp .env.example .env
# Edit .env with your key
```

Settings are loaded from: `.env` → environment variables → `config.yaml` (lowest priority).

## Documentation

- [Project Plan](docs/plan.md)
- [Roadmap](docs/roadmap.md)

## License

MIT

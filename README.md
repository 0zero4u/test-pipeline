# test-pipeline

Citation-grounded research assistance for humanities/literary analysis.

## Status

**Phase 1: Foundation** — Complete ✓  
**Phase 2: Ingestion Pipeline** — Complete ✓

## Overview

A RAG system optimized for humanities research that ingests academic PDFs and provides citation-grounded answers to research queries.

## Architecture

```
PDF → Docling → Chunking → DeepSeek V4 Flash (entities) → Embedding API → Chroma
                                                                                  ↓
Query → Embedding → Chroma Retrieval → DeepSeek V4 Flash (synthesis) → Citation-Grounded Answer
```

## Stack

| Component | Technology | Purpose | Status |
|-----------|------------|---------|--------|
| Config | Pydantic + YAML | Settings with env overrides | ✓ |
| Models | Pydantic v2 | Data schemas (Chunk, Citation, etc.) | ✓ |
| Logging | Python logging | Structured JSON + console | ✓ |
| CLI | Click + Rich | Command-line interface | ✓ |
| PDF Parser | Docling | Parse PDFs to structured markdown | ✓ |
| Entity Extraction | DeepSeek V4 Flash via OpenRouter | Extract people, works, themes | Phase 3 |
| Embeddings | BGE-base-en-v1.5 via API | Generate semantic vectors | Phase 3 |
| Vector DB | Chroma | Store embeddings + metadata | Phase 3 |
| Synthesis | DeepSeek V4 Flash via OpenRouter | Cross-paper reasoning | Phase 4 |

## Project Structure

```
research-rag/
├── pyproject.toml              # Project config, dependencies
├── config.yaml                 # Default settings
├── src/research_rag/
│   ├── __init__.py
│   ├── config.py               # Settings (YAML + env overrides)
│   ├── models.py               # Pydantic schemas
│   ├── logging.py              # Structured logging
│   └── cli/
│       ├── __init__.py
│       └── main.py             # CLI entry point
└── tests/
    ├── test_config.py          # 4 tests
    ├── test_models.py          # 5 tests
    └── test_logging.py         # 4 tests
```

## Hardware Requirements

- **RAM**: 8-16GB
- **CPU**: 4-8 cores
- **GPU**: Not required (all heavy compute via API)
- **Storage**: 10-50GB

## Quick Start

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install CPU-only PyTorch
pip install --index-url https://download.pytorch.org/whl/cpu torch

# Install dependencies
pip install -e ".[dev]"

# Set API keys
export OPENROUTER_API_KEY="..."
export EMBEDDING_API_KEY="..."

# Run tests
pytest tests/ -v

# Check status
research-rag status
```

## Commands

```bash
# Ingest PDFs (Phase 2)
research-rag ingest ./pdfs/

# Query (Phase 4)
research-rag query "How does Singh portray Partition violence?"

# Check status
research-rag status
```

## Documentation

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Project Plan](docs/plan.md)

## License

MIT

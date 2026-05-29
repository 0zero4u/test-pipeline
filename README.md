# test-pipeline

Citation-grounded research assistance for humanities/literary analysis.

## Overview

A RAG system optimized for humanities research that ingests academic PDFs and provides citation-grounded answers to research queries.

## Architecture

```
PDF → Docling → Chunking → Qwen3 8B (entities) → Embedding API → Chroma
                                                                          ↓
Query → Embedding → Chroma Retrieval → Qwen3 32B (synthesis) → Citation-Grounded Answer
```

## Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| PDF Parser | Docling | Parse PDFs to structured markdown |
| Entity Extraction | Qwen3 8B via OpenRouter | Extract people, works, themes |
| Embeddings | BGE-base-en-v1.5 via API | Generate semantic vectors |
| Vector DB | Chroma | Store embeddings + metadata |
| Synthesis | Qwen3 32B via OpenRouter | Cross-paper reasoning |

## Hardware Requirements

- **RAM**: 8-16GB
- **CPU**: 4-8 cores
- **GPU**: Not required (all heavy compute via API)
- **Storage**: 10-50GB

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set API keys
export OPENROUTER_API_KEY="..."
export EMBEDDING_API_KEY="..."

# Ingest PDFs
python -m research_rag ingest --input ./pdfs/

# Query
python -m research_rag query "How does Singh portray Partition violence?"
```

## Documentation

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Project Plan](docs/plan.md)

## License

MIT

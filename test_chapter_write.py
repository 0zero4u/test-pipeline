#!/usr/bin/env python3
"""Test script for chapter writing with real PDFs."""

import sys
sys.path.insert(0, "/home/arshhtripathi/test-pipeline/src")

from pathlib import Path
from research_rag.config import load_settings
from research_rag.embeddings import EmbeddingService
from research_rag.storage.chroma import ChromaStore
from research_rag.retrieval import Retriever
from research_rag.writing import DissertationWriter, DissertationState, MLAFormatter

# Load settings
settings = load_settings()

# Initialize components
print("Initializing components...")
embed_service = EmbeddingService(api_key=settings.openrouter_api_key)
store = ChromaStore(
    persist_directory=Path(settings.storage.chroma_path),
    embedding_service=embed_service,
)
retriever = Retriever(store=store, top_k=5)
state = DissertationState()
formatter = MLAFormatter()

# Create DissertationWriter
writer = DissertationWriter(
    retriever=retriever,
    state=state,
    formatter=formatter,
    top_k=5,
)

# Test parsing a simple chapter plan
simple_plan = """### Chapter I — Introduction

#### 1.1 Historical Background
- The Partition of India in 1947
- Violence and communal division

#### 1.2 About the Novel
- Khushwant Singh's Train to Pakistan
- Major themes: violence, humanism, sacrifice
"""

print("\nParsing chapter plan...")
chapters = writer.parse_chapter_plan(simple_plan)
print(f"Found {len(chapters)} chapter(s)")
print(f"Chapter 1: {chapters[0].title}")
print(f"Sections: {[s.title for s in chapters[0].sections]}")

# Write a single chapter
print("\nWriting Chapter 1...")
result = writer.write_single_chapter(
    chapter_number=1,
    title="Introduction to Partition Literature",
    context="Academic study of violence and humanism in Partition narratives",
    sections_data=[
        {"title": "1.1 Historical Background", "description": "The Partition of India in 1947 and its aftermath"},
        {"title": "1.2 About Train to Pakistan", "description": "Khushwant Singh's novel and its themes"},
    ],
)

print(f"\nChapter complete!")
print(f"Word count: {result['word_count']}")
print(f"Citations: {len(result['citations'])}")
print(f"\nFirst 500 chars of text:")
print(result["chapter_text"][:500])

# Get works cited
works_cited = writer.get_works_cited()
if works_cited:
    print(f"\n{'='*50}")
    print(works_cited[:1000])

print("\nTest complete!")

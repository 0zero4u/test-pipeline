#!/usr/bin/env python3
"""Write Chapter 1 using the 2 smallest PDFs."""

import sys
sys.path.insert(0, "/home/arshhtripathi/test-pipeline/src")

from pathlib import Path
from research_rag.config import load_settings
from research_rag.embeddings import EmbeddingService
from research_rag.storage.chroma import ChromaStore
from research_rag.retrieval import Retriever
from research_rag.writing import DissertationWriter, DissertationState, MLAFormatter

settings = load_settings()

print("Initializing...")
embed_service = EmbeddingService(api_key=settings.openrouter_api_key)
store = ChromaStore(
    persist_directory=Path(settings.storage.chroma_path),
    embedding_service=embed_service,
)
retriever = Retriever(store=store, top_k=10)
state = DissertationState()
formatter = MLAFormatter()

writer = DissertationWriter(
    retriever=retriever,
    state=state,
    formatter=formatter,
    top_k=10,
)

chapter_plan = """### Chapter I — Introduction

#### 1.1 Historical Background: The Partition of India
- Political and socio-historical context of the 1947 Partition
- Causes and consequences of communal division
- Violence, migration, and displacement

#### 1.2 About Khushwant Singh
- Life and literary background
- Contribution to Partition literature
- Themes and writing style

#### 1.3 Introduction to the Novel Train to Pakistan
- Plot overview
- Major characters and setting (Mano Majra)
- Major themes: violence, communalism, sacrifice, humanism

#### 1.4 Research Methodology and Scope
- Comparative textual analysis
- Historical and literary approach
- Scope and limitations of the study

#### 1.5 Thesis Statement
- Central argument of the dissertation
"""

print("Writing Chapter 1...")
result = writer.write_single_chapter(
    chapter_number=1,
    title="Introduction",
    context="Academic study of Partition violence and humanism in Khushwant Singh's Train to Pakistan",
    sections_data=[
        {"title": "1.1 Historical Background: The Partition of India", "description": "Political and socio-historical context of the 1947 Partition, causes and consequences of communal division, violence, migration, and displacement"},
        {"title": "1.2 About Khushwant Singh", "description": "Life and literary background, contribution to Partition literature, themes and writing style"},
        {"title": "1.3 Introduction to the Novel Train to Pakistan", "description": "Plot overview, major characters and setting (Mano Majra), major themes: violence, communalism, sacrifice, humanism"},
        {"title": "1.4 Research Methodology and Scope", "description": "Comparative textual analysis, historical and literary approach, scope and limitations of the study"},
        {"title": "1.5 Thesis Statement", "description": "Central argument of the dissertation"},
    ],
)

print(f"\nChapter complete!")
print(f"Word count: {result['word_count']}")
print(f"Citations: {len(result['citations'])}")

chapter_text = result["chapter_text"]
works_cited = writer.get_works_cited()

output = f"""# Chapter I — Introduction

{chapter_text}

---

{works_cited}
"""

output_path = Path("/home/arshhtripathi/test-pipeline/chapter_1_output.md")
output_path.write_text(output)
print(f"\nSaved to {output_path}")
print(f"\nFirst 1000 chars:")
print(chapter_text[:1000])

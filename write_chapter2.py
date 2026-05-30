#!/usr/bin/env python3
"""Write Chapter II: Review of Literature using the Research RAG pipeline."""

import sys
sys.path.insert(0, "/home/arshhtripathi/test-pipeline/src")

from pathlib import Path
from research_rag.config import load_settings
from research_rag.embeddings import EmbeddingService
from research_rag.storage.chroma import ChromaStore
from research_rag.retrieval import Retriever
from research_rag.synthesis.client import SynthesisClient
from research_rag.writing import MLAFormatter
from research_rag.writing.chapter_writer import ChapterWriter
from research_rag.writing.outline import ChapterOutline

settings = load_settings()

print("Initializing...")
embed_service = EmbeddingService(api_key=settings.openrouter_api_key)
store = ChromaStore(
    persist_directory=Path(settings.storage.chroma_path),
    embedding_service=embed_service,
)
retriever = Retriever(store=store, top_k=12)
formatter = MLAFormatter()

# Create SynthesisClient with high reasoning effort
synthesis_client = SynthesisClient(
    api_key=settings.openrouter_api_key,
    reasoning_effort="high",
)

chapter_writer = ChapterWriter(
    retriever=retriever,
    synthesis_client=synthesis_client,
    formatter=formatter,
    top_k=12,
)

# Define all 7 sections for Chapter II
sections_data = [
    {
        "title": "2.1 Overview of Partition Literature",
        "description": "Development and major themes of Partition writing, key authors and texts including Butalia, Singh, Manto, and other canonical works of Partition literature",
        "target_words": 1100,
    },
    {
        "title": "2.2 Critical Studies on Train to Pakistan",
        "description": "Scholarly interpretations of the novel, themes of violence, nationalism, and identity in Khushwant Singh's Train to Pakistan",
        "target_words": 1100,
    },
    {
        "title": "2.3 Studies on Violence and Communalism",
        "description": "Critical discussions on communal conflict and brutality in Partition literature, scholarly analysis of violence in Train to Pakistan and comparable texts",
        "target_words": 900,
    },
    {
        "title": "2.4 Studies on Humanism and Moral Crisis",
        "description": "Compassion, ethical conflict, sacrifice, and morality in literary criticism of Partition texts, humanist themes in Train to Pakistan",
        "target_words": 900,
    },
    {
        "title": "2.5 Studies on Film Adaptation",
        "description": "Theories of adaptation, literary texts adapted into films, a comparison of novel and film adaptation of Train to Pakistan, cinematic versus literary representation",
        "target_words": 900,
    },
    {
        "title": "2.6 Existing Scholarship on Train to Pakistan and Partition Narratives",
        "description": "Comparative overview of existing academic studies on Train to Pakistan and Partition narratives, gaps in comparative novel-film scholarship",
        "target_words": 900,
    },
    {
        "title": "2.7 Research Gap",
        "description": "What previous studies have not sufficiently explored, justification for the present comparative study of novel and film adaptation of Train to Pakistan",
        "target_words": 550,
    },
]

chapter_context = (
    "Academic literature review examining Partition writing, Train to Pakistan scholarship, "
    "violence and communalism studies, humanism, film adaptation theory, and identifying research gaps "
    "for a comparative study of Khushwant Singh's novel and its film adaptation"
)

outline = ChapterOutline(2, "Review of Literature")

for sec in sections_data:
    # Get target_words from sec dict, default 1000
    target = sec.get("target_words", 1000)
    section = outline.add_section(sec["title"], sec["description"])
    section.target_words = target

print(f"Writing Chapter II with {len(outline.sections)} sections...")
print(f"Reasoning effort: high, top_k: 12")

result = chapter_writer.write_chapter(
    outline,
    chapter_context=chapter_context,
)

print(f"\nChapter complete!")
print(f"Word count: {result['word_count']}")
print(f"Citations: {len(result['citations'])}")

chapter_text = result["chapter_text"]
works_cited = chapter_writer.get_works_cited()

output = f"""# Chapter II — Review of Literature

{chapter_text}

---

{works_cited}
"""

output_path = Path("/home/arshhtripathi/chapter/Chapter_II_Literature_Review.md")
output_path.write_text(output)
print(f"\nSaved to {output_path}")
print(f"\nStats: {chapter_writer.get_stats()}")
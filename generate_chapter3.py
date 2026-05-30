#!/usr/bin/env python3
"""Generate Chapter III using Research RAG DissertationWriter pipeline."""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from research_rag.config import load_settings
from research_rag.embeddings import EmbeddingService
from research_rag.retrieval import Retriever
from research_rag.storage.chroma import ChromaStore
from research_rag.writing.dissertation_writer import DissertationWriter
from research_rag.writing.outline import ChapterOutline
from research_rag.writing.mla_formatter import MLAFormatter
from research_rag.writing.state import DissertationState

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    # Load settings
    settings = load_settings(Path(__file__).parent / "config.yaml")
    
    logger.info("Initializing embedding service...")
    embed_service = EmbeddingService(
        api_key=settings.openrouter_api_key,
    )
    
    logger.info("Initializing Chroma store...")
    store = ChromaStore(
        persist_directory=Path(settings.storage.chroma_path),
        embedding_service=embed_service,
    )
    
    logger.info("Initializing retriever...")
    retriever = Retriever(
        store=store,
        top_k=15,  # top_k=15 for this longest chapter
    )
    
    # Check store
    chunk_count = store.count()
    logger.info(f"Chroma store has {chunk_count} chunks")
    
    # Create formatter and state
    formatter = MLAFormatter()
    state = DissertationState()
    
    logger.info("Initializing DissertationWriter with top_k=15...")
    writer = DissertationWriter(
        retriever=retriever,
        state=state,
        formatter=formatter,
        top_k=15,
    )
    
    # Chapter III outline
    sections_data = [
        {
            "title": "3.1 Historical Violence in the Novel",
            "description": "Representation of Partition riots and brutality, social and political dimensions of violence. Compare novel versus film in depicting historical violence."
        },
        {
            "title": "3.2 Communal Breakdown in Mano Majra",
            "description": "Collapse of communal harmony, Hindu-Muslim-Sikh relationships. Compare how novel and film adaptation portray the dissolution of social bonds."
        },
        {
            "title": "3.3 Displacement and Refugee Trauma",
            "description": "Forced migration and psychological suffering, loss, fear, and displacement. Examine how both novel and film represent refugee experience."
        },
        {
            "title": "3.4 Violence in the Film Adaptation",
            "description": "Visual portrayal of brutality and communal tension, cinematic representation of trauma. Analyze the film adaptation's visual strategies for depicting violence."
        },
        {
            "title": "3.5 Comparative Analysis of Violence in the Novel and Film",
            "description": "Similarities and differences in representation, narrative versus visual impact. Synthesize how the two media differ in their treatment of violence."
        },
    ]
    
    outline = ChapterOutline.from_chapter_plan(
        chapter_number=3,
        title="Partition and Violence in Train to Pakistan",
        sections_data=sections_data,
        description=(
            "Chapter III examines the representation of Partition violence across Khushwant Singh's novel "
            "Train to Pakistan and Pamela Rooks' 1998 film adaptation. The chapter analyzes historical "
            "violence, communal breakdown, displacement trauma, cinematic depiction of brutality, and "
            "provides a comparative synthesis of novel and film. Each section compares the literary and "
            "cinematic treatments of the respective theme."
        ),
    )
    
    # Update target words for each section (1500-1800 each)
    for section in outline.sections:
        section.target_words = 1700
    
    writer.chapter_writer.synthesis_client.max_tokens = 6000
    logger.info(f"Writing Chapter III with {len(outline.sections)} sections, max_tokens=6000...")
    result = writer.chapter_writer.write_chapter(outline)
    
    chapter_text = result["chapter_text"]
    word_count = result["word_count"]
    citations = result["citations"]
    
    logger.info(f"Chapter written: {word_count} words, {len(citations)} citations")
    
    # Add chapter header
    full_text = f"# Chapter III\n\n# Partition and Violence in Train to Pakistan\n\n{chapter_text}"
    
    # Append Works Cited
    works_cited = writer.get_works_cited()
    if works_cited:
        full_text += f"\n\n---\n\n# Works Cited\n\n{works_cited}"
    
    # Save output
    output_path = Path(__file__).parent / "chapter" / "Chapter_III_Partition_Violence.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(full_text)
    
    logger.info(f"Saved to {output_path}")
    
    # Print stats
    logger.info(f"Total words: {len(full_text.split())}")
    logger.info(f"Total citations: {len(citations)}")
    
    return result


if __name__ == "__main__":
    main()
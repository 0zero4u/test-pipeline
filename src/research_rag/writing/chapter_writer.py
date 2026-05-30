"""Chapter writer for dissertation generation."""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from research_rag.retrieval import Retriever
from research_rag.synthesis.client import SynthesisClient
from research_rag.writing.mla_formatter import MLAFormatter
from research_rag.writing.outline import ChapterOutline, ChapterSection
from research_rag.writing.prompts import build_section_prompt, build_works_cited_prompt
from research_rag.writing.state import DissertationState

logger = logging.getLogger(__name__)


class ChapterWriter:
    """Generates dissertation chapters section-by-section with citations.

    Pipeline: outline → for each section: retrieve → generate → parse citations
    """

    def __init__(
        self,
        retriever: Retriever,
        synthesis_client: Optional[SynthesisClient] = None,
        state: Optional[DissertationState] = None,
        formatter: Optional[MLAFormatter] = None,
        top_k: int = 10,
        metadata_dir: Optional[Path] = None,
    ):
        self.retriever = retriever
        self.synthesis_client = synthesis_client or SynthesisClient(
            api_key=retriever.embedding_service.api_key,
        )
        self.state = state or DissertationState()
        self.formatter = formatter or MLAFormatter()
        self.top_k = top_k
        self.metadata_dir = metadata_dir or Path("./data/metadata")
        self._metadata_cache: dict[str, dict] = {}

    def _load_document_metadata(self, document_id: str) -> dict:
        """Load metadata from JSON file for a document."""
        if document_id in self._metadata_cache:
            return self._metadata_cache[document_id]
        
        metadata_file = self.metadata_dir / f"{document_id}.json"
        if metadata_file.exists():
            try:
                with open(metadata_file) as f:
                    meta = json.load(f)
                self._metadata_cache[document_id] = meta
                return meta
            except Exception as e:
                logger.warning("Failed to load metadata for %s: %s", document_id, e)
        
        return {}

    def write_chapter(
        self,
        outline: ChapterOutline,
        chapter_context: str = "",
    ) -> dict:
        """Write a complete chapter from an outline.

        Args:
            outline: ChapterOutline with sections defined
            chapter_context: Brief context about the chapter's argument

        Returns:
            Dict with chapter_text, citations, word_count, sections
        """
        self.state.start_chapter(outline.chapter_number, outline.title)

        sections_text = []
        all_citations = []
        previous_summary = self.state.get_previous_summaries(outline.chapter_number)

        for i, section in enumerate(outline.sections):
            logger.info(
                "Writing section %d/%d: %s",
                i + 1,
                len(outline.sections),
                section.title,
            )

            section_text, section_citations = self._write_section(
                section=section,
                chapter_context=chapter_context,
                previous_sections=previous_summary,
            )

            section.generated_text = section_text
            section.citations = section_citations

            self.state.add_section(
                outline.chapter_number,
                section.title,
                section_text,
                section_citations,
            )

            sections_text.append(section_text)
            all_citations.extend(section_citations)

            previous_summary = self.state.get_current_chapter_summary()

        full_chapter = "\n\n".join(sections_text)
        word_count = len(full_chapter.split())

        self.state.finish_chapter(
            outline.chapter_number,
            f"Chapter covering {len(outline.sections)} sections, {word_count} words",
        )

        return {
            "chapter_text": full_chapter,
            "citations": all_citations,
            "word_count": word_count,
            "sections": [s.to_dict() for s in outline.sections],
        }

    def _write_section(
        self,
        section: ChapterSection,
        chapter_context: str = "",
        previous_sections: str = "",
    ) -> tuple[str, list[dict]]:
        """Write a single section with retrieval and generation."""
        query = f"{section.title} {section.description}"
        results = self.retriever.search(query=query, top_k=self.top_k)

        evidence_chunks = []
        citation_map = {}
        for i, r in enumerate(results, 1):
            # Load metadata from JSON file
            doc_meta = self._load_document_metadata(r.document_id)
            
            # Get author from document metadata or chunk metadata
            meta = r.metadata
            author = doc_meta.get("authors", [])
            if isinstance(author, list):
                author = ", ".join(author) if author else ""
            if not author:
                author = meta.get("authors", "")
            if isinstance(author, list):
                author = ", ".join(author) if author else ""
            if not author:
                author = "Unknown"
            
            # Get title from document metadata or chunk metadata
            title = doc_meta.get("title", "") or meta.get("title", "") or r.title or "Untitled"
            
            # Get year from document metadata
            year = doc_meta.get("year") or meta.get("year")
            
            # Filter out birth years (e.g., 1915 is Khushwant Singh's birth year)
            if year and (year < 1920 or year > 2026):
                year = None
            
            chunk_data = {
                "text": r.text,
                "title": title,
                "page": meta.get("page_start", r.page_start),
                "author": author,
                "year": year,
            }
            evidence_chunks.append(chunk_data)
            citation_map[i] = {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "title": title,
                "author": author,
                "year": year,
                "page": meta.get("page_start", r.page_start),
            }

        messages = build_section_prompt(
            section_title=section.title,
            section_description=section.description,
            evidence_chunks=evidence_chunks,
            chapter_context=chapter_context,
            previous_sections=previous_sections,
            target_words=section.target_words,
        )

        raw_text = self.synthesis_client.generate(messages, reasoning_effort="high")

        parsed_citations = self._parse_citations(raw_text, citation_map)

        for cit in parsed_citations:
            self.formatter.add_citation(
                citation_number=cit["number"],
                author=cit.get("author", ""),
                title=cit.get("title", ""),
                year=cit.get("year"),
                page=str(cit.get("page", "")),
            )

        return raw_text, parsed_citations

    def _parse_citations(
        self,
        text: str,
        citation_map: dict[int, dict],
    ) -> list[dict]:
        """Parse [N] or [N, p. X] citation markers and resolve to source details."""
        pattern = re.compile(r"\[(\d+)(?:,\s*p\.\s*\d+)?\]")
        matches = pattern.findall(text)

        seen = set()
        citations = []
        for match in matches:
            num = int(match)
            if num in seen:
                continue
            seen.add(num)
            if num in citation_map:
                cit = citation_map[num].copy()
                cit["number"] = num
                citations.append(cit)

        return citations

    def format_mla(self, text: str) -> str:
        """Convert [N] markers to MLA inline citations."""
        return self.formatter.format_answer(text)

    def get_works_cited(self) -> str:
        """Generate Works Cited page from all citations."""
        return self.formatter.build_works_cited()

    def get_stats(self) -> dict:
        """Get writing statistics."""
        return {
            "chapters_written": len(self.state.chapters),
            "total_word_count": self.state.get_word_count(),
            "total_citations": len(self.state.get_all_citations()),
            "current_chapter": self.state.current_chapter,
        }

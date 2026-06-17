"""Answer generation pipeline for Research RAG."""
from __future__ import annotations


import logging
import re
import time
from typing import Optional, TYPE_CHECKING

from research_rag.cache import QueryCache
from research_rag.citations.parser import CitationParser, Citation
from research_rag.citations.validator import CitationValidator
from research_rag.citations.auditor import CitationAuditor
from research_rag.metrics import Metrics
from research_rag.retrieval import Retriever, SearchResult
from research_rag.synthesis.client import SynthesisClient
from research_rag.synthesis.prompts import build_synthesis_messages

if TYPE_CHECKING:
    from research_rag.citations.formatter import CitationFormatter


logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generates citation-grounded answers from retrieved evidence.

    Pipeline: query → retrieve → build prompt → call LLM → parse citations → validate → return.
    """

    def __init__(
        self,
        retriever: Retriever,
        synthesis_client: Optional[SynthesisClient] = None,
        top_k: int = 5,
        citation_parser: Optional[CitationParser] = None,
        citation_validator: Optional[CitationValidator] = None,
        cache: Optional[QueryCache] = None,
        citation_formatter: Optional['CitationFormatter'] = None,
        auditor: Optional[CitationAuditor] = None,
    ):
        self.retriever = retriever
        self.synthesis_client = synthesis_client or SynthesisClient(
            api_key=retriever.embedding_service.api_key,
        )
        self.top_k = top_k
        self.citation_parser = citation_parser or CitationParser()
        self.citation_validator = citation_validator or CitationValidator()
        self.cache = cache
        self.citation_formatter = citation_formatter
        self.auditor = auditor

    def answer(
        self,
        query: str,
        top_k: Optional[int] = None,
        where: Optional[dict] = None,
        include_reasoning: bool = False,
    ) -> dict:
        """Answer a research question with citation-grounded response.

        Args:
            query: Natural language research question.
            top_k: Number of evidence chunks to retrieve.
            where: Optional metadata filter for retrieval.
            include_reasoning: Include raw reasoning trace in output.

        Returns:
            Dict with keys: query, answer, citations, confidence.
        """
        k = top_k or self.top_k
        metrics = Metrics()
        start = time.monotonic()

        # Check cache first
        if self.cache:
            cached = self.cache.get(query, k)
            if cached:
                metrics.record_cache_hit()
                return cached
            metrics.record_cache_miss()

        # Step 1: Retrieve relevant chunks
        results = self.retriever.search(query=query, top_k=k, where=where)

        if not results:
            return {
                "query": query,
                "answer": "No relevant evidence found in the knowledge base to answer this question.",
                "citations": [],
                "confidence": 0.0,
            }

        # Step 2: Build evidence context
        evidence_texts = [
            (r.text, r.title, r.page_start, r.document_id)
            for r in results
        ]

        # Step 3: Generate answer via LLM
        messages = build_synthesis_messages(query, evidence_texts)

        try:
            raw_answer = self.synthesis_client.generate(messages)
        except Exception as exc:
            logger.error("Synthesis generation failed: %s", exc)
            return {
                "query": query,
                "answer": f"Failed to generate answer due to API error: {exc}",
                "citations": [],
                "confidence": 0.0,
            }

        # Step 4: Parse citations from LLM output
        citations = self.citation_parser.parse(raw_answer, results)

        # Step 5: Validate and enrich citations with metadata
        metadata_map = self._build_metadata_map(results)
        citations = self.citation_validator.validate(citations, metadata_map)

        # Citation audit (hallucination detection)
        audit_report = None
        if self.auditor:
            audit_report = self.auditor.audit(
                raw_answer,
                [c.to_dict() for c in citations],
                results,
            )
        # Optional: Format citations in answer (replaces [N] markers, adds Works Cited)
        if self.citation_formatter:
            formatted = self.citation_formatter.format(
                raw_answer,
                [c.to_dict() for c in citations],
            )
            raw_answer = formatted["answer"]

        # Step 6: Estimate confidence based on citation coverage
        confidence = self._estimate_confidence(citations, results)

        response = {
            "query": query,
            "answer": raw_answer,
            "citations": [c.to_dict() for c in citations],
            "confidence": round(confidence, 2),
        }
        if audit_report:
            response["hallucination_report"] = audit_report

        if include_reasoning:
            response["reasoning_trace"] = {
                "evidence_count": len(results),
                "evidence_scores": [
                    {"chunk_id": r.chunk_id, "score": round(r.score, 3)}
                    for r in results
                ],
            }

        # Cache the result
        if self.cache:
            self.cache.set(query, k, response)

        metrics.record_query(time.monotonic() - start)
        return response

    def _build_metadata_map(self, results: list[SearchResult]) -> dict[str, dict]:
        """Build a metadata map from search results for citation validation.

        Args:
            results: List of SearchResult objects with metadata.

        Returns:
            Dict mapping document_id -> metadata dict with title, authors, year.
        """
        metadata_map: dict[str, dict] = {}
        for r in results:
            if r.document_id and r.document_id not in metadata_map:
                meta = r.metadata
                authors_str = meta.get("authors", "")
                authors = [a.strip() for a in authors_str.split(",") if a.strip()] if authors_str else []
                year = meta.get("year") or None
                if year and isinstance(year, str) and year.isdigit():
                    year = int(year)
                metadata_map[r.document_id] = {
                    "title": meta.get("title", r.title),
                    "authors": authors,
                    "year": year,
                }
        return metadata_map

    def _estimate_confidence(
        self,
        citations: list[Citation],
        results: list[SearchResult],
    ) -> float:
        """Estimate answer confidence based on citation quality.

        Factors:
        - How many unique sources are cited (coverage)
        - Average relevance score of cited chunks
        - Total citation count relative to evidence count
        """
        if not results:
            return 0.0

        cited_ids = {c.chunk_id for c in citations}
        if not cited_ids:
            return 0.3  # No citations = low confidence

        coverage = len(cited_ids) / min(len(results), 5)
        cited_scores = [
            r.score for r in results if r.chunk_id in cited_ids
        ]
        avg_score = sum(cited_scores) / len(cited_scores) if cited_scores else 0.0

        score = 0.3 * coverage + 0.7 * avg_score
        return min(score, 1.0)

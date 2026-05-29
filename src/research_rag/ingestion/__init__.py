"""PDF ingestion pipeline for Research RAG."""

from research_rag.ingestion.parser import ParsedDocument, parse_pdf
from research_rag.ingestion.metadata import extract_metadata
from research_rag.ingestion.chunker import chunk_document
from research_rag.ingestion.pipeline import IngestionPipeline

__all__ = [
    "ParsedDocument",
    "parse_pdf",
    "extract_metadata",
    "chunk_document",
    "IngestionPipeline",
]

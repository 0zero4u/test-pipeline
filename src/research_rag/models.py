"""Data models for Research RAG."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Document metadata extracted from PDF."""

    document_id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Document title")
    authors: list[str] = Field(default_factory=list, description="Author names")
    year: Optional[int] = Field(default=None, description="Publication year")
    journal: str = Field(default="", description="Journal name")
    volume: str = Field(default="", description="Volume number")
    issue: str = Field(default="", description="Issue number")
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier")
    source_file: str = Field(..., description="Original PDF filename")
    metadata_confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence score"
    )
    ingestion_date: datetime = Field(
        default_factory=datetime.utcnow, description="Ingestion timestamp"
    )


class EntityExtraction(BaseModel):
    """Extracted entities from text chunk."""

    people: list[str] = Field(default_factory=list, description="Scholars, authors")
    works: list[str] = Field(default_factory=list, description="Books, articles")
    themes: list[str] = Field(default_factory=list, description="Concepts, themes")
    historical_events: list[str] = Field(
        default_factory=list, description="Historical events"
    )
    references: list[dict[str, Any]] = Field(
        default_factory=list, description="Bibliographic references"
    )


class ChunkFlags(BaseModel):
    """Flags for chunk content."""

    quoted_text: bool = Field(default=False, description="Contains quoted material")
    has_citations: bool = Field(default=False, description="Contains citations")


class Chunk(BaseModel):
    """Document chunk with metadata."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document reference")
    section_title: str = Field(default="", description="Section heading")
    page_start: int = Field(..., ge=1, description="Starting page")
    page_end: int = Field(..., ge=1, description="Ending page")
    text: str = Field(..., description="Chunk text content")
    token_count: int = Field(default=0, description="Approximate token count")
    metadata: Optional[DocumentMetadata] = Field(
        default=None, description="Document metadata"
    )
    entities: Optional[EntityExtraction] = Field(
        default=None, description="Extracted entities"
    )
    flags: ChunkFlags = Field(default_factory=ChunkFlags)


class Citation(BaseModel):
    """Citation reference in answer."""

    chunk_id: str
    document_id: str
    title: str
    page: int
    relevance_score: float = Field(ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    """Response to a research query."""

    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Synthesized answer")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score")
    reasoning_trace: Optional[str] = Field(
        default=None, description="Reasoning trace"
    )


class IngestionResult(BaseModel):
    """Result of document ingestion."""

    document_id: str
    title: str
    chunks_created: int
    metadata_confidence: float
    success: bool
    error: Optional[str] = None

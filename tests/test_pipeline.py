"""Tests for the ingestion pipeline module."""

from pathlib import Path

from research_rag.ingestion.pipeline import IngestionPipeline
from research_rag.models import IngestionResult


def test_pipeline_no_pdfs(tmp_path):
    """Test pipeline with empty directory."""
    pipeline = IngestionPipeline(output_dir=tmp_path)
    results = pipeline.process_directory(tmp_path, pattern="*.pdf")
    assert results == []


def test_pipeline_initialization():
    """Test pipeline initialization with defaults."""
    pipeline = IngestionPipeline()
    assert pipeline.config is not None
    assert pipeline.config.chunk_size_min == 500
    assert pipeline.config.chunk_size_max == 900


def test_pipeline_custom_config():
    """Test pipeline with custom config."""
    from research_rag.config import IngestionConfig

    config = IngestionConfig(chunk_size_min=300, chunk_size_max=600)
    pipeline = IngestionPipeline(config=config)
    assert pipeline.config.chunk_size_min == 300


def test_pipeline_output_dir():
    """Test pipeline output directory creation."""
    pipeline = IngestionPipeline(output_dir=Path("/tmp/test_pipeline_output"))
    assert pipeline.output_dir == Path("/tmp/test_pipeline_output")


def test_pipeline_invalid_pdf(tmp_path):
    """Test pipeline handling of invalid/non-PDF files."""
    # Create an empty file that looks like a PDF
    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_text("this is not a real pdf")

    pipeline = IngestionPipeline(output_dir=tmp_path / "output")
    results = pipeline.process_pdfs([fake_pdf])
    assert len(results) == 1
    assert results[0].success is False
    assert results[0].error is not None


def test_ingestion_result_model():
    """Test IngestionResult model."""
    result = IngestionResult(
        document_id="test_001",
        title="Test Document",
        chunks_created=5,
        metadata_confidence=0.85,
        success=True,
    )
    assert result.document_id == "test_001"
    assert result.chunks_created == 5
    assert result.success is True
    assert result.error is None

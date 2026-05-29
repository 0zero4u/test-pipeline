"""Orchestration pipeline for PDF ingestion."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from research_rag.config import IngestionConfig, Settings, load_settings
from research_rag.ingestion.chunker import chunk_document
from research_rag.ingestion.metadata import extract_metadata
from research_rag.ingestion.parser import ParsedDocument, parse_pdf
from research_rag.logging import get_logger
from research_rag.models import Chunk, DocumentMetadata, IngestionResult

logger = get_logger("ingestion.pipeline")

DEFAULT_MAX_WORKERS = 4


class IngestionPipeline:
    """Orchestrates the PDF ingestion pipeline: parse → metadata → chunk."""

    def __init__(
        self,
        config: Optional[IngestionConfig] = None,
        output_dir: Optional[Path] = None,
        max_workers: int = DEFAULT_MAX_WORKERS,
    ) -> None:
        self.config = config or IngestionConfig()
        self.output_dir = output_dir or Path("./data")
        self.max_workers = max_workers

    def _save_chunks(
        self, chunks: list[Chunk], metadata: DocumentMetadata
    ) -> None:
        """Save chunks to JSON file."""
        chunks_dir = self.output_dir / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        chunk_file = chunks_dir / f"{metadata.document_id}_chunks.json"

        chunk_data = []
        for chunk in chunks:
            chunk_data.append(chunk.model_dump(mode="json"))

        with open(chunk_file, "w", encoding="utf-8") as f:
            json.dump(chunk_data, f, indent=2, default=str)

        logger.debug("Saved %d chunks to %s", len(chunks), chunk_file)

    def _save_metadata(self, metadata: DocumentMetadata) -> None:
        """Save document metadata to JSON file."""
        meta_dir = self.output_dir / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_file = meta_dir / f"{metadata.document_id}.json"

        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        logger.debug("Saved metadata to %s", meta_file)

    def process_pdfs(
        self, pdf_files: list[Path], show_progress: bool = True
    ) -> list[IngestionResult]:
        """Process a list of PDF files through the ingestion pipeline.

        Each PDF goes through: parse → extract_metadata → chunk.
        Results are saved to the output directory.

        Args:
            pdf_files: List of paths to PDF files to ingest.
            show_progress: Whether to show a progress bar.

        Returns:
            List of IngestionResult for each PDF.
        """
        if not pdf_files:
            return []

        if len(pdf_files) == 1:
            try:
                return [self._process_single_pdf(pdf_files[0])]
            except Exception as exc:
                logger.error("Failed to process %s: %s", pdf_files[0].name, exc)
                return [
                    IngestionResult(
                        document_id=pdf_files[0].stem,
                        title=pdf_files[0].stem,
                        chunks_created=0,
                        metadata_confidence=0.0,
                        success=False,
                        error=str(exc),
                    )
                ]

        results: list[IngestionResult] = [None] * len(pdf_files)  # type: ignore

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self._process_single_pdf, fp): i
                for i, fp in enumerate(pdf_files)
            }

            with tqdm(total=len(pdf_files), desc="Ingesting PDFs", unit="pdf") as pbar:
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        results[idx] = future.result()
                    except Exception as exc:
                        logger.error("Failed to process %s: %s", pdf_files[idx].name, exc)
                        results[idx] = IngestionResult(
                            document_id=pdf_files[idx].stem,
                            title=pdf_files[idx].stem,
                            chunks_created=0,
                            metadata_confidence=0.0,
                            success=False,
                            error=str(exc),
                        )
                    pbar.update(1)

        successful = sum(1 for r in results if r and r.success)
        total_chunks = sum(r.chunks_created for r in results if r)
        logger.info(
            "Ingestion complete: %d/%d PDFs processed, %d chunks created",
            successful,
            len(pdf_files),
            total_chunks,
        )

        return results  # type: ignore

    def _process_single_pdf(self, file_path: Path) -> IngestionResult:
        """Process a single PDF file."""
        logger.info("Processing: %s", file_path.name)

        # Step 1: Parse PDF
        parsed: ParsedDocument = parse_pdf(file_path)

        # Step 2: Extract metadata from first page
        metadata: DocumentMetadata = extract_metadata(
            parsed.first_page_text, file_path.name
        )

        # Step 3: Chunk the document
        chunks: list[Chunk] = chunk_document(
            parsed.markdown,
            parsed.sections,
            metadata,
            self.config,
        )

        # Step 4: Save results
        self._save_metadata(metadata)
        self._save_chunks(chunks, metadata)

        logger.info(
            "Processed %s: %d chunks (confidence: %.2f)",
            file_path.name,
            len(chunks),
            metadata.metadata_confidence,
        )

        return IngestionResult(
            document_id=metadata.document_id,
            title=metadata.title,
            chunks_created=len(chunks),
            metadata_confidence=metadata.metadata_confidence,
            success=True,
        )

    def process_directory(
        self, input_dir: Path, pattern: str = "*.pdf"
    ) -> list[IngestionResult]:
        """Process all PDFs in a directory.

        Args:
            input_dir: Directory containing PDF files.
            pattern: Glob pattern for PDF files (default: *.pdf).

        Returns:
            List of IngestionResult for each PDF.
        """
        pdf_files = sorted(input_dir.glob(pattern))
        if not pdf_files:
            logger.warning("No PDF files found in %s", input_dir)
            return []

        logger.info("Found %d PDF files in %s", len(pdf_files), input_dir)
        return self.process_pdfs(pdf_files)

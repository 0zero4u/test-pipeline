"""Performance benchmarks for Research RAG."""

import json
import time
from pathlib import Path
from typing import Optional

from research_rag.metrics import Metrics


def benchmark_ingestion(
    pdf_dir: Path,
    output_dir: Path = Path("./data/benchmark"),
    max_workers: int = 4,
    runs: int = 3,
) -> dict:
    """Benchmark PDF ingestion speed.

    Args:
        pdf_dir: Directory with PDF files to ingest.
        output_dir: Output directory for benchmark results.
        max_workers: Number of parallel workers.
        runs: Number of benchmark runs.

    Returns:
        Dict with timing results.
    """
    from research_rag.ingestion.pipeline import IngestionPipeline

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        return {"error": "No PDF files found"}

    times = []
    chunks_created = []

    for run in range(runs):
        pipeline = IngestionPipeline(
            output_dir=output_dir / f"run_{run}",
            max_workers=max_workers,
        )
        start = time.monotonic()
        results = pipeline.process_pdfs(pdf_files, show_progress=False)
        elapsed = time.monotonic() - start
        times.append(elapsed)
        chunks_created.append(sum(r.chunks_created for r in results))

    return {
        "pdf_count": len(pdf_files),
        "runs": runs,
        "avg_time_s": round(sum(times) / len(times), 2),
        "min_time_s": round(min(times), 2),
        "max_time_s": round(max(times), 2),
        "avg_chunks": round(sum(chunks_created) / len(chunks_created), 1),
        "max_workers": max_workers,
    }


def benchmark_queries(
    queries: list[str],
    top_k: int = 5,
    runs: int = 3,
) -> dict:
    """Benchmark query latency.

    Args:
        queries: List of test queries.
        top_k: Number of results per query.
        runs: Number of benchmark runs.

    Returns:
        Dict with timing results per query.
    """
    from research_rag.retrieval import Retriever

    retriever = Retriever()
    results_per_query = {}

    for query in queries:
        times = []
        for _ in range(runs):
            start = time.monotonic()
            retriever.search(query=query, top_k=top_k)
            elapsed = time.monotonic() - start
            times.append(elapsed)

        results_per_query[query[:50]] = {
            "avg_ms": round(sum(times) / len(times) * 1000, 1),
            "min_ms": round(min(times) * 1000, 1),
            "max_ms": round(max(times) * 1000, 1),
        }

    return {"query_count": len(queries), "runs": runs, "results": results_per_query}


def save_benchmark(results: dict, output_path: Path) -> None:
    """Save benchmark results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

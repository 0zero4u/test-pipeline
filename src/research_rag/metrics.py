"""Performance metrics for Research RAG."""

import time
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class Metrics:
    """Tracks query latency, ingestion stats, and cache performance.

    Singleton instance shared across components.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.query_latencies: list[float] = []
        self.ingestion_counts: dict[str, int] = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0
        self.api_errors = 0

    def record_query(self, latency: float) -> None:
        self.query_latencies.append(latency)

    def record_ingestion(self, document_id: str, chunks: int) -> None:
        self.ingestion_counts[document_id] = chunks

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1

    def record_api_call(self, success: bool = True) -> None:
        self.api_calls += 1
        if not success:
            self.api_errors += 1

    def summary(self) -> dict[str, Any]:
        latencies = self.query_latencies
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 2 else avg_latency

        total_cache = self.cache_hits + self.cache_misses
        return {
            "queries": len(latencies),
            "avg_latency_ms": round(avg_latency * 1000, 1),
            "p95_latency_ms": round(p95 * 1000, 1),
            "documents_ingested": len(self.ingestion_counts),
            "total_chunks": sum(self.ingestion_counts.values()),
            "cache_hit_rate": round(self.cache_hits / total_cache, 3) if total_cache > 0 else 0.0,
            "api_calls": self.api_calls,
            "api_errors": self.api_errors,
        }

    def reset(self) -> None:
        self.query_latencies.clear()
        self.ingestion_counts.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = 0
        self.api_errors = 0

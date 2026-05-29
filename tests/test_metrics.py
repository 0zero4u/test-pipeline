"""Tests for metrics module."""

from research_rag.metrics import Metrics


class TestMetrics:
    """Test singleton metrics tracker."""

    def setup_method(self):
        Metrics._instance = None
        self.metrics = Metrics()

    def test_singleton(self):
        m1 = Metrics()
        m2 = Metrics()
        assert m1 is m2

    def test_record_query(self):
        self.metrics.record_query(0.5)
        assert len(self.metrics.query_latencies) == 1

    def test_record_ingestion(self):
        self.metrics.record_ingestion("doc1", 10)
        assert self.metrics.ingestion_counts["doc1"] == 10

    def test_record_cache_hit_miss(self):
        self.metrics.record_cache_hit()
        self.metrics.record_cache_miss()
        assert self.metrics.cache_hits == 1
        assert self.metrics.cache_misses == 1

    def test_record_api_call(self):
        self.metrics.record_api_call(success=True)
        self.metrics.record_api_call(success=False)
        assert self.metrics.api_calls == 2
        assert self.metrics.api_errors == 1

    def test_summary(self):
        self.metrics.record_query(0.1)
        self.metrics.record_query(0.2)
        self.metrics.record_ingestion("doc1", 5)
        self.metrics.record_cache_hit()
        self.metrics.record_cache_miss()
        s = self.metrics.summary()
        assert s["queries"] == 2
        assert s["avg_latency_ms"] == 150.0
        assert s["documents_ingested"] == 1
        assert s["total_chunks"] == 5
        assert s["cache_hit_rate"] == 0.5

    def test_reset(self):
        self.metrics.record_query(0.1)
        self.metrics.record_api_call()
        self.metrics.reset()
        s = self.metrics.summary()
        assert s["queries"] == 0
        assert s["api_calls"] == 0

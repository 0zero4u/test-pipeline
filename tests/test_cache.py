"""Tests for query caching."""

from research_rag.cache import QueryCache


class TestQueryCache:
    """Test LRU cache for query results."""

    def setup_method(self):
        self.cache = QueryCache(max_size=3)

    def test_get_miss(self):
        result = self.cache.get("what is partition", top_k=5)
        assert result is None

    def test_set_and_get(self):
        self.cache.set("what is partition", 5, {"answer": "test"})
        result = self.cache.get("what is partition", top_k=5)
        assert result == {"answer": "test"}

    def test_lru_eviction(self):
        for i in range(4):
            self.cache.set(f"query {i}", 5, {"answer": f"ans {i}"})
        assert self.cache.get("query 0", top_k=5) is None
        assert self.cache.get("query 1", top_k=5) is not None

    def test_stats(self):
        self.cache.get("q1", 5)
        self.cache.set("q2", 5, {})
        self.cache.get("q2", 5)
        stats = self.cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_clear(self):
        self.cache.set("q", 5, {})
        self.cache.clear()
        assert self.cache.get("q", 5) is None

    def test_different_top_k_different_key(self):
        self.cache.set("query", 5, {"answer": "a"})
        self.cache.set("query", 10, {"answer": "b"})
        assert self.cache.get("query", 5)["answer"] == "a"
        assert self.cache.get("query", 10)["answer"] == "b"

    def test_query_normalization(self):
        self.cache.set("  What is Partition  ", 5, {"answer": "x"})
        result = self.cache.get("what is partition", top_k=5)
        assert result == {"answer": "x"}

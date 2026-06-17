"""Query result caching for Research RAG."""

import hashlib
import logging
import tempfile
from typing import Optional

import diskcache

logger = logging.getLogger(__name__)

class QueryCache:
    """LRU cache for query results with disk persistence via diskcache."""

    def __init__(
        self,
        max_size: int = 100,
        persist_path: Optional[str] = None,
    ):
        self.max_size = max_size
        directory = persist_path if persist_path else tempfile.mkdtemp(prefix="research_rag_cache_")
        self._cache = diskcache.Cache(
            directory=directory,
            size_limit=100 * 1024 * 1024,
            eviction_policy="least-recently-used",
        )
        # No clear() — default mode uses tempdir for test isolation,
        # persist_path mode provides true disk persistence.
        self._hits = 0
        self._misses = 0

    def get(self, query: str, top_k: int = 5) -> Optional[dict]:
        """Get cached result for a query.

        Args:
            query: The research query.
            top_k: Number of results requested.

        Returns:
            Cached result dict or None if not found.
        """
        key = self._make_key(query, top_k)
        result = self._cache.get(key)
        if result is not None:
            self._hits += 1
            logger.debug("Cache hit for query: %s", query[:50])
            return result
        self._misses += 1
        return None

    def set(self, query: str, top_k: int, result: dict) -> None:
        """Cache a query result.

        Args:
            query: The research query.
            top_k: Number of results requested.
            result: The result dict to cache.
        """
        key = self._make_key(query, top_k)
        self._cache.set(key, result, expire=3600)

        # Enforce count-based LRU when capacity is exceeded. diskcache's
        # built-in cull is byte-based, so handle count-based eviction here.
        if len(self._cache) > self.max_size:
            to_remove = len(self._cache) - self.max_size
            # diskcache iterates in insertion order; remove oldest entries
            for old_key in list(self._cache)[:to_remove]:
                del self._cache[old_key]

        logger.debug("Cached result for query: %s", query[:50])

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(query: str, top_k: int) -> str:
        """Create a cache key from query and top_k."""
        raw = f"{query.lower().strip()}:{top_k}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

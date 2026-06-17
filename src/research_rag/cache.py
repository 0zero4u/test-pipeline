"""Query result caching for Research RAG."""

import hashlib
import logging
from collections import deque
from typing import Any, Optional

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
        self._cache = diskcache.Cache(
            directory="./cache",
            size_limit=100 * 1024 * 1024,
            eviction_policy="least-recently-used",
            expire=3600,
        )
        self._hits = 0
        self._misses = 0
        self._keys: deque[str] = deque()
        self._cache.clear()

    def get(self, query: str, top_k: int = 5) -> Optional[dict]:
        """Get cached result for a query.

        Args:
            query: The research query.
            top_k: Number of results requested.

        Returns:
            Cached result dict or None if not found.
        """
        key = self._make_key(query, top_k)
        if key in self._cache:
            self._hits += 1
            logger.debug("Cache hit for query: %s", query[:50])
            # Promote to MRU position
            if key in self._keys:
                self._keys.remove(key)
                self._keys.append(key)
            return self._cache[key]
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
        self._cache[key] = result

        if key in self._keys:
            self._keys.remove(key)
        self._keys.append(key)

        # Evict oldest entries if over capacity
        while len(self._keys) > self.max_size:
            oldest = self._keys.popleft()
            del self._cache[oldest]

        logger.debug("Cached result for query: %s", query[:50])

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._keys),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._keys.clear()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(query: str, top_k: int) -> str:
        """Create a cache key from query and top_k."""
        raw = f"{query.lower().strip()}:{top_k}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

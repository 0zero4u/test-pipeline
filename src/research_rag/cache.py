"""Query result caching for Research RAG."""

import hashlib
import json
import logging
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class QueryCache:
    """LRU cache for query results with optional disk persistence.

    Caches query → result mappings to avoid redundant LLM calls.
    """

    def __init__(
        self,
        max_size: int = 100,
        persist_path: Optional[Path] = None,
    ):
        self.max_size = max_size
        self.persist_path = persist_path
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._hits = 0
        self._misses = 0

        if persist_path and persist_path.exists():
            self._load()

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
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug("Cache hit for query: %s", query[:50])
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
        self._cache.move_to_end(key)

        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

        if self.persist_path:
            self._save()

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

    def _make_key(self, query: str, top_k: int) -> str:
        """Create a cache key from query and top_k."""
        raw = f"{query.lower().strip()}:{top_k}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _save(self) -> None:
        """Persist cache to disk."""
        if not self.persist_path:
            return
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, "w") as f:
                json.dump(dict(self._cache), f, indent=2, default=str)
        except Exception as exc:
            logger.warning("Failed to save cache: %s", exc)

    def _load(self) -> None:
        """Load cache from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            with open(self.persist_path) as f:
                data = json.load(f)
            self._cache = OrderedDict(data)
            logger.info("Loaded %d cached queries from %s", len(self._cache), self.persist_path)
        except Exception as exc:
            logger.warning("Failed to load cache: %s", exc)

"""Embedding service with OpenRouter API and local fallback."""

import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "thenlper/gte-large"
LOCAL_MODEL = "BAAI/bge-small-en-v1.5"


class EmbeddingService:
    """Generates text embeddings via OpenRouter API, with local fallback.

    Uses OpenAI-compatible OpenRouter endpoint for embedding models.
    Falls back to sentence-transformers locally if no API key is available.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        batch_size: int = 32,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.batch_size = batch_size
        self._local_ef = None
        self._using_local = False

        if self.api_key:
            logger.info(
                "Embedding service using OpenRouter model: %s", self.model
            )
        else:
            logger.warning(
                "No OPENROUTER_API_KEY set. Falling back to local model: %s",
                LOCAL_MODEL,
            )
            self.model = LOCAL_MODEL
            self._using_local = True

    def _get_local_ef(self):
        """Lazy-load sentence-transformers embedding function."""
        if self._local_ef is None:
            logger.info("Loading local embedding model: %s", LOCAL_MODEL)
            from chromadb.utils.embedding_functions import (
                SentenceTransformerEmbeddingFunction,
            )

            self._local_ef = SentenceTransformerEmbeddingFunction(
                model_name=LOCAL_MODEL
            )
            logger.info("Local model loaded (dim=%d)", self.dimension)
        return self._local_ef

    @property
    def dimension(self) -> int:
        """Return embedding dimension for the current model."""
        if self._using_local:
            ef = self._get_local_ef()
            return len(ef([""])[0])
        # GTE-Large produces 1024-dim embeddings
        return 1024

    def embed(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            numpy array of shape (len(texts), dimension).
        """
        if not texts:
            return np.empty((0, self.dimension))

        if self._using_local:
            return self._embed_local(texts)

        return self._embed_api(texts)

    def _embed_local(self, texts: list[str]) -> np.ndarray:
        """Embed using local sentence-transformers."""
        ef = self._get_local_ef()
        embeddings = ef(texts)
        return np.array(embeddings, dtype=np.float32)

    def _embed_api(self, texts: list[str]) -> np.ndarray:
        """Embed using OpenRouter API (OpenAI-compatible)."""
        from openai import OpenAI

        client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=self.api_key,
        )

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            try:
                response = client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
                # Sort by index to maintain order
                sorted_data = sorted(response.data, key=lambda x: x.index)
                batch_embeddings = [item.embedding for item in sorted_data]
                all_embeddings.extend(batch_embeddings)
                logger.debug(
                    "Embedded batch %d-%d (%d texts)",
                    i,
                    i + len(batch),
                    len(batch),
                )
            except Exception as exc:
                logger.error("Embedding API call failed at batch %d: %s", i, exc)
                raise

        return np.array(all_embeddings, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query string.

        For BGE models, we apply the instruction prefix for asymmetric retrieval.
        For GTE-Large via API, no prefix needed.
        """
        if self._using_local:
            # BGE models benefit from a query instruction prefix
            prefixed = f"Represent this sentence for searching relevant passages: {text}"
            return self.embed([prefixed])[0]
        return self.embed([text])[0]

    def __repr__(self) -> str:
        return (
            f"EmbeddingService(model={self.model}, "
            f"dim={self.dimension}, local={self._using_local})"
        )

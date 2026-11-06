"""
Local embedding service using sentence-transformers (no paid API).
Implements batched encoding with caching to minimize redundant computation.
"""
from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Lazy import to avoid startup delays when embedding is not used
_model = None
_model_name: Optional[str] = None


def _get_model():
    """Return the sentence-transformers model (lazy load)."""
    global _model, _model_name
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
            _model = SentenceTransformer(settings.EMBEDDING_MODEL)
            _model_name = settings.EMBEDDING_MODEL
            logger.info("Embedding model loaded.")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            )
    return _model


# In-memory cache: text_hash → embedding (list of floats)
_embedding_cache: Dict[str, List[float]] = {}


def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


class EmbeddingService:
    """
    Wraps sentence-transformers for local text embedding.
    Maintains an in-memory cache to avoid re-encoding identical texts.
    """

    def __init__(self) -> None:
        self._batch_size = settings.EMBEDDING_BATCH_SIZE

    def embed(self, text: str) -> List[float]:
        """Return the embedding for a single text string."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Encode a list of texts, using cache for already-encoded strings.
        Returns embeddings in the same order as inputs.
        """
        model = _get_model()
        results: List[Optional[List[float]]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for i, text in enumerate(texts):
            key = _cache_key(text)
            if key in _embedding_cache:
                results[i] = _embedding_cache[key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            logger.debug("Encoding %d texts (batch size %d)...", len(uncached_texts), self._batch_size)
            embeddings = model.encode(
                uncached_texts,
                batch_size=self._batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            for idx, (orig_idx, text) in enumerate(zip(uncached_indices, uncached_texts)):
                emb = embeddings[idx].tolist()
                _embedding_cache[_cache_key(text)] = emb
                results[orig_idx] = emb

        return [r for r in results if r is not None]

    def get_model_name(self) -> str:
        return _model_name or settings.EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return the application-wide EmbeddingService singleton."""
    return EmbeddingService()

"""
Retrieval service: ChromaDB vector store with metadata filtering,
similarity thresholds, and deduplication.
"""
from __future__ import annotations

import asyncio
import uuid
from functools import lru_cache
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.ingestion.chunker import TextChunker
from app.services.embedding_service import get_embedding_service

logger = get_logger(__name__)

_chroma_client = None
_collection = None


def _get_chroma_collection():
    """Return ChromaDB collection (lazy init, persistent local storage)."""
    global _chroma_client, _collection
    if _collection is None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            logger.info("Initializing ChromaDB at: %s", settings.CHROMA_PERSIST_DIR)
            _chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
            )
            _collection = _chroma_client.get_or_create_collection(
                name=settings.CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "ChromaDB collection '%s' ready. Documents: %d",
                settings.CHROMA_COLLECTION_NAME,
                _collection.count(),
            )
        except ImportError:
            raise RuntimeError("chromadb is not installed. Run: pip install chromadb")
    return _collection


class RetrievalService:
    """
    Manages storage and retrieval of document chunks in ChromaDB.
    All operations are account-scoped via metadata filtering.
    """

    def __init__(self) -> None:
        self._chunker = TextChunker(
            chunk_size=settings.RAG_MAX_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        )
        self._embedder = get_embedding_service()
        self._top_k = settings.RAG_TOP_K
        self._threshold = settings.RAG_SIMILARITY_THRESHOLD

    async def store_document(
        self,
        account_id: str,
        document_id: str,
        text: str,
        metadata: Dict[str, Any],
    ) -> int:
        """
        Chunk text, embed chunks, and store in ChromaDB.
        Returns the number of chunks stored.
        """
        chunks = self._chunker.chunk(text, metadata={**metadata, "document_id": document_id})
        if not chunks:
            return 0

        collection = _get_chroma_collection()

        # Build lists for batch upsert
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        texts_to_embed = [c["text"] for c in chunks]
        embeddings_list = await asyncio.get_event_loop().run_in_executor(
            None, self._embedder.embed_batch, texts_to_embed
        )

        for chunk, embedding in zip(chunks, embeddings_list):
            chunk_id = f"{document_id}_{chunk['chunk_index']}"
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk["text"])
            metadatas.append({
                "account_id": account_id,
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "source_url": metadata.get("source_url", ""),
                "source_title": metadata.get("source_title", ""),
                "source_type": metadata.get("source_type", ""),
            })

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            ),
        )

        logger.info(
            "Stored %d chunks for document %s (account: %s)",
            len(chunks), document_id, account_id,
        )
        return len(chunks)

    async def retrieve(
        self,
        query: str,
        account_id: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-K most relevant chunks for a query, filtered by account.

        Returns list of dicts with keys: text, score, source_url, source_title,
        document_id, chunk_index.
        """
        k = top_k or self._top_k
        min_score = threshold if threshold is not None else self._threshold

        collection = _get_chroma_collection()

        if collection.count() == 0:
            logger.debug("ChromaDB collection is empty.")
            return []

        # Embed query
        query_embedding = await asyncio.get_event_loop().run_in_executor(
            None, self._embedder.embed, query
        )

        # Query with account filter
        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(k * 2, max(collection.count(), 1)),  # Over-fetch for filtering
                    where={"account_id": account_id},
                    include=["documents", "metadatas", "distances"],
                ),
            )
        except Exception as exc:
            logger.error("ChromaDB query error: %s", exc)
            return []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        retrieved = []
        seen_texts: set = set()

        for doc, meta, dist in zip(documents, metadatas, distances):
            # ChromaDB cosine distance: 0=identical, 2=opposite
            # Convert to similarity: 1 - distance/2 → [0,1]
            # Threshold is applied on similarity scale
            similarity = 1.0 - (dist / 2.0)

            if similarity < min_score:
                continue

            # Deduplicate by text
            text_key = doc[:100]
            if text_key in seen_texts:
                continue
            seen_texts.add(text_key)

            retrieved.append({
                "text": doc,
                "score": round(similarity, 4),
                "source_url": meta.get("source_url", ""),
                "source_title": meta.get("source_title", ""),
                "document_id": meta.get("document_id", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "source_type": meta.get("source_type", ""),
            })

        # Sort by score descending, return top_k
        retrieved.sort(key=lambda x: x["score"], reverse=True)
        return retrieved[:k]

    async def get_account_document_count(self, account_id: str) -> int:
        """Return the number of chunks stored for an account."""
        collection = _get_chroma_collection()
        try:
            result = collection.get(where={"account_id": account_id})
            return len(result.get("ids", []))
        except Exception:
            return 0

    async def delete_account_documents(self, account_id: str) -> int:
        """Delete all chunks for an account. Returns count deleted."""
        collection = _get_chroma_collection()
        try:
            result = collection.get(where={"account_id": account_id})
            ids = result.get("ids", [])
            if ids:
                collection.delete(ids=ids)
            return len(ids)
        except Exception as exc:
            logger.error("Failed to delete account documents: %s", exc)
            return 0


@lru_cache(maxsize=1)
def get_retrieval_service() -> RetrievalService:
    """Return the application-wide RetrievalService singleton."""
    return RetrievalService()

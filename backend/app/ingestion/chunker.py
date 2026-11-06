"""
Document chunker: splits extracted text into overlapping chunks
with metadata for RAG indexing.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


class TextChunker:
    """
    Split text into fixed-size overlapping chunks with metadata preservation.
    Uses sentence-aware splitting to avoid cutting mid-sentence where possible.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Split text into chunks. Each chunk carries the base metadata plus
        a chunk index and character offsets.

        Returns list of dicts: {text, metadata, chunk_index, char_start, char_end}.
        """
        if not text or not text.strip():
            return []

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Split into sentences for cleaner boundaries
        sentences = self._split_sentences(text)
        chunks: List[Dict[str, Any]] = []
        current = ""
        char_pos = 0
        chunk_idx = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If adding this sentence would exceed chunk_size, finalize current chunk
            if current and len(current) + len(sentence) + 1 > self.chunk_size:
                chunk_text = current.strip()
                if len(chunk_text) > 20:  # Skip trivially short chunks
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {**metadata, "chunk_index": chunk_idx},
                        "chunk_index": chunk_idx,
                        "char_start": char_pos - len(chunk_text),
                        "char_end": char_pos,
                    })
                    chunk_idx += 1

                # Overlap: retain last `chunk_overlap` characters
                if self.chunk_overlap > 0 and len(current) > self.chunk_overlap:
                    current = current[-self.chunk_overlap:] + " " + sentence
                else:
                    current = sentence
            else:
                current = (current + " " + sentence).strip() if current else sentence

            char_pos += len(sentence) + 1

        # Final chunk
        if current.strip() and len(current.strip()) > 20:
            chunks.append({
                "text": current.strip(),
                "metadata": {**metadata, "chunk_index": chunk_idx},
                "chunk_index": chunk_idx,
                "char_start": char_pos - len(current),
                "char_end": char_pos,
            })

        return chunks

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences using simple regex heuristics."""
        # Split on sentence-ending punctuation followed by space and capital letter
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"])", text)
        return [p.strip() for p in parts if p.strip()]

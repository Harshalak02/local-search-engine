# extractor/base_extractor.py
# ─────────────────────────────────────────────────────────────
# Responsibility : define the interface every extractor must follow.
# Member A owns this file.
# ─────────────────────────────────────────────────────────────

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from abc import ABC, abstractmethod
from shared_types import ExtractedDocument


class BaseExtractor(ABC):
    """
    All file-type extractors inherit from this class.
    This guarantees that extractor/__init__.py can call
    any extractor the same way, regardless of file type.
    """

    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """Return True if this extractor handles the given file type."""
        pass

    @abstractmethod
    def extract(self, file_path: str) -> ExtractedDocument:
        """
        Extract text and metadata from the file.

        Args:
            file_path : absolute path to the file.

        Returns:
            ExtractedDocument with raw_text, chunks, and metadata filled in.
        """
        pass

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list:
        """
        Split text into overlapping word-based chunks.

        chunk_size : number of words per chunk
        overlap    : number of words shared between consecutive chunks
                     (keeps context at boundaries)

        Example with chunk_size=5, overlap=2:
            words = [a, b, c, d, e, f, g]
            chunk 1 → [a, b, c, d, e]
            chunk 2 → [d, e, f, g]     ← d,e repeated for context
        """
        words = text.split()
        if not words:
            return []

        chunks = []
        start = 0

        while start < len(words):
            end = start + chunk_size
            chunk = " ".join(words[start:end])
            chunks.append(chunk)
            start += chunk_size - overlap

        return chunks

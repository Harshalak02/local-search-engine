# indexer/inverted_index.py
# ─────────────────────────────────────────────────────────────
# Responsibility : build and query an inverted index with BM25 ranking.
#
# What is an inverted index?
#   Normal:   document → list of words
#   Inverted: word     → list of documents that contain it
#
# What is BM25?
#   A ranking formula. Given a query word, it scores each document
#   based on how often the word appears (term frequency) and how
#   rare the word is across all documents (inverse document frequency).
#   More common in a doc + rarer across all docs = higher score.
# ─────────────────────────────────────────────────────────────

import math
import re
import sys
import os
from collections import defaultdict
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_types import ExtractedDocument


def tokenize(text: str) -> List[str]:
    """
    Convert text into a list of lowercase tokens.
    Strips punctuation, splits on whitespace.

    Example:
        "Hello, World!" → ["hello", "world"]
    """
    text = text.lower()
    tokens = re.findall(r'\b[a-z0-9]+\b', text)
    return tokens


class InvertedIndex:
    """
    Stores an inverted index and supports BM25-ranked keyword search.

    Internal data structures:
        index       : { token → { doc_id → term_frequency } }
        documents   : { doc_id → ExtractedDocument }
        doc_lengths : { doc_id → total token count in that doc }
    """

    # BM25 tuning parameters (standard defaults, don't change unless you know why)
    K1 = 1.5   # controls term frequency saturation
    B  = 0.75  # controls document length normalization

    def __init__(self):
        # token → { doc_id → how many times token appears in doc }
        self.index: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # doc_id → the full ExtractedDocument
        self.documents: Dict[str, ExtractedDocument] = {}

        # doc_id → total number of tokens in that document
        self.doc_lengths: Dict[str, int] = {}

        # running total of all token counts (used to compute average doc length)
        self._total_tokens: int = 0

    # ── indexing ─────────────────────────────────────────────

    def add_document(self, doc: ExtractedDocument) -> None:
        """
        Index one ExtractedDocument.
        Uses the file_path as the unique document ID.
        Indexes all chunks together as one document.
        """
        doc_id = doc.file_path

        # join all chunks into one text for indexing
        full_text = " ".join(doc.chunks)
        tokens    = tokenize(full_text)

        if not tokens:
            return

        # store the document
        self.documents[doc_id]   = doc
        self.doc_lengths[doc_id] = len(tokens)
        self._total_tokens      += len(tokens)

        # build term frequency map for this document
        for token in tokens:
            self.index[token][doc_id] += 1

    def remove_document(self, file_path: str) -> None:
        """Remove a document from the index (used when file is deleted)."""
        doc_id = file_path
        if doc_id not in self.documents:
            return

        # clean up doc_lengths and total
        self._total_tokens -= self.doc_lengths.pop(doc_id, 0)

        # remove from inverted index
        for token_postings in self.index.values():
            token_postings.pop(doc_id, None)

        del self.documents[doc_id]

    # ── searching ────────────────────────────────────────────

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float, ExtractedDocument]]:
        """
        Search the index using BM25 ranking.

        Args:
            query : raw query string, e.g. "machine learning python"
            top_k : number of results to return

        Returns:
            List of (file_path, bm25_score, ExtractedDocument) tuples,
            sorted by score descending.
        """
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores: Dict[str, float] = defaultdict(float)
        N      = len(self.documents)           # total number of documents
        avgdl  = self._avg_doc_length()

        for token in query_tokens:
            if token not in self.index:
                continue

            postings = self.index[token]       # { doc_id → tf }
            df       = len(postings)           # how many docs contain this token

            # IDF: penalises tokens that appear in many documents
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1)

            for doc_id, tf in postings.items():
                dl     = self.doc_lengths[doc_id]
                # BM25 term score
                tf_norm = (tf * (self.K1 + 1)) / (
                    tf + self.K1 * (1 - self.B + self.B * dl / avgdl)
                )
                scores[doc_id] += idf * tf_norm

        # sort by score, return top_k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(doc_id, score, self.documents[doc_id]) for doc_id, score in ranked]

    def get_snippet(self, doc: ExtractedDocument, query: str, snippet_len: int = 200) -> str:
        """
        Find the chunk that best matches the query and return a short preview.
        This is what gets shown under each result in the UI.
        """
        query_tokens = set(tokenize(query))
        best_chunk   = ""
        best_hits    = -1

        for chunk in doc.chunks:
            chunk_tokens = set(tokenize(chunk))
            hits         = len(query_tokens & chunk_tokens)
            if hits > best_hits:
                best_hits  = hits
                best_chunk = chunk

        # trim to snippet_len characters
        if len(best_chunk) > snippet_len:
            best_chunk = best_chunk[:snippet_len].rsplit(" ", 1)[0] + "..."

        return best_chunk

    # ── stats ────────────────────────────────────────────────

    def _avg_doc_length(self) -> float:
        if not self.documents:
            return 1.0
        return self._total_tokens / len(self.documents)

    def stats(self) -> dict:
        return {
            "total_documents": len(self.documents),
            "total_tokens":    self._total_tokens,
            "vocab_size":      len(self.index),
            "avg_doc_length":  round(self._avg_doc_length(), 1),
        }

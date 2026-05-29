# indexer/engine.py
# ─────────────────────────────────────────────────────────────
# Responsibility : orchestrate the full indexing pipeline.
#   scan folder → extract each file → add to index
#
# This is the single object the UI talks to.
# ─────────────────────────────────────────────────────────────

import sys
import os
from typing import List, Tuple, Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discovery.scanner import scan_directory
from extractor import extract_file
from shared_types import ExtractedDocument
from .inverted_index import InvertedIndex


class SearchEngine:
    """
    The main object the UI imports and uses.

    Usage:
        engine = SearchEngine()
        engine.index_folder("/home/user/Documents")
        results = engine.search("machine learning")
        for path, score, doc, snippet in results:
            print(score, path, snippet)
    """

    def __init__(self):
        self.index  = InvertedIndex()
        self._ready = False

    def index_folder(
        self,
        folder_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        """
        Scan a folder, extract every supported file, and index it.

        Args:
            folder_path       : root folder to scan
            progress_callback : optional function called as each file is indexed
                                signature: callback(current, total, file_path)

        Returns:
            dict with keys: indexed, failed, skipped, stats
        """
        files   = scan_directory(folder_path)
        total   = len(files)
        indexed = 0
        failed  = []

        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(i + 1, total, file_path)

            try:
                doc = extract_file(file_path)

                if not doc.raw_text.strip():
                    # empty extraction (e.g. scanned image PDF) — skip silently
                    continue

                self.index.add_document(doc)
                indexed += 1

            except Exception as e:
                failed.append({"file": file_path, "error": str(e)})

        self._ready = True

        return {
            "indexed": indexed,
            "failed":  failed,
            "skipped": total - indexed - len(failed),
            "stats":   self.index.stats(),
        }

    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[str, float, ExtractedDocument, str]]:
        """
        Search the indexed documents.

        Returns:
            List of (file_path, score, doc, snippet) tuples, best first.
        """
        if not query.strip():
            return []

        raw_results = self.index.search(query, top_k=top_k)

        return [
            (doc_id, score, doc, self.index.get_snippet(doc, query))
            for doc_id, score, doc in raw_results
        ]

    @property
    def is_ready(self) -> bool:
        return self._ready

    def stats(self) -> dict:
        return self.index.stats()

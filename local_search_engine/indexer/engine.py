# indexer/engine.py
import sys
import os
from typing import List, Tuple, Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discovery.scanner import scan_directory
from extractor import extract_file
from shared_types import ExtractedDocument
from .inverted_index import InvertedIndex
from .persistence import (
    init_db, is_file_indexed, save_document,
    load_index, get_db_stats, DB_PATH
)


class SearchEngine:

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_db(db_path)

        loaded = load_index(db_path)
        if loaded:
            self.index  = loaded
            self._ready = True

            # clean up files that were deleted while app was closed
            deleted = [p for p in list(self.index.documents.keys()) if not os.path.exists(p)]
            for p in deleted:
                self.index.remove_document(p)
                from .persistence import remove_document as db_remove
                db_remove(p, self.db_path)

            if deleted:
                print(f"Cleaned up {len(deleted)} deleted files from index")

            print(f"Loaded existing index: {len(self.index.documents)} documents")
        else:
            self.index  = InvertedIndex()
            self._ready = False

    def index_folder(
        self,
        folder_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> dict:
        files   = scan_directory(folder_path)
        total   = len(files)
        indexed = 0
        skipped = 0
        failed  = []

        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(i + 1, total, file_path)

            # skip if already indexed and file hasn't changed
            if is_file_indexed(file_path, self.db_path):
                # still load it into memory index if not already there
                if file_path not in self.index.documents:
                    loaded = load_index(self.db_path)
                    if loaded and file_path in loaded.documents:
                        self.index.add_document(loaded.documents[file_path])
                skipped += 1
                continue

            try:
                doc = extract_file(file_path)

                if not doc.raw_text.strip():
                    skipped += 1
                    continue

                # save to disk first, then load into memory
                save_document(doc, self.db_path)
                self.index.add_document(doc)
                indexed += 1

            except Exception as e:
                failed.append({"file": file_path, "error": str(e)})

        self._ready = True

        return {
            "indexed": indexed,
            "skipped": skipped,
            "failed":  failed,
            "stats":   self.index.stats(),
        }

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float, ExtractedDocument, str]]:
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
        return {**self.index.stats(), **get_db_stats(self.db_path)}
    def add_file(self, file_path: str) -> bool:
        """
        Index a single file. Called by watchdog when a new/modified file is detected.
        Returns True if successfully indexed.
        """
        try:
            from extractor import extract_file
            doc = extract_file(file_path)
            if not doc.raw_text.strip():
                return False
            save_document(doc, self.db_path)
            self.index.add_document(doc)
            return True
        except Exception as e:
            print(f"Failed to index {file_path}: {e}")
            return False

    def remove_file(self, file_path: str):
        """Remove a file from index. Called by watchdog when file is deleted."""
        from .persistence import remove_document as db_remove
        self.index.remove_document(file_path)
        db_remove(file_path, self.db_path)
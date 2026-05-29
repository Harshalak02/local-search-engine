# extractor/txt_extractor.py
# ─────────────────────────────────────────────────────────────
# Responsibility : extract text from plain .txt files.
# Member A owns this file.
# ─────────────────────────────────────────────────────────────

import os
from pathlib import Path

import chardet

from .base_extractor import BaseExtractor

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_types import ExtractedDocument


class TXTExtractor(BaseExtractor):

    def can_handle(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() == ".txt"

    def extract(self, file_path: str) -> ExtractedDocument:
        metadata = {
            "file_type":     "txt",
            "title":         Path(file_path).stem,
            "modified_time": os.path.getmtime(file_path),
        }

        # detect encoding first — plain text files are not always UTF-8
        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        detected   = chardet.detect(raw_bytes)
        encoding   = detected.get("encoding") or "utf-8"
        raw_text   = raw_bytes.decode(encoding, errors="replace").strip()

        chunks = self._chunk_text(raw_text)

        return ExtractedDocument(
            file_path=file_path,
            raw_text=raw_text,
            chunks=chunks,
            metadata=metadata,
        )

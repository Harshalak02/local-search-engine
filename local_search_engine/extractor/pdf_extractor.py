# extractor/pdf_extractor.py
# ─────────────────────────────────────────────────────────────
# Responsibility : extract text and metadata from PDF files.
# Member A owns this file.
# ─────────────────────────────────────────────────────────────

import os
from pathlib import Path

import pdfplumber

from .base_extractor import BaseExtractor

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_types import ExtractedDocument


class PDFExtractor(BaseExtractor):

    def can_handle(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() == ".pdf"

    def extract(self, file_path: str) -> ExtractedDocument:
        text_parts = []
        metadata = {"file_type": "pdf"}

        with pdfplumber.open(file_path) as pdf:
            metadata["page_count"] = len(pdf.pages)

            # pdfplumber exposes PDF metadata dict if it exists
            if pdf.metadata:
                metadata["title"]  = pdf.metadata.get("Title", "")
                metadata["author"] = pdf.metadata.get("Author", "")

            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text.strip())

        # NOTE: if text_parts is empty, the PDF is likely a scanned image.
        # pdfplumber cannot OCR — this is a known Phase 1 limitation.
        raw_text = "\n\n".join(text_parts)

        # get file modified time from OS
        metadata["modified_time"] = os.path.getmtime(file_path)
        metadata.setdefault("title", Path(file_path).stem)

        chunks = self._chunk_text(raw_text)

        return ExtractedDocument(
            file_path=file_path,
            raw_text=raw_text,
            chunks=chunks,
            metadata=metadata,
        )

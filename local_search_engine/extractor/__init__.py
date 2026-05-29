# extractor/__init__.py
# ─────────────────────────────────────────────────────────────
# Responsibility : route any file path to the correct extractor.
# This is the ONLY function Member B's indexer should call.
# ─────────────────────────────────────────────────────────────

from .pdf_extractor  import PDFExtractor
from .docx_extractor import DOCXExtractor
from .txt_extractor  import TXTExtractor

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_types import ExtractedDocument

# register all extractors here — order matters if extensions ever overlap
_EXTRACTORS = [
    PDFExtractor(),
    DOCXExtractor(),
    TXTExtractor(),
]


def extract_file(file_path: str) -> ExtractedDocument:
    """
    Main entry point for the extractor system.

    Automatically picks the right extractor for the given file.
    Returns a fully populated ExtractedDocument.

    Raises:
        ValueError : if no extractor supports this file type.
    """
    for extractor in _EXTRACTORS:
        if extractor.can_handle(file_path):
            return extractor.extract(file_path)

    raise ValueError(
        f"No extractor available for: {file_path}\n"
        f"Supported types: .pdf  .docx  .txt"
    )

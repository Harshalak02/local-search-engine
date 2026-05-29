# shared_types.py
# ─────────────────────────────────────────────────────────────
# CONTRACT FILE — agreed between Member A and Member B.
# Do NOT change the field names or types without telling Member B.
# ─────────────────────────────────────────────────────────────

from dataclasses import dataclass, field
from typing import List


@dataclass
class ExtractedDocument:
    """
    What Member A produces. What Member B consumes.

    file_path   : absolute path to the original file
    raw_text    : full extracted text, clean UTF-8 string
    chunks      : text split into overlapping indexable pieces
    metadata    : dict with keys — title, author, page_count,
                  modified_time, file_type
    """
    file_path: str
    raw_text: str
    chunks: List[str]
    metadata: dict = field(default_factory=dict)

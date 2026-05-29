# tests/test_extractor.py
# ─────────────────────────────────────────────────────────────
# Tests for the extractor system.
# Run with:  pytest tests/test_extractor.py -v
# ─────────────────────────────────────────────────────────────

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extractor import extract_file
from extractor.base_extractor import BaseExtractor
from shared_types import ExtractedDocument


# ── chunking logic (unit tests, no real files needed) ────────

class ConcreteExtractor(BaseExtractor):
    """Minimal concrete subclass just to test _chunk_text."""
    def can_handle(self, f): return True
    def extract(self, f):    return None


def test_chunk_text_basic():
    ext    = ConcreteExtractor()
    words  = "word " * 1200          # 1200 words
    chunks = ext._chunk_text(words.strip(), chunk_size=500, overlap=50)

    assert len(chunks) > 1           # must produce multiple chunks
    for c in chunks:
        assert isinstance(c, str)
        assert len(c) > 0


def test_chunk_text_overlap():
    ext  = ConcreteExtractor()
    # 10 words, chunk_size=6, overlap=2 → step=4
    # chunk1 → words 0–5  : "a b c d e f"
    # chunk2 → words 4–9  : "e f g h i j"
    # chunk3 → words 8–9  : "i j"          (tail remainder)
    text   = "a b c d e f g h i j"
    chunks = ext._chunk_text(text, chunk_size=6, overlap=2)

    assert len(chunks) == 3
    # overlap: "e f" appears at end of chunk1 and start of chunk2
    assert chunks[0].endswith("e f")
    assert chunks[1].startswith("e f")


def test_chunk_text_empty_string():
    ext    = ConcreteExtractor()
    chunks = ext._chunk_text("")
    assert chunks == []


# ── txt extraction (no external dependency) ──────────────────

def test_txt_extractor_basic():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write("Hello world. This is a test document with some words in it.")
        tmp_path = f.name

    try:
        doc = extract_file(tmp_path)

        assert isinstance(doc, ExtractedDocument)
        assert doc.file_path == tmp_path
        assert "Hello world" in doc.raw_text
        assert len(doc.chunks) >= 1
        assert doc.metadata["file_type"] == "txt"
    finally:
        os.unlink(tmp_path)


def test_txt_extractor_preserves_content():
    content = "The quick brown fox jumps over the lazy dog. " * 50
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp_path = f.name

    try:
        doc = extract_file(tmp_path)
        # all original words should be present somewhere across chunks
        all_chunk_text = " ".join(doc.chunks)
        assert "quick brown fox" in all_chunk_text
    finally:
        os.unlink(tmp_path)


# ── unsupported file type ─────────────────────────────────────

def test_unsupported_file_raises():
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
        tmp_path = f.name

    try:
        with pytest.raises(ValueError, match="No extractor available"):
            extract_file(tmp_path)
    finally:
        os.unlink(tmp_path)


# ── ExtractedDocument shape ───────────────────────────────────

def test_extracted_document_has_required_fields():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w",
                                     delete=False, encoding="utf-8") as f:
        f.write("Some content here.")
        tmp_path = f.name

    try:
        doc = extract_file(tmp_path)

        assert hasattr(doc, "file_path")
        assert hasattr(doc, "raw_text")
        assert hasattr(doc, "chunks")
        assert hasattr(doc, "metadata")
        assert isinstance(doc.chunks, list)
        assert isinstance(doc.metadata, dict)
    finally:
        os.unlink(tmp_path)

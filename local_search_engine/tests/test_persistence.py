# tests/test_persistence.py
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared_types import ExtractedDocument
from indexer.persistence import (
    init_db, save_document, load_index,
    is_file_indexed, remove_document, get_db_stats
)


def make_doc(file_path, text):
    words  = text.split()
    chunks = [" ".join(words[i:i+50]) for i in range(0, len(words), 50)]
    return ExtractedDocument(
        file_path=file_path,
        raw_text=text,
        chunks=chunks or [text],
        metadata={"file_type": "txt", "title": "test"},
    )


def test_init_creates_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = os.path.join(tmpdir, "test.db")
        init_db(db)
        assert os.path.exists(db)


def test_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        db      = os.path.join(tmpdir, "test.db")
        txtfile = os.path.join(tmpdir, "a.txt")
        open(txtfile, "w").write("python is great for data science and machine learning")

        init_db(db)
        doc = make_doc(txtfile, "python is great for data science and machine learning")
        save_document(doc, db)

        index = load_index(db)
        assert index is not None
        assert len(index.documents) == 1

        results = index.search("python")
        assert len(results) == 1
        assert results[0][0] == txtfile


def test_is_file_indexed():
    with tempfile.TemporaryDirectory() as tmpdir:
        db      = os.path.join(tmpdir, "test.db")
        txtfile = os.path.join(tmpdir, "a.txt")
        open(txtfile, "w").write("hello world")

        init_db(db)
        assert is_file_indexed(txtfile, db) == False

        doc = make_doc(txtfile, "hello world")
        save_document(doc, db)
        assert is_file_indexed(txtfile, db) == True


def test_remove_document():
    with tempfile.TemporaryDirectory() as tmpdir:
        db      = os.path.join(tmpdir, "test.db")
        txtfile = os.path.join(tmpdir, "a.txt")
        open(txtfile, "w").write("hello world")

        init_db(db)
        doc = make_doc(txtfile, "hello world")
        save_document(doc, db)
        remove_document(txtfile, db)

        index = load_index(db)
        assert index is None or len(index.documents) == 0


def test_get_db_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        db      = os.path.join(tmpdir, "test.db")
        txtfile = os.path.join(tmpdir, "a.txt")
        open(txtfile, "w").write("hello world foo bar")

        init_db(db)
        doc = make_doc(txtfile, "hello world foo bar")
        save_document(doc, db)

        stats = get_db_stats(db)
        assert stats["total_documents"] == 1
        assert stats["db_size_kb"] >= 0
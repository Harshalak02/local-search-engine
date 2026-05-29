# tests/test_indexer.py
# ─────────────────────────────────────────────────────────────
# Tests for indexer/inverted_index.py and indexer/engine.py
# Run with:  pytest tests/test_indexer.py -v
# ─────────────────────────────────────────────────────────────

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared_types import ExtractedDocument
from indexer.inverted_index import InvertedIndex, tokenize
from indexer.engine import SearchEngine


# ── helpers ──────────────────────────────────────────────────

def make_doc(file_path: str, text: str) -> ExtractedDocument:
    words  = text.split()
    chunks = [" ".join(words[i:i+50]) for i in range(0, len(words), 50)]
    return ExtractedDocument(
        file_path=file_path,
        raw_text=text,
        chunks=chunks if chunks else [text],
        metadata={"file_type": "txt", "title": os.path.basename(file_path)},
    )


# ── tokenizer ────────────────────────────────────────────────

def test_tokenize_lowercases():
    assert tokenize("Hello World") == ["hello", "world"]

def test_tokenize_strips_punctuation():
    assert tokenize("hello, world!") == ["hello", "world"]

def test_tokenize_empty():
    assert tokenize("") == []


# ── inverted index ───────────────────────────────────────────

def test_add_and_search_basic():
    idx = InvertedIndex()
    idx.add_document(make_doc("/a.txt", "python is a great programming language"))
    idx.add_document(make_doc("/b.txt", "java is also a programming language"))

    results = idx.search("python")
    assert len(results) == 1
    assert results[0][0] == "/a.txt"


def test_search_returns_both_matching_docs():
    idx = InvertedIndex()
    idx.add_document(make_doc("/a.txt", "python programming language"))
    idx.add_document(make_doc("/b.txt", "java programming language"))

    results = idx.search("programming language")
    paths = [r[0] for r in results]
    assert "/a.txt" in paths
    assert "/b.txt" in paths


def test_bm25_ranks_more_relevant_doc_higher():
    idx = InvertedIndex()
    # doc A mentions python many times
    idx.add_document(make_doc("/a.txt", "python python python python python"))
    # doc B mentions python once
    idx.add_document(make_doc("/b.txt", "python java ruby go rust"))

    results = idx.search("python")
    assert results[0][0] == "/a.txt"     # higher tf → higher BM25 score
    assert results[0][1] > results[1][1] # score of A > score of B


def test_search_no_results():
    idx = InvertedIndex()
    idx.add_document(make_doc("/a.txt", "hello world"))

    results = idx.search("zzzznotaword")
    assert results == []


def test_remove_document():
    idx = InvertedIndex()
    idx.add_document(make_doc("/a.txt", "python programming"))
    idx.remove_document("/a.txt")

    results = idx.search("python")
    assert results == []


def test_stats():
    idx = InvertedIndex()
    idx.add_document(make_doc("/a.txt", "hello world foo bar"))
    idx.add_document(make_doc("/b.txt", "foo bar baz"))

    s = idx.stats()
    assert s["total_documents"] == 2
    assert s["vocab_size"] >= 5


def test_get_snippet_contains_query_word():
    idx = InvertedIndex()
    doc = make_doc("/a.txt", "the quick brown fox jumps over the lazy dog " * 10)
    idx.add_document(doc)

    snippet = idx.get_snippet(doc, "fox")
    assert "fox" in snippet.lower()


# ── search engine (integration) ──────────────────────────────

def test_engine_index_and_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        # write two real txt files
        f1 = os.path.join(tmpdir, "python.txt")
        f2 = os.path.join(tmpdir, "cooking.txt")
        open(f1, "w").write("python is a great programming language used for data science")
        open(f2, "w").write("cooking pasta requires boiling water and adding salt")

        engine = SearchEngine()
        result = engine.index_folder(tmpdir)

        assert result["indexed"] == 2
        assert engine.is_ready

        hits = engine.search("python programming")
        assert len(hits) >= 1
        assert "python.txt" in hits[0][0]


def test_engine_empty_query_returns_nothing():
    engine = SearchEngine()
    assert engine.search("") == []


def test_engine_search_before_indexing_returns_nothing():
    engine = SearchEngine()
    assert engine.search("hello") == []

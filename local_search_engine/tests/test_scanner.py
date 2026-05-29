# tests/test_scanner.py
# ─────────────────────────────────────────────────────────────
# Tests for discovery/scanner.py
# Run with:  pytest tests/test_scanner.py -v
# ─────────────────────────────────────────────────────────────

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from discovery.scanner import scan_directory, scan_directory_lazy


# ── helpers ──────────────────────────────────────────────────

def make_file(directory: str, filename: str) -> str:
    """Create an empty file and return its path."""
    path = os.path.join(directory, filename)
    open(path, "w").close()
    return path


# ── tests ────────────────────────────────────────────────────

def test_finds_pdf_and_txt():
    with tempfile.TemporaryDirectory() as tmpdir:
        make_file(tmpdir, "report.pdf")
        make_file(tmpdir, "notes.txt")

        results = scan_directory(tmpdir)
        extensions = {os.path.splitext(f)[1].lower() for f in results}

        assert ".pdf" in extensions
        assert ".txt" in extensions


def test_ignores_unsupported_extensions():
    with tempfile.TemporaryDirectory() as tmpdir:
        make_file(tmpdir, "photo.png")
        make_file(tmpdir, "data.csv")
        make_file(tmpdir, "archive.zip")

        results = scan_directory(tmpdir)
        assert results == []


def test_scans_subdirectories_recursively():
    with tempfile.TemporaryDirectory() as tmpdir:
        subdir = os.path.join(tmpdir, "subdir")
        os.makedirs(subdir)
        make_file(subdir, "deep.pdf")

        results = scan_directory(tmpdir)
        assert any("deep.pdf" in r for r in results)


def test_skips_hidden_folders():
    with tempfile.TemporaryDirectory() as tmpdir:
        hidden = os.path.join(tmpdir, ".git")
        os.makedirs(hidden)
        make_file(hidden, "secret.pdf")

        results = scan_directory(tmpdir)
        assert len(results) == 0


def test_raises_on_missing_folder():
    with pytest.raises(FileNotFoundError):
        scan_directory("/this/path/absolutely/does/not/exist")


def test_returns_absolute_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        make_file(tmpdir, "file.pdf")

        results = scan_directory(tmpdir)
        assert all(os.path.isabs(r) for r in results)


def test_lazy_scanner_yields_same_results():
    with tempfile.TemporaryDirectory() as tmpdir:
        make_file(tmpdir, "a.pdf")
        make_file(tmpdir, "b.txt")
        make_file(tmpdir, "c.docx")

        eager  = sorted(scan_directory(tmpdir))
        lazy   = sorted(scan_directory_lazy(tmpdir))

        assert eager == lazy

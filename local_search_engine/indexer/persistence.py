# indexer/persistence.py
# ─────────────────────────────────────────────────────────────
# Responsibility : save and load the index to/from SQLite.
#
# What gets stored:
#   documents table  → file_path, raw_text, metadata, modified_time
#   chunks table     → file_path, chunk_index, chunk_text
#   tokens table     → token, file_path, term_frequency
# ─────────────────────────────────────────────────────────────

import sqlite3
import json
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_types import ExtractedDocument
from .inverted_index import InvertedIndex, tokenize

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "search_index.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")   # faster writes
    return conn


def init_db(db_path: str = DB_PATH):
    """Create tables if they don't exist yet."""
    with get_connection(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                file_path     TEXT PRIMARY KEY,
                raw_text      TEXT,
                metadata      TEXT,
                modified_time REAL
            );

            CREATE TABLE IF NOT EXISTS chunks (
                file_path   TEXT,
                chunk_index INTEGER,
                chunk_text  TEXT,
                PRIMARY KEY (file_path, chunk_index)
            );

            CREATE TABLE IF NOT EXISTS tokens (
                token     TEXT,
                file_path TEXT,
                tf        INTEGER,
                PRIMARY KEY (token, file_path)
            );
        """)


def is_file_indexed(file_path: str, db_path: str = DB_PATH) -> bool:
    """
    Check if a file is already indexed AND hasn't changed since.
    Compares the file's current modified_time against what's stored in DB.
    """
    try:
        current_mtime = os.path.getmtime(file_path)
    except FileNotFoundError:
        return False

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT modified_time FROM documents WHERE file_path = ?",
            (file_path,)
        ).fetchone()

    if row is None:
        return False  # not in DB at all

    stored_mtime = row[0]
    return abs(current_mtime - stored_mtime) < 0.01   # same file, not changed


def save_document(doc: ExtractedDocument, db_path: str = DB_PATH):
    """Persist one ExtractedDocument and its token frequencies to SQLite."""
    modified_time = os.path.getmtime(doc.file_path)

    # compute term frequencies for this document
    full_text = " ".join(doc.chunks)
    tokens    = tokenize(full_text)
    tf_map    = {}
    for token in tokens:
        tf_map[token] = tf_map.get(token, 0) + 1

    with get_connection(db_path) as conn:
        # upsert document row
        conn.execute("""
            INSERT OR REPLACE INTO documents (file_path, raw_text, metadata, modified_time)
            VALUES (?, ?, ?, ?)
        """, (doc.file_path, doc.raw_text, json.dumps(doc.metadata), modified_time))

        # delete old chunks and tokens for this file (in case of re-index)
        conn.execute("DELETE FROM chunks WHERE file_path = ?", (doc.file_path,))
        conn.execute("DELETE FROM tokens WHERE file_path = ?", (doc.file_path,))

        # insert chunks
        conn.executemany(
            "INSERT INTO chunks (file_path, chunk_index, chunk_text) VALUES (?, ?, ?)",
            [(doc.file_path, i, chunk) for i, chunk in enumerate(doc.chunks)]
        )

        # insert token frequencies
        conn.executemany(
            "INSERT INTO tokens (token, file_path, tf) VALUES (?, ?, ?)",
            [(token, doc.file_path, tf) for token, tf in tf_map.items()]
        )


def load_index(db_path: str = DB_PATH) -> Optional[InvertedIndex]:
    """
    Load the full index from SQLite into memory.
    Returns None if DB doesn't exist or is empty.
    """
    if not os.path.exists(db_path):
        return None

    with get_connection(db_path) as conn:
        doc_rows   = conn.execute("SELECT file_path, raw_text, metadata, modified_time FROM documents").fetchall()
        chunk_rows = conn.execute("SELECT file_path, chunk_index, chunk_text FROM chunks ORDER BY file_path, chunk_index").fetchall()
        token_rows = conn.execute("SELECT token, file_path, tf FROM tokens").fetchall()

    if not doc_rows:
        return None

    # rebuild chunk lists per document
    chunks_by_file = {}
    for file_path, chunk_index, chunk_text in chunk_rows:
        chunks_by_file.setdefault(file_path, []).append((chunk_index, chunk_text))

    # sort chunks by index
    for file_path in chunks_by_file:
        chunks_by_file[file_path].sort(key=lambda x: x[0])
        chunks_by_file[file_path] = [c[1] for c in chunks_by_file[file_path]]

    # rebuild InvertedIndex in memory
    index = InvertedIndex()

    for file_path, raw_text, metadata_json, modified_time in doc_rows:
        doc = ExtractedDocument(
            file_path=file_path,
            raw_text=raw_text,
            chunks=chunks_by_file.get(file_path, []),
            metadata=json.loads(metadata_json),
        )
        index.documents[file_path]   = doc
        index.doc_lengths[file_path] = len(tokenize(" ".join(doc.chunks)))
        index._total_tokens         += index.doc_lengths[file_path]

    for token, file_path, tf in token_rows:
        index.index[token][file_path] = tf

    return index


def remove_document(file_path: str, db_path: str = DB_PATH):
    """Remove a document from SQLite (used when file is deleted)."""
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM documents WHERE file_path = ?", (file_path,))
        conn.execute("DELETE FROM chunks    WHERE file_path = ?", (file_path,))
        conn.execute("DELETE FROM tokens    WHERE file_path = ?", (file_path,))


def get_db_stats(db_path: str = DB_PATH) -> dict:
    if not os.path.exists(db_path):
        return {"total_documents": 0, "db_size_kb": 0}

    with get_connection(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    size_kb = os.path.getsize(db_path) // 1024
    return {"total_documents": total, "db_size_kb": size_kb}
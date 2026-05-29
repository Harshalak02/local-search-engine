# discovery/scanner.py
# ─────────────────────────────────────────────────────────────
# Responsibility : walk folders and return supported file paths.
# Member A owns this file.
# ─────────────────────────────────────────────────────────────

import os
from pathlib import Path
from typing import List, Generator

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def scan_directory(root_path: str) -> List[str]:
    """
    Walk a folder recursively and return all supported file paths.

    Args:
        root_path : folder to scan, e.g. "/home/user/Documents"

    Returns:
        List of absolute file path strings.

    Raises:
        FileNotFoundError : if root_path does not exist.
    """
    root = Path(root_path)

    if not root.exists():
        raise FileNotFoundError(f"Folder not found: {root_path}")

    found_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # skip hidden folders like .git, __pycache__, .venv
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]

        for filename in filenames:
            filepath = Path(dirpath) / filename
            if filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
                found_files.append(str(filepath.resolve()))

    return found_files


def scan_directory_lazy(root_path: str) -> Generator[str, None, None]:
    """
    Same as scan_directory but yields one path at a time.
    Use this for large folders to avoid loading everything into memory.
    """
    root = Path(root_path)

    if not root.exists():
        raise FileNotFoundError(f"Folder not found: {root_path}")

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]

        for filename in filenames:
            filepath = Path(dirpath) / filename
            if filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield str(filepath.resolve())

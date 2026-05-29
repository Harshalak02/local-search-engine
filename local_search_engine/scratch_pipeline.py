# scratch_pipeline.py
# ─────────────────────────────────────────────────────────────
# Run this manually to verify the full pipeline end-to-end.
# Point SCAN_FOLDER at a real folder containing PDFs/DOCX/TXT.
#
# Usage:
#   python scratch_pipeline.py
#   python scratch_pipeline.py /path/to/your/documents
# ─────────────────────────────────────────────────────────────

import sys
import os

# allow running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from discovery.scanner import scan_directory
from extractor import extract_file

# ── configure this ────────────────────────────────────────────
SCAN_FOLDER = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Documents")
# ─────────────────────────────────────────────────────────────


def main():
    print(f"\nScanning: {SCAN_FOLDER}\n{'─'*50}")

    try:
        files = scan_directory(SCAN_FOLDER)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Usage: python scratch_pipeline.py /path/to/folder")
        sys.exit(1)

    if not files:
        print("No supported files found (.pdf .docx .txt)")
        sys.exit(0)

    print(f"Found {len(files)} file(s)\n")

    for path in files:
        print(f"FILE     : {path}")
        try:
            doc = extract_file(path)
            print(f"CHARS    : {len(doc.raw_text)}")
            print(f"CHUNKS   : {len(doc.chunks)}")
            print(f"METADATA : {doc.metadata}")
            if doc.chunks:
                preview = doc.chunks[0][:120].replace("\n", " ")
                print(f"PREVIEW  : {preview}...")
            else:
                print("PREVIEW  : (empty — scanned image PDF?)")
        except Exception as e:
            print(f"ERROR    : {e}")
        print("─" * 50)


if __name__ == "__main__":
    main()

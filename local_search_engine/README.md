# Local Search Engine

Hybrid AI-powered local file search — keyword + semantic + real-time.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run tests

```bash
pytest tests/ -v
```

## Quick pipeline test

```bash
python scratch_pipeline.py /path/to/your/documents
```

---

## Project structure

```
local_search_engine/
├── shared_types.py          ← contract between Member A and B
├── discovery/
│   ├── scanner.py           ← file discovery (Member A, Phase 1)
│   └── monitor.py           ← real-time watching (Phase 2)
├── extractor/
│   ├── base_extractor.py    ← abstract interface
│   ├── pdf_extractor.py     ← PDF → text
│   ├── docx_extractor.py    ← DOCX → text
│   ├── txt_extractor.py     ← TXT → text
│   └── __init__.py          ← dispatcher: extract_file()
├── indexer/                 ← Member B: keyword index + BM25
├── ui/                      ← Member B: PyQt search interface
└── tests/
    ├── test_scanner.py
    └── test_extractor.py
```

## Known limitations (Phase 1)

- Scanned image PDFs return empty text — pdfplumber cannot OCR.
- No semantic search yet — keyword only in Phase 1.
- No real-time monitoring yet — manual re-scan only.

---

## Team split

| Member | Phase 1 owns            | Phase 2 takes over      |
|--------|-------------------------|-------------------------|
| A      | discovery + extractor   | indexer + chunking      |
| B      | indexer + UI            | monitoring + UI upgrade |

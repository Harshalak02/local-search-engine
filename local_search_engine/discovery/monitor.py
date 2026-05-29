# discovery/monitor.py
# ─────────────────────────────────────────────────────────────
# Responsibility : watch folders for new/modified/deleted files
#                 and trigger re-indexing automatically.
# Phase 2 — leave empty for now.
# Member B will own this after the Phase 2 swap.
# ─────────────────────────────────────────────────────────────

# TODO (Phase 2):
#   pip install watchdog
#   Implement FileChangeHandler(FileSystemEventHandler)
#   on_created  → extract + index the new file
#   on_modified → re-extract + re-index
#   on_deleted  → remove from index

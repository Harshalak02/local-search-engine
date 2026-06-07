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



# discovery/monitor.py
# discovery/monitor.py
# discovery/monitor.py
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class FileChangeHandler(FileSystemEventHandler):

    def __init__(self, on_new_file, on_deleted_file):
        self.on_new_file     = on_new_file
        self.on_deleted_file = on_deleted_file
        self._recently_seen  = {}
        super().__init__()

    def _is_supported(self, path: str) -> bool:
        return os.path.splitext(path)[1].lower() in SUPPORTED_EXTENSIONS

    def _debounce(self, path: str) -> bool:
        now  = time.time()
        last = self._recently_seen.get(path, 0)
        if now - last < 2.0:
            return False
        self._recently_seen[path] = now
        return True

    def on_created(self, event):
        print(f"on_created fired: {event.src_path}")
        # don't index on created — wait for on_closed which fires after fully written
        pass

    def on_modified(self, event):
        print(f"on_modified fired: {event.src_path}")
        if not event.is_directory and self._is_supported(event.src_path):
            if os.path.exists(event.src_path):
                if self._debounce(event.src_path):
                    self.on_new_file(event.src_path)

    def on_closed(self, event):
        print(f"on_closed fired: {event.src_path}")
        if not event.is_directory and self._is_supported(event.src_path):
            if os.path.exists(event.src_path):
                # reset debounce so on_closed always goes through
                self._recently_seen.pop(event.src_path, None)
                if self._debounce(event.src_path):
                    self.on_new_file(event.src_path)

    def on_deleted(self, event):
        print(f"on_deleted fired: {event.src_path}")
        if not event.is_directory and self._is_supported(event.src_path):
            self.on_deleted_file(event.src_path)

    def on_moved(self, event):
        print(f"on_moved fired: {event.src_path} -> {event.dest_path}")
        if not event.is_directory:
            if self._is_supported(event.dest_path):
                if self._debounce(event.dest_path):
                    self.on_new_file(event.dest_path)
            if self._is_supported(event.src_path):
                self.on_deleted_file(event.src_path)


class FolderMonitor:

    def __init__(self, folder_path: str, on_new_file, on_deleted_file):
        self.folder_path = folder_path
        self.handler     = FileChangeHandler(on_new_file, on_deleted_file)
        self.observer    = Observer()
        self._running    = False

    def start(self):
        self.observer.schedule(self.handler, self.folder_path, recursive=True)
        self.observer.start()
        self._running = True

    def stop(self):
        if self._running:
            self.observer.stop()
            self.observer.join()
            self._running = False

    @property
    def is_running(self):
        return self._running
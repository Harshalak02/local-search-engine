# ui/app.py
import sys
import os
import threading
import subprocess
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from discovery.monitor import FolderMonitor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indexer import SearchEngine

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config.json"
)


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            return json.load(open(CONFIG_PATH))
        except Exception:
            pass
    return {}


def save_config(data: dict):
    try:
        json.dump(data, open(CONFIG_PATH, "w"))
    except Exception:
        pass


class SearchApp:

    def __init__(self, root: tk.Tk):
        self.root   = root
        self.engine = SearchEngine()
        self.config = load_config()
        self.monitor = None

        root.title("Local Search Engine")
        root.geometry("900x650")
        root.minsize(700, 500)

        self._build_ui()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        # auto-index last folder on startup if one exists
        last_folder = self.config.get("last_folder", "")
        if last_folder and os.path.isdir(last_folder):
            self.folder_var.set(last_folder)
            # slight delay so UI fully renders before indexing starts
            self.root.after(500, self._start_indexing)
        
    def _start_monitor(self, folder: str):
        if self.monitor:
            self.monitor.stop()

        def on_new_file(file_path: str):
            print(f"NEW FILE DETECTED: {file_path}")
            success = self.engine.add_file(file_path)
            print(f"INDEXED: {success}")
            if success:
                filename = os.path.basename(file_path)
                s = self.engine.stats()
                self.root.after(0, lambda: self.stats_var.set(
                    f"Ready — {s['total_documents']} documents  •  "
                    f"{s['vocab_size']:,} unique words  •  "
                    f"just indexed: {filename}"
                ))

        def on_deleted_file(file_path: str):
            print(f"DELETED DETECTED: {file_path}")
            self.engine.remove_file(file_path)

        self.monitor = FolderMonitor(folder, on_new_file, on_deleted_file)
        self.monitor.start()
        print(f"WATCHDOG STARTED on: {folder}")
    # ── UI construction ──────────────────────────────────────
    def _on_close(self):
        if self.monitor:
            self.monitor.stop()
        self.root.destroy()
        
    def _build_ui(self):
        top = tk.Frame(self.root, padx=10, pady=8)
        top.pack(fill=tk.X)

        tk.Label(top, text="Folder:").pack(side=tk.LEFT)

        self.folder_var = tk.StringVar(value=os.path.expanduser("~"))
        folder_entry = tk.Entry(top, textvariable=self.folder_var, width=55)
        folder_entry.pack(side=tk.LEFT, padx=(4, 4))

        tk.Button(top, text="Browse", command=self._browse_folder).pack(side=tk.LEFT)
        tk.Button(top, text="Index Folder", command=self._start_indexing,
                  bg="#4a90d9", fg="white").pack(side=tk.LEFT, padx=(8, 0))

        self.progress_frame = tk.Frame(self.root, padx=10)
        self.progress_frame.pack(fill=tk.X)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_label = tk.Label(self.progress_frame, text="", fg="gray")

        search_frame = tk.Frame(self.root, padx=10, pady=6)
        search_frame.pack(fill=tk.X)

        self.query_var = tk.StringVar()
        search_entry   = tk.Entry(search_frame, textvariable=self.query_var,
                                  font=("Arial", 13), width=60)
        search_entry.pack(side=tk.LEFT, ipady=4)
        search_entry.bind("<Return>", lambda e: self._run_search())

        tk.Button(search_frame, text="Search", command=self._run_search,
                  bg="#4a90d9", fg="white", padx=10).pack(side=tk.LEFT, padx=(6, 0))

        self.stats_var = tk.StringVar(value="Loading...")
        tk.Label(self.root, textvariable=self.stats_var,
                 fg="gray", anchor="w", padx=10).pack(fill=tk.X)

        ttk.Separator(self.root).pack(fill=tk.X, padx=10)

        results_frame = tk.Frame(self.root, padx=10, pady=6)
        results_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas    = tk.Canvas(results_frame, highlightthickness=0)
        scrollbar      = ttk.Scrollbar(results_frame, orient="vertical",
                                       command=self.canvas.yview)
        self.scrollable = tk.Frame(self.canvas)

        self.scrollable.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind_all("<Button-4>",
                             lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>",
                             lambda e: self.canvas.yview_scroll(1, "units"))

    # ── event handlers ───────────────────────────────────────

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def _start_indexing(self):
        folder = self.folder_var.get().strip()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"Folder not found:\n{folder}")
            return

        # save folder to config so next startup auto-loads it
        self.config["last_folder"] = folder
        save_config(self.config)

        self.progress_bar.pack(fill=tk.X, pady=2)
        self.progress_label.pack(anchor="w")
        self.progress_var.set(0)
        self.stats_var.set("Checking index...")
        self._clear_results()

        thread = threading.Thread(target=self._index_worker, args=(folder,), daemon=True)
        thread.start()

    def _index_worker(self, folder: str):
        def on_progress(current, total, file_path):
            pct      = (current / total) * 100
            filename = os.path.basename(file_path)
            self.root.after(0, lambda: self.progress_var.set(pct))
            self.root.after(0, lambda: self.progress_label.config(
                text=f"[{current}/{total}] {filename}"
            ))

        result = self.engine.index_folder(folder, progress_callback=on_progress)

        def on_done():
            s = result["stats"]
            self.stats_var.set(
                f"Indexed {s['total_documents']} documents  •  "
                f"{s['vocab_size']:,} unique words  •  "
                f"{len(result['failed'])} failed  •  "
                f"{result['skipped']} skipped (already indexed)"
            )
            self.progress_bar.pack_forget()
            self.progress_label.pack_forget()
            self._start_monitor(folder)   # ← start watching after indexing done

        self.root.after(0, on_done)

    def _run_search(self):
        query = self.query_var.get().strip()

        if not query:
            return

        if not self.engine.is_ready:
            messagebox.showinfo("Not ready", "Please wait for indexing to finish.")
            return

        results = self.engine.search(query, top_k=15)
        self._clear_results()
        self._render_results(results, query)

    # ── results rendering ────────────────────────────────────

    def _clear_results(self):
        for widget in self.scrollable.winfo_children():
            widget.destroy()

    def _render_results(self, results, query: str):
        if not results:
            tk.Label(self.scrollable, text="No results found.",
                     fg="gray", font=("Arial", 11), pady=20).pack()
            return

        tk.Label(self.scrollable,
                 text=f"{len(results)} result(s) for '{query}'",
                 fg="gray", font=("Arial", 10), anchor="w").pack(fill=tk.X, pady=(0, 4))

        for rank, (file_path, score, doc, snippet) in enumerate(results, start=1):
            self._render_card(rank, file_path, score, doc, snippet)

        self.scrollable.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _render_card(self, rank, file_path, score, doc, snippet):
        card = tk.Frame(self.scrollable, relief=tk.RIDGE, bd=1,
                        padx=10, pady=8, bg="white")
        card.pack(fill=tk.X, pady=3)

        header = tk.Frame(card, bg="white")
        header.pack(fill=tk.X)

        tk.Label(header, text=f"#{rank}", fg="#888", bg="white",
                 font=("Arial", 9), width=3).pack(side=tk.LEFT)

        filename = os.path.basename(file_path)
        tk.Label(header, text=filename, fg="#1a73e8", bg="white",
                 font=("Arial", 11, "bold"), cursor="hand2").pack(side=tk.LEFT)

        tk.Label(header, text=f"score: {score:.2f}", fg="#aaa", bg="white",
                 font=("Arial", 9)).pack(side=tk.RIGHT)

        tk.Label(card, text=file_path, fg="#888", bg="white",
                 font=("Arial", 8), anchor="w").pack(fill=tk.X)

        if snippet:
            tk.Label(card, text=snippet, fg="#333", bg="white",
                     font=("Arial", 10), wraplength=820,
                     justify=tk.LEFT, anchor="w").pack(fill=tk.X, pady=(4, 0))

        tk.Button(card, text="Open file",
                  command=lambda p=file_path: self._open_file(p),
                  fg="#1a73e8", bg="white", relief=tk.FLAT,
                  font=("Arial", 9), cursor="hand2").pack(anchor="e")

        for widget in [card, header]:
            widget.bind("<Double-Button-1>", lambda e, p=file_path: self._open_file(p))

    def _open_file(self, file_path: str):
        try:
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", file_path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
            else:
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")


def main():
    root = tk.Tk()
    SearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
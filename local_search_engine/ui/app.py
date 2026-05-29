# ui/app.py
# ─────────────────────────────────────────────────────────────
# Responsibility : desktop search UI built with tkinter.
# tkinter ships with Python — no extra install needed.
#
# Features:
#   ✅ folder picker
#   ✅ indexing progress bar
#   ✅ search bar
#   ✅ ranked results list with snippets
#   ✅ double-click to open file
#   ✅ stats display
# ─────────────────────────────────────────────────────────────

import sys
import os
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indexer import SearchEngine


class SearchApp:

    def __init__(self, root: tk.Tk):
        self.root   = root
        self.engine = SearchEngine()

        root.title("Local Search Engine")
        root.geometry("900x650")
        root.minsize(700, 500)

        self._build_ui()

    # ── UI construction ──────────────────────────────────────

    def _build_ui(self):
        # ── top bar: folder picker + index button ────────────
        top = tk.Frame(self.root, padx=10, pady=8)
        top.pack(fill=tk.X)

        tk.Label(top, text="Folder:").pack(side=tk.LEFT)

        self.folder_var = tk.StringVar(value=os.path.expanduser("~"))
        folder_entry = tk.Entry(top, textvariable=self.folder_var, width=55)
        folder_entry.pack(side=tk.LEFT, padx=(4, 4))

        tk.Button(top, text="Browse", command=self._browse_folder).pack(side=tk.LEFT)
        tk.Button(top, text="Index Folder", command=self._start_indexing,
                  bg="#4a90d9", fg="white").pack(side=tk.LEFT, padx=(8, 0))

        # ── progress bar (hidden until indexing starts) ──────
        self.progress_frame = tk.Frame(self.root, padx=10)
        self.progress_frame.pack(fill=tk.X)

        self.progress_var   = tk.DoubleVar()
        self.progress_bar   = ttk.Progressbar(
            self.progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_label = tk.Label(self.progress_frame, text="", fg="gray")
        # not packed yet — shown only during indexing

        # ── search bar ───────────────────────────────────────
        search_frame = tk.Frame(self.root, padx=10, pady=6)
        search_frame.pack(fill=tk.X)

        self.query_var = tk.StringVar()
        search_entry   = tk.Entry(search_frame, textvariable=self.query_var,
                                  font=("Arial", 13), width=60)
        search_entry.pack(side=tk.LEFT, ipady=4)
        search_entry.bind("<Return>", lambda e: self._run_search())

        tk.Button(search_frame, text="Search", command=self._run_search,
                  bg="#4a90d9", fg="white", padx=10).pack(side=tk.LEFT, padx=(6, 0))

        # ── stats label ──────────────────────────────────────
        self.stats_var = tk.StringVar(value="No folder indexed yet.")
        tk.Label(self.root, textvariable=self.stats_var,
                 fg="gray", anchor="w", padx=10).pack(fill=tk.X)

        ttk.Separator(self.root).pack(fill=tk.X, padx=10)

        # ── results area ─────────────────────────────────────
        results_frame = tk.Frame(self.root, padx=10, pady=6)
        results_frame.pack(fill=tk.BOTH, expand=True)

        # scrollable canvas holding result cards
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

        # mouse wheel scrolling
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

        # show progress bar
        self.progress_bar.pack(fill=tk.X, pady=2)
        self.progress_label.pack(anchor="w")
        self.progress_var.set(0)
        self.stats_var.set("Indexing...")

        # clear old results
        self._clear_results()

        # run indexing in background thread so UI doesn't freeze
        thread = threading.Thread(target=self._index_worker, args=(folder,), daemon=True)
        thread.start()

    def _index_worker(self, folder: str):
        """Runs in background thread."""
        self.engine = SearchEngine()

        def on_progress(current, total, file_path):
            pct      = (current / total) * 100
            filename = os.path.basename(file_path)
            # update UI from main thread
            self.root.after(0, lambda: self.progress_var.set(pct))
            self.root.after(0, lambda: self.progress_label.config(
                text=f"[{current}/{total}] {filename}"
            ))

        result = self.engine.index_folder(folder, progress_callback=on_progress)

        # back on main thread: update stats, hide progress
        def on_done():
            s = result["stats"]
            self.stats_var.set(
                f"Indexed {s['total_documents']} documents  •  "
                f"{s['vocab_size']:,} unique words  •  "
                f"{result['failed'].__len__()} failed"
            )
            self.progress_bar.pack_forget()
            self.progress_label.pack_forget()

        self.root.after(0, on_done)

    def _run_search(self):
        query = self.query_var.get().strip()

        if not query:
            return

        if not self.engine.is_ready:
            messagebox.showinfo("Not ready", "Please index a folder first.")
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
        print(f"Results found: {len(results)}")

    def _render_card(self, rank: int, file_path: str, score: float,
                     doc, snippet: str):
        """Render one result card."""
        card = tk.Frame(self.scrollable, relief=tk.RIDGE, bd=1,
                        padx=10, pady=8, bg="white")
        card.pack(fill=tk.X, pady=3)

        # ── rank + filename ──────────────────────────────────
        header = tk.Frame(card, bg="white")
        header.pack(fill=tk.X)

        tk.Label(header, text=f"#{rank}", fg="#888", bg="white",
                 font=("Arial", 9), width=3).pack(side=tk.LEFT)

        filename = os.path.basename(file_path)
        tk.Label(header, text=filename, fg="#1a73e8", bg="white",
                 font=("Arial", 11, "bold"), cursor="hand2").pack(side=tk.LEFT)

        score_txt = f"score: {score:.2f}"
        tk.Label(header, text=score_txt, fg="#aaa", bg="white",
                 font=("Arial", 9)).pack(side=tk.RIGHT)

        # ── full path ────────────────────────────────────────
        tk.Label(card, text=file_path, fg="#888", bg="white",
                 font=("Arial", 8), anchor="w").pack(fill=tk.X)

        # ── snippet ──────────────────────────────────────────
        if snippet:
            tk.Label(card, text=snippet, fg="#333", bg="white",
                     font=("Arial", 10), wraplength=820,
                     justify=tk.LEFT, anchor="w").pack(fill=tk.X, pady=(4, 0))

        # ── open button ──────────────────────────────────────
        open_btn = tk.Button(card, text="Open file",
                             command=lambda p=file_path: self._open_file(p),
                             fg="#1a73e8", bg="white", relief=tk.FLAT,
                             font=("Arial", 9), cursor="hand2")
        open_btn.pack(anchor="e")

        # clicking anywhere on the card opens the file
        for widget in [card, header]:
            widget.bind("<Double-Button-1>", lambda e, p=file_path: self._open_file(p))

    def _open_file(self, file_path: str):
        """Open the file with the system default application."""
        try:
            if sys.platform == "linux":
                subprocess.Popen(["xdg-open", file_path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", file_path])
            else:
                os.startfile(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")


# ── entry point ──────────────────────────────────────────────

def main():
    root = tk.Tk()
    SearchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

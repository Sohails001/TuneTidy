"""Minimal cross-platform Tkinter GUI for TuneTidy.

Two-phase flow: "Scan for Matches" gathers a few candidate matches per file
without touching anything, then you review and pick the right one for each
file (or skip it), then "Apply" does the actual tagging/renaming.
"""
import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

from . import cli as core


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TuneTidy")
        self.geometry("700x600")

        self.pending = []      # [{"path": ..., "candidates": [...]}]
        self.selections = {}   # path -> chosen candidate index, or -1 for skip
        self.review_index = 0

        self.folder_var = tk.StringVar()
        self.pattern_var = tk.StringVar(value="{artist}/{album}/{track} - {title}")
        self.apikey_var = tk.StringVar(value=os.environ.get("ACOUSTID_API_KEY", ""))
        self.discogs_var = tk.StringVar(value=os.environ.get("DISCOGS_TOKEN", ""))
        self.bpmkey_var = tk.StringVar(value=os.environ.get("GETSONGBPM_API_KEY", ""))
        self.dryrun_var = tk.BooleanVar(value=True)
        self.nocover_var = tk.BooleanVar(value=False)

        settings = ttk.Frame(self, padding=10)
        settings.pack(fill="x")

        ttk.Label(settings, text="Music folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.folder_var, width=55).grid(row=0, column=1)
        ttk.Button(settings, text="Browse", command=self.browse).grid(row=0, column=2, padx=4)

        ttk.Label(settings, text="AcoustID API key:").grid(row=1, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.apikey_var, width=55).grid(row=1, column=1, columnspan=2, sticky="w")

        ttk.Label(settings, text="Discogs token (optional):").grid(row=2, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.discogs_var, width=55).grid(row=2, column=1, columnspan=2, sticky="w")

        ttk.Label(settings, text="GetSongBPM key (optional):").grid(row=3, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.bpmkey_var, width=55).grid(row=3, column=1, columnspan=2, sticky="w")

        ttk.Label(settings, text="Naming pattern:").grid(row=4, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.pattern_var, width=55).grid(row=4, column=1, columnspan=2, sticky="w")

        ttk.Checkbutton(settings, text="Dry run (preview only)", variable=self.dryrun_var).grid(row=5, column=0, sticky="w")
        ttk.Checkbutton(settings, text="Skip cover art", variable=self.nocover_var).grid(row=5, column=1, sticky="w")

        self.scan_button = ttk.Button(settings, text="Scan for Matches", command=self.start_scan)
        self.scan_button.grid(row=6, column=1, pady=8)

        # --- Review section (hidden until a scan finishes) ---
        self.review_frame = ttk.LabelFrame(self, text="Review matches", padding=10)
        self.review_label = ttk.Label(self.review_frame, text="")
        self.review_label.pack(anchor="w")
        self.candidates_frame = ttk.Frame(self.review_frame)
        self.candidates_frame.pack(fill="x", pady=6)
        self.candidate_var = tk.IntVar(value=-1)

        nav = ttk.Frame(self.review_frame)
        nav.pack(fill="x")
        self.back_button = ttk.Button(nav, text="< Back", command=lambda: self.show_file(self.review_index - 1))
        self.back_button.pack(side="left")
        self.next_button = ttk.Button(nav, text="Next >", command=lambda: self.show_file(self.review_index + 1))
        self.next_button.pack(side="left", padx=6)
        self.apply_button = ttk.Button(nav, text="Apply All & Tag Files", command=self.start_apply)
        self.apply_button.pack(side="right")

        self.log_box = scrolledtext.ScrolledText(self, height=16)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def browse(self):
        d = filedialog.askdirectory()
        if d:
            self.folder_var.set(d)

    def logmsg(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.update_idletasks()

    # --- Phase 1: scan for candidates (nothing is written yet) ---

    def start_scan(self):
        folder = self.folder_var.get()
        if not folder:
            self.logmsg("Please choose a folder first.")
            return
        self.review_frame.pack_forget()
        self.pending, self.selections = [], {}
        self.scan_button.config(state="disabled", text="Scanning...")
        threading.Thread(target=self.run_scan, args=(folder,), daemon=True).start()

    def run_scan(self, folder):
        files = list(core.find_audio_files(folder))
        self.logmsg(f"Found {len(files)} audio file(s). Gathering possible matches...")
        for f in files:
            item = core.gather_candidates(
                f, self.apikey_var.get() or None,
                discogs_token=self.discogs_var.get() or None,
                log=self.logmsg,
            )
            self.pending.append(item)
        self.logmsg("Scan complete - review the matches below, then click Apply.")
        self.scan_button.config(state="normal", text="Scan for Matches")
        self.after(0, self.begin_review)

    # --- Phase 2: human picks the right candidate per file ---

    def begin_review(self):
        if not self.pending:
            return
        self.review_frame.pack(fill="x", padx=10, pady=5, before=self.log_box)
        self.show_file(0)

    def show_file(self, index):
        if not self.pending:
            return
        # Save whatever was selected for the file we're leaving.
        cur_path = self.pending[self.review_index]["path"]
        self.selections[cur_path] = self.candidate_var.get()

        index = max(0, min(index, len(self.pending) - 1))
        self.review_index = index
        item = self.pending[index]
        path, candidates = item["path"], item["candidates"]

        self.review_label.config(text=f"File {index + 1} of {len(self.pending)}: {os.path.basename(path)}")
        for w in self.candidates_frame.winfo_children():
            w.destroy()

        default = self.selections.get(path, 0 if candidates else -1)
        self.candidate_var = tk.IntVar(value=default)

        if not candidates:
            ttk.Label(self.candidates_frame, text="No matches found for this file.").pack(anchor="w")
        for i, c in enumerate(candidates):
            label = (
                f"{c.get('artist', '?')} - {c.get('title', '?')}  "
                f"({c.get('album', '?')}, {c.get('date', '?')})  [{c.get('_source', '?')}]"
            )
            ttk.Radiobutton(self.candidates_frame, text=label, variable=self.candidate_var, value=i).pack(anchor="w")
        ttk.Radiobutton(self.candidates_frame, text="Skip this file (don't tag it)",
                         variable=self.candidate_var, value=-1).pack(anchor="w")

        self.back_button.config(state=("normal" if index > 0 else "disabled"))
        self.next_button.config(state=("normal" if index < len(self.pending) - 1 else "disabled"))

    # --- Phase 3: apply whatever was picked ---

    def start_apply(self):
        if self.pending:
            cur_path = self.pending[self.review_index]["path"]
            self.selections[cur_path] = self.candidate_var.get()
        self.apply_button.config(state="disabled", text="Working...")
        threading.Thread(target=self.run_apply, daemon=True).start()

    def run_apply(self):
        results = []
        for item in self.pending:
            path, candidates = item["path"], item["candidates"]
            choice = self.selections.get(path, 0 if candidates else -1)
            meta = candidates[choice] if 0 <= choice < len(candidates) else None
            self.logmsg(f"Applying: {path}")
            outcome = core.apply_candidate(
                path, meta, self.pattern_var.get(), self.folder_var.get(),
                self.dryrun_var.get(), self.nocover_var.get(),
                bpm_api_key=self.bpmkey_var.get() or None, log=self.logmsg,
            )
            outcome["path"] = path
            results.append(outcome)

        report_path = core.write_report(self.folder_var.get(), results, self.dryrun_var.get())
        tagged = sum(1 for r in results if r["status"] == "tagged")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        errors = sum(1 for r in results if r["status"] == "error")
        self.logmsg(f"\nDone. Tagged: {tagged}   Skipped: {skipped}   Errors: {errors}")
        self.logmsg(f"Full report saved to: {report_path}")
        self.apply_button.config(state="normal", text="Apply All & Tag Files")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()

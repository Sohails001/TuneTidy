"""Minimal cross-platform Tkinter GUI for TuneTidy."""
import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

from . import cli as core


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TuneTidy")
        self.geometry("680x500")

        self.folder_var = tk.StringVar()
        self.pattern_var = tk.StringVar(value="{artist}/{album}/{track} - {title}")
        self.apikey_var = tk.StringVar(value=os.environ.get("ACOUSTID_API_KEY", ""))
        self.dryrun_var = tk.BooleanVar(value=True)
        self.nocover_var = tk.BooleanVar(value=False)

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="x")

        ttk.Label(frm, text="Music folder:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.folder_var, width=55).grid(row=0, column=1)
        ttk.Button(frm, text="Browse", command=self.browse).grid(row=0, column=2, padx=4)

        ttk.Label(frm, text="AcoustID API key:").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.apikey_var, width=55).grid(row=1, column=1, columnspan=2, sticky="w")

        ttk.Label(frm, text="Naming pattern:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.pattern_var, width=55).grid(row=2, column=1, columnspan=2, sticky="w")

        ttk.Checkbutton(frm, text="Dry run (preview only)", variable=self.dryrun_var).grid(row=3, column=0, sticky="w")
        ttk.Checkbutton(frm, text="Skip cover art", variable=self.nocover_var).grid(row=3, column=1, sticky="w")

        self.start_button = ttk.Button(frm, text="Start", command=self.start)
        self.start_button.grid(row=4, column=1, pady=8)

        self.log_box = scrolledtext.ScrolledText(self, height=22)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def browse(self):
        d = filedialog.askdirectory()
        if d:
            self.folder_var.set(d)

    def logmsg(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.update_idletasks()

    def start(self):
        folder = self.folder_var.get()
        if not folder:
            self.logmsg("Please choose a folder first.")
            return
        # Prevent a second click while a scan is already running - previously
        # this could silently launch a duplicate overlapping scan.
        self.start_button.config(state="disabled", text="Working...")
        threading.Thread(target=self.run_scan, args=(folder,), daemon=True).start()

    def run_scan(self, folder):
        files = list(core.find_audio_files(folder))
        self.logmsg(f"Found {len(files)} audio file(s).")
        for f in files:
            core.process_file(
                f,
                self.apikey_var.get() or None,
                self.pattern_var.get(),
                folder,
                self.dryrun_var.get(),
                self.nocover_var.get(),
                log=self.logmsg,
            )
        self.logmsg("Done.")
        self.start_button.config(state="normal", text="Start")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()

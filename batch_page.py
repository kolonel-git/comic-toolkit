"""Scaffold for folder tools that run one job per item and log each result."""
import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from comic_core import COMIC_EXT, common_root, picked_files
from ui_kit import ACCENT, BORDER, FONT, PANEL, TEXT, DropZone, Page, button, divider, title_block

MARKS = {"ok": "✓", "skip": "↷", "fail": "✗"}


def _worker(q, page, items, o, dry, stop):
    for k, item in enumerate(items):
        if stop.is_set():
            q.put(("stopped",))
            return
        q.put(("start", k, len(items)))
        try:
            kind, text = page.work(item, o, dry)
        except Exception as e:  # noqa: BLE001 - one bad file must not stop the batch
            kind, text = "fail", f"{page.label(item)}  {e}"
        q.put(("line", kind, text))
    q.put(("done",))


class BatchPage(Page):
    """Subclasses set title/subtitle/noun/run_label, add options to self.form, and implement
    scan(folder, options) -> items, label(item) -> str and work(item, options, dry) -> (kind, text)
    where kind is 'ok' | 'skip' | 'fail'. work() runs on a worker thread: no Tk calls in it."""
    title = subtitle = ""
    noun = "file"
    run_label = "Run"
    drop_prompt = "Drop a folder here, or add a folder or comics below"
    pick_ext = COMIC_EXT  # what 'Choose comics' accepts

    def __init__(self, parent):
        super().__init__(parent)
        self.folder = None
        self.picked = None  # files chosen one by one instead of a folder (None = scan the folder)
        self.items = []
        self.q = None
        self.stop = threading.Event()
        self.dry = False

        title_block(self.main, self.title, self.subtitle)
        self.drop = DropZone(self.main, self.drop_prompt, self.browse, self.browse, self.browse_files)
        self.drop.pack(fill="x")
        self.meta = ctk.CTkLabel(self.main, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(16, 8))
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER,
                                           progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 10))
        self.log = ctk.CTkTextbox(self.main, font=("Consolas", 12), fg_color=PANEL, text_color=TEXT,
                                  border_color=BORDER, border_width=1, corner_radius=8, wrap="none")
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        self.btn_run = button(self.footer, self.run_label, lambda: self.start(False), primary=True)
        self.btn_run.pack(pady=(0, 8))
        self.btn_preview = button(self.footer, "Preview changes", lambda: self.start(True))
        self.btn_preview.pack(pady=(0, 8))
        divider(self.footer, vertical=False).pack(fill="x", pady=(2, 10))
        self.btn_open = button(self.footer, "Open folder", self.open_folder)
        self.btn_open.pack()
        self.btn_stop = button(self.footer, "Stop", self.stop.set)
        self.actions = [self.btn_run, self.btn_preview]
        self._idle()

    # --- hooks ---
    def scan(self, folder, o):
        raise NotImplementedError

    def label(self, item):
        return str(item)

    def work(self, item, o, dry):
        raise NotImplementedError

    def pick_items(self, files, o):
        """Items for files chosen one by one (the counterpart of scan() for a folder)."""
        raise NotImplementedError

    def validate(self, o):
        """Return an error message to block a run, or None."""
        return None

    def found_text(self, n):
        return f"{n} {self.noun}{'s' if n != 1 else ''} found"

    def rel(self, p):
        try:
            return str(Path(p).relative_to(self.folder))
        except ValueError:
            return str(p)

    # --- folder ---
    def browse(self):
        d = filedialog.askdirectory(title="Choose a folder")
        if d:
            self.set_folder(d)

    def browse_files(self):
        exts = " ".join("*" + e for e in sorted(self.pick_ext))
        files = filedialog.askopenfilenames(title="Choose comics", filetypes=[("Comics", exts), ("All", "*.*")])
        if files:
            self.set_files(files)

    def set_files(self, paths):
        """Work on these comics instead of a whole folder."""
        files = picked_files(paths, self.pick_ext)
        if not files:
            self.say("None of those files can be used by this tool.", err=True)
            return
        self.picked = files
        self.folder = common_root(files)
        self.drop.set(f"{len(files)} file{'s' if len(files) != 1 else ''} chosen from {self.folder}")
        self._log(None)
        self.say("")
        self.rescan()

    def set_folder(self, folder):
        self.folder = Path(folder)
        self.picked = None
        self.drop.set(str(self.folder))
        self._log(None)
        self.say("")
        self.rescan()

    def rescan(self):
        if not self.folder or self.q:
            return
        o = self.state()
        self.items = self.pick_items(self.picked, o) if self.picked is not None else self.scan(self.folder, o)
        self.meta.configure(text=self.found_text(len(self.items)))
        self._idle()

    def open_folder(self):
        if self.folder and self.folder.exists():
            os.startfile(self.folder)  # Windows

    # --- running ---
    def _idle(self):
        ready = bool(self.items) and not self.q
        for b in self.actions:
            b.configure(state="normal" if ready else "disabled")
        self.btn_open.configure(state="normal" if self.folder else "disabled")
        self.btn_stop.pack_forget()

    def start(self, dry):
        o = self.state()
        err = self.validate(o)
        if err:
            self.say(err, err=True)
            return
        if not self.items:
            self.say(f"Pick a folder that contains {self.noun}s.", err=True)
            return
        self.dry = dry
        self.counts = {"ok": 0, "skip": 0, "fail": 0}
        self.stop.clear()
        self.q = queue.Queue()
        self._log(None)
        self.say("")
        self.progress.set(0)
        for b in self.actions:
            b.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_stop.pack(pady=(8, 0))
        threading.Thread(target=_worker, args=(self.q, self, list(self.items), o, dry, self.stop),
                         daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(50):
                msg = self.q.get_nowait()
                if msg[0] == "start":
                    self.progress.set(msg[1] / msg[2])
                    self.say(f"{msg[1] + 1} of {msg[2]}")
                elif msg[0] == "line":
                    self.counts[msg[1]] += 1
                    mark = "•" if self.dry and msg[1] == "ok" else MARKS[msg[1]]
                    self._log(f"{mark}  {msg[2]}")
                else:
                    self._finish(msg[0] == "stopped")
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish(self, stopped):
        self.q = None
        c = self.counts
        parts = [f"{c['ok']} {'would change' if self.dry else 'done'}"]
        if c["skip"]:
            parts.append(f"{c['skip']} skipped")
        if c["fail"]:
            parts.append(f"{c['fail']} failed")
        lead = "Stopped · " if stopped else "Preview · " if self.dry else "Done · "
        self.progress.set(0 if stopped else 1)
        self.say(lead + ", ".join(parts), err=bool(c["fail"]))
        if not self.dry:
            self.rescan()  # counts change after a real run
        self._idle()

    def _log(self, line):
        self.log.configure(state="normal")
        if line is None:
            self.log.delete("1.0", "end")
        else:
            self.log.insert("end", line + "\n")
            self.log.see("end")
        self.log.configure(state="disabled")

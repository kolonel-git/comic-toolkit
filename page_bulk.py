"""Bulk folder page: covers from every CBZ/CBR in a folder, organised how you like."""
import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from comic_core import (COMIC_EXT, CONFLICTS, FORMATS, HEIGHTS, NAMES, ORG_FLAT, ORG_MIRROR, ORG_SERIES, ORGS,
                        WHERE_BESIDE, WHERE_CUSTOM, WHERE_SUB, WHERES, Comic, export_cover,
                        common_root, find_comics, picked_files, plan_dest, sanitize, series_name)
from ui_kit import (ACCENT, BORDER, FONT, MUTED, PANEL, TEXT, DropZone, Form, Page, button, entry, menu,
                    switch_style, title_block, divider)


def _worker(q, files, root, o, stop):
    used = set()
    for k, src in enumerate(files):
        if stop.is_set():
            q.put(("stopped",))
            return
        q.put(("start", k, len(files)))
        comic = None
        try:
            comic = Comic(src)
            status, dest = export_cover(comic, root, o, used)
            q.put((status, src, dest))
        except Exception as e:  # noqa: BLE001 - one bad file must not stop the batch
            q.put(("failed", src, str(e)))
        finally:
            if comic:
                comic.close()
    q.put(("done",))


class BulkPage(Page):
    defaults = {"recursive": True, "where": WHERE_SUB, "subfolder": "Covers", "custom": "",
                "organize": ORG_FLAT, "format": "Original", "quality": 90, "height": "Original size",
                "name": NAMES[0], "conflict": "Overwrite"}
    choices = {"where": WHERES, "organize": ORGS, "format": FORMATS, "height": list(HEIGHTS),
               "name": NAMES, "conflict": CONFLICTS}

    def __init__(self, parent):
        super().__init__(parent)
        self.folder = None
        self.picked = None  # comics chosen one by one instead of a folder
        self.files = []
        self.q = None
        self.stop = threading.Event()
        self.out_dir = None

        title_block(self.main, "Bulk folder", "Pull the cover from every CBZ and CBR in a folder.")
        self.drop = DropZone(self.main, "Drop a folder here, or add a folder or comics below", self.browse,
                             self.browse, self.browse_files)
        self.drop.pack(fill="x")
        self.meta = ctk.CTkLabel(self.main, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(16, 0))
        self.example = ctk.CTkLabel(self.main, text="", font=(FONT, 12), text_color=MUTED, anchor="w")
        self.example.pack(fill="x", pady=(2, 10))
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER,
                                           progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 10))
        self.log = ctk.CTkTextbox(self.main, font=("Consolas", 12), fg_color=PANEL, text_color=TEXT,
                                  border_color=BORDER, border_width=1, corner_radius=8, wrap="none")
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        v = self.vars
        self.form.heading("Source")
        ctk.CTkSwitch(self.form.add("Subfolders"), text="Include subfolders", variable=v["recursive"],
                      **switch_style()).pack(anchor="w")
        self.form.heading("Cover image")
        self.add_image_rows()
        self.form.heading("Output")
        menu(self.form.add("Save covers to"), v["where"], WHERES).pack(fill="x")
        self.sub_row = self.form.add("Subfolder name")
        entry(self.sub_row, v["subfolder"]).pack(fill="x")
        self.custom_row = self.form.add("Folder")
        self.path_row(self.custom_row, v["custom"], "Save covers to")
        self.org_row = self.form.add("Organise covers")
        menu(self.org_row, v["organize"], ORGS).pack(fill="x")
        menu(self.form.add("File name"), v["name"], NAMES).pack(fill="x")
        menu(self.form.add("If the file exists"), v["conflict"], CONFLICTS).pack(fill="x")

        self.btn_start = button(self.footer, "Extract covers", self.start, primary=True)
        self.btn_start.pack(pady=(0, 8))
        divider(self.footer, vertical=False).pack(fill="x", pady=(2, 10))
        self.btn_open = button(self.footer, "Open output folder", self.open_out)
        self.btn_open.pack()
        self.btn_open.configure(state="disabled")

        self.watch("recursive", callback=self.rescan)
        self.watch("where", "subfolder", "custom", "organize", "format", "name", callback=self.refresh)
        self.refresh()

    # --- state / preview ---
    def browse(self):
        d = filedialog.askdirectory(title="Folder of CBZ / CBR files")
        if d:
            self.set_folder(d)

    def browse_files(self):
        files = filedialog.askopenfilenames(title="Choose comics", filetypes=[
            ("Comic archives", "*.cbz *.cbr"), ("All", "*.*")])
        if files:
            self.set_files(files)

    def set_files(self, paths):
        """Take the covers of these comics only, instead of a whole folder."""
        files = picked_files(paths, COMIC_EXT)
        if not files:
            self.say("None of those files are .cbz or .cbr comics.", err=True)
            return
        self.picked = files
        self.folder = common_root(files)
        self.drop.set(f"{len(files)} comic{'s' if len(files) != 1 else ''} chosen from {self.folder}")
        self.say("")
        self.rescan()

    def set_folder(self, folder):
        self.folder = Path(folder)
        self.picked = None
        self.drop.set(str(self.folder))
        self.rescan()

    def rescan(self):
        if self.picked is not None:
            self.files = [p for p in self.picked if p.exists()]
        else:
            self.files = find_comics(self.folder, self.vars["recursive"].get()) if self.folder else []
        self.refresh()

    def options(self):
        return self.state()

    def refresh(self):
        v = self.vars
        where, org = v["where"].get(), v["organize"].get()
        self.refresh_quality()
        Form.show(self.sub_row, where == WHERE_SUB)
        Form.show(self.custom_row, where == WHERE_CUSTOM)
        Form.show(self.org_row, where != WHERE_BESIDE)
        n = len(self.files)
        if not self.folder:
            self.meta.configure(text="")
            self.example.configure(text="")
            return
        text = f"{n} comic{'s' if n != 1 else ''} {'chosen' if self.picked is not None else 'found'}"
        if n and where != WHERE_BESIDE:
            if org == ORG_SERIES:
                k = len({series_name(p.stem) for p in self.files})
                text += f" · {k} series folder{'s' if k != 1 else ''}"
            elif org == ORG_MIRROR:
                k = len({p.parent for p in self.files})
                text += f" · {k} folder{'s' if k != 1 else ''}"
        self.meta.configure(text=text)
        self.example.configure(text=self._example())

    def _example(self):
        if not self.files:
            return ""
        o = self.options()
        if o["where"] == WHERE_CUSTOM and not o["custom"].strip():
            return "Choose a folder to save to."
        ext = {"JPG": ".jpg", "PNG": ".png", "WebP": ".webp"}.get(o["format"], ".jpg")
        dest = plan_dest(self.files[0], self.folder, o, ext)
        try:
            dest = dest.relative_to(self.folder)
        except ValueError:
            pass
        return f"Example:  {dest}"

    # --- run ---
    def start(self):
        if self.q:  # running: this button is "Stop"
            self.stop.set()
            self.btn_start.configure(state="disabled", text="Stopping…")
            return
        o = self.options()
        if not self.folder or not self.files:
            self.say("Pick a folder that contains .cbz or .cbr files.", err=True)
            return
        if o["where"] == WHERE_CUSTOM and not o["custom"].strip():
            self.say("Choose a folder to save covers to.", err=True)
            return
        self.out_dir = {WHERE_SUB: self.folder / sanitize(o["subfolder"]),
                        WHERE_CUSTOM: Path(o["custom"]), WHERE_BESIDE: self.folder}[o["where"]]
        self.counts = {"saved": 0, "skipped": 0, "failed": 0}
        self.stop.clear()
        self.q = queue.Queue()
        self._log(None)
        self.say("")
        self.progress.set(0)
        self.btn_start.configure(text="Stop")
        self.btn_open.configure(state="disabled")
        threading.Thread(target=_worker, args=(self.q, list(self.files), self.folder, o, self.stop),
                         daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(50):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "start":
                    self.progress.set(msg[1] / msg[2])
                    self.say(f"{msg[1] + 1} of {msg[2]}")
                elif kind in ("saved", "skipped"):
                    self.counts[kind] += 1
                    mark = "✓" if kind == "saved" else "↷"
                    self._log(f"{mark}  {msg[1].name}  →  {self._shorten(msg[2])}")
                elif kind == "failed":
                    self.counts["failed"] += 1
                    self._log(f"✗  {msg[1].name}  {msg[2]}")
                else:
                    self._finish(kind == "stopped")
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _shorten(self, p):
        try:
            return str(p.relative_to(self.folder))
        except ValueError:
            return str(p)

    def _finish(self, stopped):
        self.q = None
        c = self.counts
        parts = [f"{c['saved']} saved"]
        if c["skipped"]:
            parts.append(f"{c['skipped']} skipped")
        if c["failed"]:
            parts.append(f"{c['failed']} failed")
        self.progress.set(0 if stopped else 1)
        self.say(("Stopped · " if stopped else "Done · ") + ", ".join(parts), err=bool(c["failed"]))
        self.btn_start.configure(state="normal", text="Extract covers")
        self.btn_open.configure(state="normal" if self.out_dir and self.out_dir.exists() else "disabled")

    def _log(self, line):
        self.log.configure(state="normal")
        if line is None:
            self.log.delete("1.0", "end")
        else:
            self.log.insert("end", line + "\n")
            self.log.see("end")
        self.log.configure(state="disabled")

    def open_out(self):
        if self.out_dir and self.out_dir.exists():
            os.startfile(self.out_dir)  # Windows

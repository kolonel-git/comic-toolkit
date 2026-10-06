"""Metadata page: stamp series/issue/volume/year/title from filenames into each CBZ's ComicInfo.xml,
with a review table you can edit before anything is written."""
import queue
import re
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from archive_tools import BACKUP, REPLACE, apply_metadata
from comic_core import in_archive, natural_key
from rename_core import parse_filename, read_comicinfo
from ui_kit import (ACCENT, BG, BORDER, FONT, MUTED, PANEL, TEXT, DropZone, Page, apply_tree_theme, build_tree,
                    button, menu, pick, switch_style, title_block)

FILL, OVERWRITE = "Fill in missing fields only", "Overwrite with filename values"
FIELDS = ("series", "issue", "volume", "year", "title")
LABELS = {"series": "Series", "issue": "Issue number", "volume": "Volume", "year": "Year", "title": "Title"}
EDITABLE = {"#3": "series", "#4": "issue", "#5": "volume", "#6": "year"}
NO_CHANGE = "No change"


def clean(field_, value):
    """Normalise a value before it goes into ComicInfo.xml ('012' -> '12')."""
    value = (value or "").strip()
    if field_ == "issue":
        m = re.fullmatch(r"0*(\d+)(\.\d+)?", value)
        if m:
            return m.group(1) + (m.group(2) or "")
    return value


@dataclass
class Row:
    path: Path
    parsed: dict
    ci: dict
    edits: dict = field(default_factory=dict)  # values typed in the table
    writes: dict = field(default_factory=dict)  # what will actually be written
    checked: bool = True
    status: str = ""
    iid: str = ""


def _scan(q, files):
    for k, p in enumerate(files):
        q.put(("row", Row(p, parse_filename(p.stem), read_comicinfo(p)), k + 1, len(files)))
    q.put(("done",))


def _apply(q, rows, backup):
    for k, r in enumerate(rows):
        q.put(("start", k, len(rows)))
        try:
            apply_metadata(r.path, r.writes, backup)
            q.put(("ok", r))
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            q.put(("fail", r, str(e)))
    q.put(("finished",))


class MetadataPage(Page):
    defaults = {"recursive": True, "w_series": True, "w_issue": True, "w_volume": True, "w_year": True,
                "w_title": True, "existing": FILL, "folder_series": True, "original": BACKUP}
    choices = {"existing": [FILL, OVERWRITE], "original": [BACKUP, REPLACE]}

    def __init__(self, parent):
        super().__init__(parent)
        self.root_dir = None
        self.rows, self.by_iid = [], {}
        self.skipped_cbr = 0
        self.q = None
        self.busy = None  # 'scan' | 'apply'
        self._pending = False
        self._editor = None

        title_block(self.main, "Metadata", "Write series and issue info from filenames into ComicInfo.xml.")
        self.drop = DropZone(self.main, "Drop a folder here, or click to browse", self.browse)
        self.drop.pack(fill="x")
        bar = ctk.CTkFrame(self.main, fg_color=BG)
        bar.pack(fill="x", pady=(14, 6))
        self.meta = ctk.CTkLabel(bar, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(side="left")
        for text, val in (("Select none", False), ("Select all", True)):
            ctk.CTkButton(bar, text=text, width=84, height=26, corner_radius=6, font=(FONT, 12), fg_color=BG,
                          hover_color=PANEL, text_color=TEXT, border_width=1, border_color=BORDER,
                          command=lambda v=val: self.select_all(v)).pack(side="right", padx=(6, 0))
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER,
                                           progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        wrap, self.tree = build_tree(self.main, [
            ("sel", "", 38, False), ("file", "File", 170, True), ("series", "Series", 130, True),
            ("issue", "#", 52, False), ("volume", "Vol", 44, False), ("year", "Year", 56, False),
            ("status", "Status", 78, False)])
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<Double-1>", self._edit)
        ctk.CTkLabel(self.main, text="Double-click Series, #, Vol or Year to correct a value.", font=(FONT, 12),
                     text_color=MUTED, anchor="w").pack(fill="x", pady=(6, 0))

        v = self.vars
        sw = switch_style()
        box = self.form.add("Files")
        ctk.CTkSwitch(box, text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        box = self.form.add("Fields to write")
        for i, f in enumerate(FIELDS):
            ctk.CTkSwitch(box, text=LABELS[f], variable=v["w_" + f], **sw).pack(anchor="w", pady=(0 if i == 0 else 8, 0))
        menu(self.form.add("Existing values"), v["existing"], [FILL, OVERWRITE]).pack(fill="x")
        ctk.CTkSwitch(self.form.add("Missing series"), text="Use the folder name", variable=v["folder_series"],
                      **sw).pack(anchor="w")
        menu(self.form.add("Original file"), v["original"], [BACKUP, REPLACE]).pack(fill="x")

        self.btn_apply = button(self.footer, "Write metadata", self.apply, primary=True)
        self.btn_apply.pack(pady=(0, 8))
        self.btn_scan = button(self.footer, "Rescan folder", self.rescan)
        self.btn_scan.pack()
        self._buttons(False)
        self.watch("recursive", callback=self.rescan)
        self.watch("existing", "folder_series", *("w_" + f for f in FIELDS), callback=self.recompute)

    # --- theme ---
    def apply_theme(self):
        self._close_editor(False)
        apply_tree_theme(self.tree)

    # --- scan ---
    def browse(self):
        d = filedialog.askdirectory(title="Folder of comics")
        if d:
            self.set_folder(d)

    def set_folder(self, folder):
        self.root_dir = Path(folder)
        self.drop.set(str(self.root_dir))
        self.rescan()

    def _buttons(self, settled):
        self.btn_apply.configure(state="disabled")
        self.btn_scan.configure(state="normal" if settled and self.root_dir else "disabled")

    def rescan(self):
        if not self.root_dir:
            return
        if self.busy:
            self._pending = True
            return
        self._close_editor(False)
        self.tree.delete(*self.tree.get_children())
        self.rows, self.by_iid = [], {}
        it = self.root_dir.rglob("*") if self.vars["recursive"].get() else self.root_dir.iterdir()
        everything = [p for p in it if p.is_file() and not in_archive(p, self.root_dir)]
        files = sorted((p for p in everything if p.suffix.lower() == ".cbz"),
                       key=lambda p: natural_key(p.relative_to(self.root_dir)))
        self.skipped_cbr = sum(1 for p in everything if p.suffix.lower() == ".cbr")
        self.say("")
        if not files:
            self.meta.configure(text="No .cbz files found" + self._cbr_note())
            self._buttons(True)
            return
        self.meta.configure(text=f"Reading {len(files)} files…")
        self.progress.set(0)
        self._buttons(False)
        self.busy, self.q = "scan", queue.Queue()
        threading.Thread(target=_scan, args=(self.q, files), daemon=True).start()
        self._poll()

    def _cbr_note(self):
        return f" · {self.skipped_cbr} .cbr skipped (convert first)" if self.skipped_cbr else ""

    # --- polling for both scan and apply ---
    def _poll(self):
        try:
            for _ in range(100):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "row":
                    row = msg[1]
                    self.rows.append(row)
                    self._compute(row)
                    row.iid = self.tree.insert("", "end", values=self._values(row), tags=self._tags(row))
                    self.by_iid[row.iid] = row
                    self.progress.set(msg[2] / msg[3])
                elif kind == "done":
                    self._end_scan()
                    return
                elif kind == "start":
                    self.progress.set(msg[1] / msg[2])
                    self.say(f"Writing {msg[1] + 1} of {msg[2]}")
                elif kind == "ok":
                    self.applied += 1
                elif kind == "fail":
                    self.failed.append(f"{msg[1].path.name}: {msg[2]}")
                else:  # finished applying
                    self._end_apply()
                    return
        except queue.Empty:
            pass
        self.after(40, self._poll)

    def _end_scan(self):
        self.busy = self.q = None
        self.progress.set(0)
        self._buttons(True)
        self._resolve()
        if self._pending:
            self._pending = False
            self.rescan()

    def _end_apply(self):
        self.busy = self.q = None
        text = f"Updated {self.applied} file{'s' if self.applied != 1 else ''}"
        if self.failed:
            text += f" · {len(self.failed)} failed ({self.failed[0]})"
        self.rescan()
        self.say(text, err=bool(self.failed))

    # --- values ---
    def _compute(self, row):
        o = self.state()
        writes = {}
        for f in FIELDS:
            if not o["w_" + f]:
                continue
            manual = f in row.edits
            value = clean(f, row.edits[f] if manual else row.parsed.get(f))
            if f == "series" and not value and o["folder_series"] and row.path.parent != self.root_dir:
                value = row.path.parent.name
            if not value:
                continue
            existing = row.ci.get(f)
            if existing and not manual and o["existing"] == FILL:
                continue
            if existing and clean(f, existing) == value:
                continue
            writes[f] = value
        row.writes = writes
        row.status = NO_CHANGE if not writes else "Update" if row.ci else "Add"

    def _shown(self, row, f):
        return row.writes.get(f) or row.ci.get(f) or ""

    def _values(self, row):
        return ("☑" if row.checked else "☐", row.path.name, *(self._shown(row, f) for f in
                ("series", "issue", "volume", "year")), row.status)

    def _tags(self, row):
        return ("dim",) if row.status == NO_CHANGE else ()

    def _refresh(self, row):
        self.tree.item(row.iid, values=self._values(row), tags=self._tags(row))

    def recompute(self):
        if self.busy or not self.rows:
            return
        for r in self.rows:
            self._compute(r)
        self._resolve()

    def _resolve(self):
        for r in self.rows:
            self._refresh(r)
        ready = sum(1 for r in self.rows if r.checked and r.writes)
        self.meta.configure(text=f"{len(self.rows)} files · {ready} to update" + self._cbr_note())
        self.btn_apply.configure(state="normal" if ready and not self.busy else "disabled")

    def select_all(self, value):
        for r in self.rows:
            r.checked = value
        self._resolve()

    # --- table interaction ---
    def _click(self, e):
        if self.tree.identify_region(e.x, e.y) == "cell" and self.tree.identify_column(e.x) == "#1":
            row = self.by_iid.get(self.tree.identify_row(e.y))
            if row:
                row.checked = not row.checked
                self._resolve()
                return "break"
        return None

    def _edit(self, e):
        iid, col = self.tree.identify_row(e.y), self.tree.identify_column(e.x)
        if not iid or col not in EDITABLE or self.busy:
            return
        self._close_editor(False)
        row, f = self.by_iid[iid], EDITABLE[col]
        x, y, w, h = self.tree.bbox(iid, col)
        ed = tk.Entry(self.tree, font=(FONT, 11), relief="flat", bd=0, highlightthickness=1,
                      highlightbackground=pick(ACCENT), highlightcolor=pick(ACCENT), fg=pick(TEXT),
                      bg=pick(BG), insertbackground=pick(TEXT))
        ed.insert(0, self._shown(row, f))
        ed.select_range(0, "end")
        ed.place(x=x, y=y, width=w, height=h)
        ed.focus_set()
        ed.bind("<Return>", lambda _: self._close_editor(True))
        ed.bind("<Escape>", lambda _: self._close_editor(False))
        ed.bind("<FocusOut>", lambda _: self._close_editor(True))
        self._editor = (ed, row, f)

    def _close_editor(self, commit):
        if not self._editor:
            return
        ed, row, f = self._editor
        self._editor = None
        text = ed.get().strip()
        ed.destroy()
        if commit and text != self._shown(row, f):
            row.edits[f] = text
            self._compute(row)
            self._resolve()

    # --- apply ---
    def apply(self):
        self._close_editor(True)
        todo = [r for r in self.rows if r.checked and r.writes]
        if not todo:
            return
        backup = self.vars["original"].get() == BACKUP
        msg = f"Write metadata into {len(todo)} file{'s' if len(todo) != 1 else ''}?\n\n"
        msg += "Originals are kept in an Archive folder." if backup else "Files are replaced in place."
        if not messagebox.askyesno("Write metadata", msg, icon="warning"):
            return
        self.applied, self.failed = 0, []
        self.busy, self.q = "apply", queue.Queue()
        self._buttons(False)
        self.btn_apply.configure(state="disabled")
        threading.Thread(target=_apply, args=(self.q, todo, backup), daemon=True).start()
        self._poll()

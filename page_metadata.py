"""Metadata page: repair the details stored inside comics (ComicInfo.xml). Two columns side by side. Left: the comics
(a table showing what each comic holds and what is missing). Right: the fields of the comics selected on the left, which
follow the selection at once (one at a time or several together, with suggestions taken from the other comics in the
library), and below them, as you scroll, every change waiting to be saved. Nothing is written until you confirm."""
import io
import queue
import threading
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageTk

import metadata_core as mc
from archive_tools import BACKUP, REPLACE, apply_metadata
from comic_core import COMIC_EXT, common_root, in_archive, is_page, natural_key, picked_files
from flow_kit import Advanced, LazyTable, SegmentPage
from rename_core import parse_filename, read_comicinfo
from ui_kit import (BG, BORDER, DANGER, EDGE, FONT, HEAD, MUTED, PANEL, SCROLL, TEXT, TYPE_BODY, TYPE_HINT, TYPE_SEGMENT, DropZone,
                    Toggle, entry, menu, button, pick, segmented, switch_style, tool_button, tooltip)

AUTO, ONE, MANY = "Automatic", "One at a time", "Several at once"   # automatic follows how many comics are selected
VIEWS = list(mc.FILTERS.values())
KEY_OF = {v: k for k, v in mc.FILTERS.items()}
SOURCE_WORDS = {"series": "used in the same series", "folder": "used in the same folder", "name": "read from the file name",
                "library": "used elsewhere in your library"}
DASH = "—"


def _scan(q, files, root):
    """Read the filename and ComicInfo.xml of every comic (a .cbr is listed but cannot be edited)."""
    for k, p in enumerate(files):
        locked = p.suffix.lower() != ".cbz"
        try:
            ci = {} if locked else read_comicinfo(p)
        except Exception:  # noqa: BLE001 - one unreadable file must not stop the list
            ci = {}
        q.put(("row", mc.Row(p, parse_filename(p.stem), ci, locked), k + 1, len(files)))
    q.put(("done",))


def _apply(q, rows, backup):
    for k, r in enumerate(rows):
        q.put(("start", k, len(rows)))
        try:
            apply_metadata(r.path, mc.writes(r), backup)
            q.put(("ok", r))
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            q.put(("fail", r, str(e)))
    q.put(("finished",))


def _plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


class MetadataPage(SegmentPage):
    title = "Metadata"
    subtitle = "Fill in and correct the details stored inside your comics."
    defaults = {"recursive": True, "view": VIEWS[0], "original": BACKUP}
    choices = {"view": VIEWS, "original": [BACKUP, REPLACE]}
    split = True
    show_auto = False
    max_width = 1500

    def __init__(self, parent):
        super().__init__(parent)
        self.open_tool = None          # the app gives a function opening another tool (the .cbr converter)
        self.on_saved = None           # the app listens, so Library stats can refresh
        self.root_dir = None
        self.picked = None             # comics chosen one by one instead of a folder
        self.rows, self.shown, self.index = [], [], {}
        self.sugg = mc.SuggestIndex([])
        self.q = None
        self.busy = None               # 'scan' | 'apply'
        self.progress_text = ""
        self.loading = []
        self._filling = False
        self._pending_view = None
        self._review_job = None
        self._dirty, self._flush_job = [], None   # rows edited by typing, redrawn together once typing pauses
        self.mode = ctk.StringVar(value=AUTO)     # which way of editing the user chose (not remembered between runs)
        self.selected_rows = []
        self.offer = None
        self.cover_image = None
        self.vars_one, self.vars_many = {}, {}
        self.chip_boxes = {}
        self.field_labels = {}
        v = self.vars

        # ---- left: the comics
        self.panes = ctk.CTkFrame(self.col, fg_color="transparent")
        self.panes.pack(fill="both", expand=True)
        self.panes.grid_columnconfigure(0, weight=5, uniform="pane", minsize=420)
        self.panes.grid_columnconfigure(1, weight=6, uniform="pane", minsize=480)
        self.panes.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(self.panes, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        head = ctk.CTkFrame(left, fg_color="transparent")
        head.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(head, text="Comics", font=TYPE_SEGMENT, text_color=TEXT, anchor="w").pack(side="left")
        self.left_summary = ctk.CTkLabel(head, text="", font=TYPE_BODY, text_color=MUTED, anchor="e")
        self.left_summary.pack(side="right")
        self.drop = DropZone(left, "Drop a folder here, or add a folder or comics", self.browse, self.browse,
                             self.browse_files)
        self.drop.pack(fill="x", padx=(0, 6), pady=(0, 10))
        bar = ctk.CTkFrame(left, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        Toggle(bar, text="Include subfolders", variable=v["recursive"], **switch_style()).pack(side="left")
        tool_button(bar, "Select all shown", self.select_shown, 130).pack(side="right", padx=(0, 6))
        bar = ctk.CTkFrame(left, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(bar, text="Show", font=TYPE_HINT, text_color=MUTED).pack(side="left", padx=(0, 8))
        menu(bar, v["view"], VIEWS, width=190).pack(side="left")
        self.origin_clear = tool_button(self.origin, "Show all comics", lambda: v["view"].set(VIEWS[0]), 140)
        self.status = ctk.CTkLabel(left, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=420)
        self.status.pack(side="bottom", fill="x", pady=(6, 0))
        self.yac_note = ctk.CTkLabel(left, text="YACReader shows this only after you turn on ComicInfo import (Settings > General) and "
                     "update the library.", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                     wraplength=420)
        self.yac_note.pack(side="bottom", fill="x", pady=(6, 0))
        self.cbr_note = ctk.CTkFrame(left, fg_color="transparent")
        self.cbr_label = ctk.CTkLabel(self.cbr_note, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                                      wraplength=260)
        self.cbr_label.pack(side="left")
        tool_button(self.cbr_note, "Convert them…", lambda: self._open("convert"), 130).pack(side="left", padx=(10, 0))
        self.comics = LazyTable(left, [
            ("dot", "", 30, False), ("file", "File", 200, True), ("series", "Series", 110, True), ("issue", "#", 44, False),
            ("volume", "Vol", 40, False), ("year", "Year", 50, False), ("publisher", "Publisher", 100, True),
            ("state", "", 96, False)], rows=8, grow=True,
            empty="Add a folder above to see what each comic holds and what is missing.")
        self.comics.pack(fill="both", expand=True)
        self.comics.tree.bind("<<TreeviewSelect>>", lambda _: self._selection_changed())

        # ---- right: the fields to edit, then every change waiting to be saved
        self.right = ctk.CTkScrollableFrame(self.panes, fg_color=BG, corner_radius=0, scrollbar_button_color=SCROLL,
                                            scrollbar_button_hover_color=MUTED)
        self.right.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(self.right, text="Edit", font=TYPE_SEGMENT, text_color=TEXT, anchor="w").pack(fill="x", pady=(0, 8))
        segmented(self.right, self.mode, [AUTO, ONE, MANY], width=440).pack(anchor="w", pady=(0, 8))
        self.target_label = ctk.CTkLabel(self.right, text="", font=(FONT, 13, "bold"), text_color=TEXT, anchor="w",
                                         justify="left", wraplength=560)
        self.target_label.pack(fill="x", pady=(4, 12))
        self.slot = ctk.CTkFrame(self.right, fg_color="transparent")   # holds the offer, the hint or a form
        self.slot.pack(fill="x")
        self.offer_box = ctk.CTkFrame(self.slot, fg_color=PANEL, border_color=BORDER, border_width=EDGE, corner_radius=0)
        self.offer_label = ctk.CTkLabel(self.offer_box, text="", font=TYPE_BODY, text_color=TEXT, anchor="w", justify="left",
                                        wraplength=380)
        self.offer_label.pack(side="left", padx=14, pady=10)
        tool_button(self.offer_box, "No", self._drop_offer, 60).pack(side="right", padx=(0, 10), pady=8)
        tool_button(self.offer_box, "Apply", self._take_offer, 80).pack(side="right", padx=(0, 6), pady=8)
        self.empty = ctk.CTkLabel(self.slot, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                                  wraplength=560)
        self._build_one()
        self._build_many()

        self.changes_box = ctk.CTkFrame(self.right, fg_color="transparent")
        self.changes_box.pack(fill="x", pady=(26, 0))
        ctk.CTkFrame(self.changes_box, height=EDGE, fg_color=BORDER, corner_radius=0).pack(fill="x", pady=(0, 14))
        self.review_head = ctk.CTkLabel(self.changes_box, text="", font=(HEAD, 16), text_color=TEXT, anchor="w")
        self.review_head.pack(fill="x", pady=(0, 8))
        self.review = LazyTable(self.changes_box, [("comic", "Comic", 220, True), ("field", "Field", 100, False),
                                                   ("old", "Was", 130, True), ("new", "Becomes", 130, True)], rows=8,
                                empty="Nothing to save yet. Changes you make above are listed here.")
        self.review.pack(fill="x")
        self.save_adv = Advanced(self.changes_box)
        self.save_adv.pack(fill="x", pady=(12, 0))
        row = ctk.CTkFrame(self.save_adv.body, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="Original file", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w").pack(fill="x", pady=(0, 4))
        menu(row, v["original"], [BACKUP, REPLACE]).pack(fill="x")
        self.save_adv.track(v, {"original": BACKUP})
        self.save_note = ctk.CTkLabel(self.changes_box, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                                      wraplength=560)
        self.save_note.pack(fill="x", pady=(16, 10))
        row = ctk.CTkFrame(self.changes_box, fg_color="transparent")
        row.pack(fill="x", pady=(0, 20))
        self.confirm_btn = button(row, "Confirm and save", self.apply, primary=True, width=260)
        self.confirm_btn.pack(side="left", padx=(0, 12))
        tool_button(row, "Discard edits", self.discard, 130).pack(side="left")

        self.watch("recursive", callback=self.rescan)
        self.watch("view", callback=self._view_changed)
        self.mode.trace_add("write", lambda *_: self._selection_changed())
        v["original"].trace_add("write", lambda *_: self._schedule_review())
        self._selection_changed()
        self._refresh_review()

    # ------------------------------------------------------------------ the two edit forms
    def _field_row(self, parent, name, var, many=False):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        label = ctk.CTkLabel(box, text=mc.LABELS[name], font=(FONT, 12, "bold"), text_color=MUTED, anchor="w")
        label.pack(fill="x", pady=(0, 5))
        self.field_labels[(many, name)] = label
        ent = entry(box, var)
        ent.pack(fill="x")
        chips = ctk.CTkFrame(box, fg_color="transparent", height=0)   # (height 0: an empty frame is 200 px tall otherwise)
        chips.pack(fill="x", pady=(6, 0))
        self.chip_boxes[(many, name)] = chips
        return box, ent

    def _build_one(self):
        self.one = ctk.CTkFrame(self.slot, fg_color="transparent")
        left = ctk.CTkFrame(self.one, fg_color="transparent")
        left.pack(side="left", anchor="n", padx=(0, 28))
        self.cover_box = tk.Frame(left, width=150, height=220, bd=0, highlightthickness=0)
        self.cover_box.pack_propagate(False)
        self.cover_box.pack()
        # (a plain Tk label, not a CustomTkinter one: those re-draw their picture on every theme change, even after
        # their window is gone)
        self.cover = tk.Label(self.cover_box, bd=0, font=TYPE_HINT)
        self.cover.place(relx=0.5, rely=0.5, anchor="center")
        self._cover_colors()
        nav = ctk.CTkFrame(left, fg_color="transparent")
        nav.pack(fill="x", pady=(12, 0))
        tool_button(nav, "◀ Previous", lambda: self._step(-1), 90).pack(side="left")
        tool_button(nav, "Next ▶", lambda: self._step(1), 70).pack(side="right")
        self.position = ctk.CTkLabel(left, text="", font=TYPE_HINT, text_color=MUTED)
        self.position.pack(pady=(8, 0))
        right = ctk.CTkFrame(self.one, fg_color="transparent")
        right.pack(side="left", fill="x", expand=True)
        self.file_label = ctk.CTkLabel(right, text="", font=(FONT, 13, "bold"), text_color=TEXT, anchor="w", wraplength=620,
                                       justify="left")
        self.file_label.pack(fill="x", pady=(0, 16))
        grid = ctk.CTkFrame(right, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure((0, 1), weight=1, uniform="one")
        self.one_entries = {}
        for n, name in enumerate(mc.MAIN):
            self.vars_one[name] = ctk.StringVar()
            box, ent = self._field_row(grid, name, self.vars_one[name])
            box.grid(row=n // 2, column=n % 2, sticky="ew", padx=(0, 20) if n % 2 == 0 else (0, 0), pady=(0, 20))
            self.one_entries[name] = ent
            self.vars_one[name].trace_add("write", lambda *_, n=name: self._typed(n))
            self._on_commit(ent, name)
        self.one_adv = Advanced(right)
        self.one_adv.pack(fill="x", pady=(0, 4))
        for name in mc.EXTRA:
            self.vars_one[name] = ctk.StringVar()
            box, ent = self._field_row(self.one_adv.body, name, self.vars_one[name])
            box.pack(fill="x", pady=(0, 18))
            self.one_entries[name] = ent
            self.vars_one[name].trace_add("write", lambda *_, n=name: self._typed(n))
            self._on_commit(ent, name)

    def _on_commit(self, ent, name):
        """Leaving a field, or pressing Enter in it, counts as finishing with it."""
        inner = getattr(getattr(ent, "inner", ent), "_entry", None)
        if inner is not None:
            inner.bind("<FocusOut>", lambda _, n=name: self._committed(n), "+")
            inner.bind("<Return>", lambda _, n=name: self._committed(n), "+")

    def _build_many(self):
        self.many = ctk.CTkFrame(self.slot, fg_color="transparent")
        ctk.CTkLabel(self.many, text="Fill in only the fields to change. A field left empty keeps what each comic already has.",
                     font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=800).pack(fill="x", pady=(0, 8))
        grid = ctk.CTkFrame(self.many, fg_color="transparent")
        grid.pack(fill="x")
        grid.grid_columnconfigure((0, 1), weight=1, uniform="many")
        self.many_entries = {}
        for n, name in enumerate(mc.MAIN):
            self.vars_many[name] = ctk.StringVar()
            box, ent = self._field_row(grid, name, self.vars_many[name], many=True)
            box.grid(row=n // 2, column=n % 2, sticky="ew", padx=(0, 20 if n % 2 == 0 else 0), pady=(0, 20))
            self.many_entries[name] = ent
        self.many_adv = Advanced(self.many)
        self.many_adv.pack(fill="x", pady=(4, 8))
        for name in mc.EXTRA:
            self.vars_many[name] = ctk.StringVar()
            box, ent = self._field_row(self.many_adv.body, name, self.vars_many[name], many=True)
            box.pack(fill="x", pady=(0, 18))
            self.many_entries[name] = ent
        row = ctk.CTkFrame(self.many_adv.body, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        tool_button(row, "Remove issue number", lambda: self.remove_issue(True), 170).pack(side="left", padx=(0, 8))
        tool_button(row, "Keep it again", lambda: self.remove_issue(False), 120).pack(side="left")
        ctk.CTkLabel(self.many_adv.body, text="YACReader sorts by issue number before file name. Removing the number makes it fall "
                     "back to the file name.", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                     wraplength=700).pack(fill="x", pady=(6, 0))
        bar = ctk.CTkFrame(self.many, fg_color="transparent")
        bar.pack(fill="x", pady=(8, 0))
        self.set_btn = tool_button(bar, "Set for 0 comics", self.set_many, 190)
        self.set_btn.pack(side="left", padx=(0, 10))
        tool_button(bar, "Fill blanks from file names", self.fill_blanks, 220).pack(side="left")

    # ------------------------------------------------------------------ choosing and reading comics
    def browse(self):
        d = filedialog.askdirectory(title="Folder of comics")
        if d:
            self.set_folder(d)

    def browse_files(self):
        files = filedialog.askopenfilenames(title="Choose comics", filetypes=[("Comic archives", "*.cbz *.cbr"), ("All", "*.*")])
        if files:
            self.set_files(files)

    def set_files(self, paths):
        """Work on these comics only, instead of a whole folder."""
        files = picked_files(paths, COMIC_EXT)
        if not files:
            self.say("None of those files are .cbz or .cbr comics.", err=True)
            return
        self.picked = files
        self.root_dir = common_root(files)
        self.drop.set(f"{_plural(len(files), 'comic')} chosen from {self.root_dir}")
        self.rescan()

    def set_folder(self, folder):
        self.root_dir = Path(folder)
        self.picked = None
        self.drop.set(str(self.root_dir))
        self.clear_origin()
        self.origin_clear.pack_forget()
        self.rescan()

    def open_with(self, folder, view=None, origin=None, back=None):
        """Open the library folder from another tool, already filtered to `view` (a key of FILTERS), with a chip saying
        where you came from and a Back button."""
        self.root_dir = Path(folder)
        self.picked = None
        self.drop.set(str(self.root_dir))
        self._pending_view = view
        if view and view in mc.FILTERS:
            self.vars["view"].set(mc.FILTERS[view])
        if origin:
            self.show_origin(f"From {origin}" + (f"  ·  {mc.FILTERS[view]}" if view and view != "all" else ""), back,
                             f"Back to {origin}")
            self.origin_clear.pack(side="right", padx=(0, 8), pady=6)
        self.rescan()

    def rescan(self):
        if not self.root_dir:
            return
        if self.busy:
            return
        self._close_cover()
        self.rows, self.shown, self.index, self.loading = [], [], {}, []
        self.comics.set_rows([])
        if self.picked is not None:
            everything = [p for p in self.picked if p.is_file()]
        else:
            it = self.root_dir.rglob("*") if self.vars["recursive"].get() else self.root_dir.iterdir()
            everything = [p for p in it if p.is_file() and not in_archive(p, self.root_dir)]
        files = sorted((p for p in everything if p.suffix.lower() in COMIC_EXT),
                       key=lambda p: natural_key(p.relative_to(self.root_dir)))
        self.say("")
        if not files:
            self.progress_text = "No comics found."
            self._sync()
            return
        self.progress_text = f"Reading {len(files):,} comics…"
        self.busy, self.q = "scan", queue.Queue()
        threading.Thread(target=_scan, args=(self.q, files, self.root_dir), daemon=True).start()
        self._sync()
        self._poll()

    def _poll(self):
        try:
            for _ in range(300):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "row":
                    self.loading.append(msg[1])
                    if msg[2] % 100 == 0:
                        self.progress_text = f"Reading {msg[2]:,} of {msg[3]:,}…"
                        self.bar_text.configure(text=self.progress_text)
                elif kind == "done":
                    self._end_scan()
                    return
                elif kind == "start":
                    self.progress_text = f"Saving {msg[1] + 1} of {msg[2]}…"
                    self.bar_text.configure(text=self.progress_text)
                elif kind == "ok":
                    self.applied += 1
                elif kind == "fail":
                    self.failed.append(f"{msg[1].path.name}: {msg[2]}")
                else:
                    self._end_apply()
                    return
        except queue.Empty:
            pass
        self.after(40, self._poll)

    def _end_scan(self):
        self.busy = self.q = None
        self.rows = self.loading
        self.loading = []
        self.sugg = mc.SuggestIndex(self.rows)
        self.progress_text = ""
        locked = sum(1 for r in self.rows if r.locked)
        if locked:
            self.cbr_label.configure(text=f"{_plural(locked, '.cbr file')} cannot be edited until converted to .cbz.")
            self.cbr_note.pack(fill="x", pady=(8, 0), after=self.comics)
        else:
            self.cbr_note.pack_forget()
        self._rebuild()
        self._sync()

    def _end_apply(self):
        self.busy = self.q = None
        text = f"Saved {_plural(self.applied, 'comic')}" + (f" · {len(self.failed)} failed ({self.failed[0]})" if self.failed else "")
        self.progress_text = ""
        self.rescan()
        self.say(text, err=bool(self.failed))
        if self.on_saved and self.applied:
            self.on_saved()

    # ------------------------------------------------------------------ the table of comics
    def _view_key(self):
        return KEY_OF.get(self.vars["view"].get(), "all")

    def _view_changed(self):
        if self.rows:
            self._rebuild()

    def _rebuild(self):
        key = self._view_key()
        self.shown = [r for r in self.rows if mc.matches(r, key)]
        self.index = {id(r): i for i, r in enumerate(self.shown)}
        self.comics.set_rows([self._values(r) for r in self.shown], tags=[self._tags(r) for r in self.shown])
        self._selection_changed()
        self._refresh_review()
        self._sync()

    @staticmethod
    def _cell(row, name):
        return row.value(name) or DASH

    def _values(self, row):
        dot = "·" if row.locked else ("!" if mc.needs_attention(row) else "✓")
        state = "Locked (.cbr)" if row.locked else ("Edited" if row.pending else "")
        return (dot, row.path.name, self._cell(row, "series"), self._cell(row, "issue"), self._cell(row, "volume"),
                self._cell(row, "year"), self._cell(row, "publisher"), state)

    @staticmethod
    def _tags(row):
        return ("dim",) if row.locked else ()

    def _update(self, rows):
        """Redraw the table rows for `rows` after an edit, without losing the selection."""
        for r in rows:
            i = self.index.get(id(r))
            if i is not None:
                self.comics.update_row(i, self._values(r), self._tags(r))
        self._schedule_review()
        self._sync()

    def select_shown(self):
        self.comics.select(range(len(self.shown)))

    # ------------------------------------------------------------------ selection and the forms
    def _selection_changed(self):
        self._flush_now()
        self.selected_rows = [self.shown[i] for i in self.comics.selected() if i < len(self.shown)]
        self._drop_offer()
        n = len(self.selected_rows)
        mode = self.mode.get()
        if mode == AUTO:
            mode = ONE if n == 1 else MANY   # follows the selection
        self.empty.pack_forget()
        self.one.pack_forget()
        self.many.pack_forget()
        if not n:
            self.target_label.configure(text="Nothing selected")
            self.empty.configure(text="Select a comic on the left to edit it, or several to edit them together." if self.rows else
                                 "Choose a folder or some comics on the left to begin.")
            self.empty.pack(fill="x", pady=(4, 0))
        elif mode == ONE:
            self.target_label.configure(text="Editing one comic" + (f" (the first of {n} selected)" if n > 1 else ""))
            self.one.pack(fill="x")
            self._fill_one(self.selected_rows[0])
        else:
            targets = self._targets()
            self.target_label.configure(text=f"Editing {_plural(len(targets), 'comic')} together"
                                        + (f" ({n - len(targets)} locked .cbr left out)" if len(targets) != n else ""))
            self.many.pack(fill="x")
            self.set_btn.configure(text=f"Set for {_plural(len(targets), 'comic')}")
            self._fill_many()
        self._sync()

    def _targets(self):
        return [r for r in self.selected_rows if not r.locked]

    def _step(self, d):
        if not self.selected_rows:
            return
        i = self.index.get(id(self.selected_rows[0]), 0) + d
        if 0 <= i < len(self.shown):
            self.comics.tree.selection_set(str(i))
            self.comics.tree.see(str(i))

    def _fill_one(self, row):
        self._filling = True
        try:
            for name in mc.FIELDS:
                self.vars_one[name].set(row.value(name))
                ent = self.one_entries[name]
                inner = getattr(getattr(ent, "inner", ent), "_entry", None)
                if inner is not None:
                    inner.configure(state="disabled" if row.locked else "normal")
        finally:
            self._filling = False
        i = self.index.get(id(row), 0)
        self.file_label.configure(text=row.path.name + ("   (.cbr: convert it to .cbz to edit)" if row.locked else ""))
        self.position.configure(text=f"{i + 1} of {len(self.shown)}")
        self._load_cover(row)
        for name in mc.FIELDS:
            self._chips(False, name, row, self.vars_one[name])
        self._mark_edited(row)

    def _mark_edited(self, row):
        """Say on each field of the one-comic form whether its value differs from what the comic stores."""
        for name in mc.FIELDS:
            label = self.field_labels[(False, name)]
            text = mc.LABELS[name] + ("  ·  edited" if name in row.pending else "")
            if label.cget("text") != text:
                label.configure(text=text, text_color=TEXT if name in row.pending else MUTED)

    def _fill_many(self):
        for name in mc.FIELDS:
            self.vars_many[name].set("")
        first = next(iter(self._targets()), None)
        if first:
            for name in mc.FIELDS:
                self._chips(True, name, first, self.vars_many[name])

    def _chips(self, many, name, row, var):
        box = self.chip_boxes[(many, name)]
        for w in box.winfo_children():
            w.destroy()
        for value, source in self.sugg.for_field(row, name):
            b = tool_button(box, value if len(value) <= 26 else value[:25] + "…", lambda v=value: self._pick_chip(var, name, v),
                            max(60, 22 + 7 * min(len(value), 26)))
            b.pack(side="left", padx=(0, 6))
            tooltip(b, SOURCE_WORDS[source])

    def _pick_chip(self, var, name, value):
        var.set(value)
        if var in self.vars_one.values():
            self._committed(name)

    def _cover_colors(self):
        bg = pick(PANEL)
        self.cover_box.configure(bg=bg)
        self.cover.configure(bg=bg, fg=pick(MUTED))

    def _show_cover(self, photo, text=""):
        """Put `photo` (a PhotoImage, or None) on the cover label, keeping a reference so Tk does not lose it."""
        self.cover.configure(image=photo or "", text=text)
        self.cover_image = photo

    def _load_cover(self, row):
        if row.locked:
            self._show_cover(None, "No preview\nfor .cbr")
            return
        try:
            with zipfile.ZipFile(row.path) as z:
                pages = sorted((n for n in z.namelist() if is_page(n)), key=natural_key)
                img = Image.open(io.BytesIO(z.read(pages[0]))) if pages else None
            if img is None:
                raise ValueError("no pages")
            img.thumbnail((150, 220))
            self._show_cover(ImageTk.PhotoImage(img.convert("RGB")))
        except Exception:  # noqa: BLE001 - a missing preview must never block editing
            self._show_cover(None, "No preview")

    def _close_cover(self):
        self._show_cover(None)

    # ------------------------------------------------------------------ editing
    def _typed(self, name):
        """A field of the one-comic form changed: store it as a pending edit."""
        if self._filling or not self.selected_rows:
            return
        row = self.selected_rows[0]
        if row.locked:
            return
        row.set(name, self.vars_one[name].get())
        self._mark_edited(row)
        self._dirty.append(row)
        if self._flush_job is None:   # redraw once typing pauses, not on every key
            self._flush_job = self.after(350, self._flush_now)

    def _flush_now(self):
        """Redraw the table rows, the review and the footer for the comics edited by typing."""
        if self._flush_job is not None:
            self.after_cancel(self._flush_job)
            self._flush_job = None
        if self._dirty:
            rows = {id(r): r for r in self._dirty}.values()
            self._dirty = []
            self._update(list(rows))

    def _committed(self, name):
        """The user finished with a field (left it or pressed Enter): offer the value to the rest of the series."""
        self._flush_now()
        if not self.selected_rows or self.selected_rows[0].locked:
            return
        row = self.selected_rows[0]
        if name in mc.SHARED and name in row.pending and row.pending[name]:
            others = mc.others_lacking(self.rows, row, name)
            if others:
                self.offer = (row, name, others)
                self.offer_label.configure(text=f"Apply {mc.LABELS[name].lower()} “{row.pending[name]}” to the other "
                                                f"{_plural(len(others), 'comic')} in this series that have none?")
                self.offer_box.pack(fill="x", pady=(0, 10), before=self.one)

    def _take_offer(self):
        if self.offer:
            row, name, others = self.offer
            for r in others:
                r.set(name, row.value(name))
            self._update(others)
            self.say(f"{mc.LABELS[name]} set on {_plural(len(others), 'more comic')}.")
        self._drop_offer()

    def _drop_offer(self):
        self.offer = None
        self.offer_box.pack_forget()

    def set_many(self):
        """Set the fields that have a value for every selected comic."""
        targets = self._targets()
        if not targets:
            return
        done = 0
        for name in mc.FIELDS:
            text = self.vars_many[name].get().strip()
            if text:
                for r in targets:
                    r.set(name, text)
                done += 1
        for name in mc.FIELDS:
            self.vars_many[name].set("")
        self._update(targets)
        self.say(f"{_plural(done, 'field')} set on {_plural(len(targets), 'comic')}." if done else "Fill in a field first.", err=not done)

    def fill_blanks(self):
        """Fill every empty field the file name can supply, for the selected comics."""
        targets = self._targets()
        n = sum(mc.fill_from_filename(r, self.root_dir) for r in targets)
        self._update(targets)
        self.say(f"Filled {_plural(n, 'blank')} from file names." if n else "Nothing to fill: the file names add nothing new.")

    def remove_issue(self, remove):
        """Delete the issue number from the selected comics (or take that back)."""
        targets = self._targets()
        for r in targets:
            if remove:
                if r.ci.get("issue"):
                    r.pending["issue"] = None
                else:
                    r.pending.pop("issue", None)
            else:
                r.pending.pop("issue", None)
        self._update(targets)
        have = sum(1 for r in targets if r.ci.get("issue"))
        self.say(f"Issue number will be removed from {have} of {len(targets)} comics." if remove
                 else f"Issue number kept on {_plural(len(targets), 'comic')}.")

    def discard(self):
        changed = [r for r in self.rows if r.pending]
        for r in changed:
            r.discard()
        self._update(changed)
        self._selection_changed()
        self.say("Edits discarded.")

    # ------------------------------------------------------------------ review and save
    def _schedule_review(self):
        if self._review_job is None:
            self._review_job = self.after(150, self._refresh_review)

    def _refresh_review(self):
        self._review_job = None
        ch = mc.changes(self.rows)
        comics = len({id(r) for r, *_ in ch})
        gone = sum(1 for _r, _f, _o, new in ch if not new)
        backup = self.vars["original"].get() == BACKUP
        self.review_head.configure(text=(f"{_plural(len(ch), 'change')} in {_plural(comics, 'comic')}" if ch else "No changes yet"))
        if ch:
            note = f"Saving writes {_plural(len(ch), 'change')} to {_plural(comics, 'comic')}."
            if gone:
                note += f" {_plural(gone, 'value')} will be deleted from the comics."
            note += " The originals are kept in an Archive folder." if backup else " The files are replaced in place."
            note += " Nothing is written until you press Confirm."
        else:
            note = "Nothing to save yet. Changes you make above are listed here."
        if self.save_note.cget("text") != note:
            self.save_note.configure(text=note)
        want = f"Confirm and save {_plural(len(ch), 'change')}" if ch else "Confirm and save"
        state = "normal" if ch and not self.busy else "disabled"
        if self.confirm_btn.cget("text") != want or str(self.confirm_btn.cget("state")) != state:
            self.confirm_btn.configure(text=want, state=state)
        self.review.set_rows([(r.path.name, mc.LABELS[f], old or DASH, new if new else "(removed)") for r, f, old, new in ch])
        self._sync()

    def go_review(self):
        """The footer button: scroll to the changes (nothing is written from here)."""
        self._refresh_review()
        self.update_idletasks()
        canvas = self.right._parent_canvas
        total = max(1, self.right.winfo_height())
        canvas.yview_moveto(max(0.0, min(1.0, (self.changes_box.winfo_y() - 8) / total)))

    def pending_rows(self):
        return [r for r in self.rows if r.pending and not r.locked]

    def apply(self):
        """Confirm and save, pressed under the changes: the only place anything is written."""
        self._flush_now()
        todo = self.pending_rows()
        if not todo or self.busy:
            return
        backup = self.vars["original"].get() == BACKUP
        self.applied, self.failed = 0, []
        self.busy, self.q = "apply", queue.Queue()
        self.progress_text = "Saving…"
        self._sync()
        threading.Thread(target=_apply, args=(self.q, todo, backup), daemon=True).start()
        self._poll()

    def _open(self, key):
        if self.open_tool:
            self.open_tool(key)

    def stop_action(self):
        return None

    # ------------------------------------------------------------------ segments and footer
    def _sync(self):
        n = len(self.rows)
        pending = self.pending_rows()
        changes = len(mc.changes(pending))
        if not n:
            summary = self.progress_text
        else:
            need = sum(1 for r in self.rows if mc.needs_attention(r) and not r.locked)
            key = self._view_key()
            summary = (f"{_plural(n, 'comic')} · {need:,} need attention" if key == "all" else
                       f"{len(self.shown):,} of {n:,} · {mc.FILTERS[key]}")
        if self.left_summary.cget("text") != summary:
            self.left_summary.configure(text=summary)
        if self.busy:
            self.set_footer(self.progress_text or "Working…", "Review changes", None, enabled=False)
            return
        text = self.status.cget("text") or (f"{_plural(changes, 'change')} in {_plural(len(pending), 'comic')} waiting to be saved."
                                            if changes else ("Select comics to edit them." if n else "Choose a folder of comics."))
        self.set_footer(text, f"Review {_plural(changes, 'change')}" if changes else "Review changes", self.go_review,
                        enabled=bool(changes), secondary=[("Discard edits", self.discard)] if changes else [])

    def say(self, msg, err=False):
        if hasattr(self, "status"):
            self.status.configure(text=msg, text_color=DANGER if err else MUTED)
            if hasattr(self, "confirm_btn"):
                self._sync()

    def apply_theme(self):
        super().apply_theme()
        self._cover_colors()
        for table in (self.comics, self.review):
            table.apply_theme()

"""Renamer page: standardise comic file names from the filename and ComicInfo.xml, with a
preview table you can edit before anything is touched on disk."""
import queue
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from rename_core import (CASES, CUSTOM, DEFAULT_CUSTOM, FIELDS, FOLDER_STYLES, PADS, PRESETS, STYLES,
                         build_stem, do_rename, find_files, merge, parse_filename, read_comicinfo,
                         safe_name, series_folder)
from ui_kit import (ACCENT, BG, BORDER, FONT, MUTED, PANEL, TEXT, DropZone, Form, Page, apply_tree_theme,
                    build_tree, button, entry, menu, pick, switch_style, title_block)

OK, SAME, BAD = "Ready", "Unchanged", ("Exists", "Duplicate", "No series")


@dataclass
class Item:
    src: Path
    parsed: dict
    ci: dict
    new_stem: str = ""
    dest: Path = None
    checked: bool = True
    status: str = ""
    source: str = "Filename"
    manual: bool = False  # user typed the name: don't overwrite it when options change
    fields: dict = field(default_factory=dict)
    missing: bool = False  # no series could be found
    iid: str = field(default="", repr=False)


def _scan(q, files, use_ci):
    for k, p in enumerate(files):
        ci = read_comicinfo(p) if use_ci else {}
        q.put(("item", Item(p, parse_filename(p.stem), ci), k + 1, len(files)))
    q.put(("done",))


class RenamePage(Page):
    defaults = {"recursive": True, "include_other": True, "use_ci": True, "style": STYLES[0],
                "custom": DEFAULT_CUSTOM, "pad": "3 digits (001)", "case": CASES[0],
                "move": False, "folder_style": FOLDER_STYLES[0], "keep_order": False}
    choices = {"style": STYLES, "pad": list(PADS), "case": CASES, "folder_style": FOLDER_STYLES}

    def __init__(self, parent):
        super().__init__(parent)
        self.root_dir = None
        self.items = []
        self.q = None
        self._editor = None
        self._by_iid = {}
        self._pending = False
        self._canon = {}  # series folder casing: first spelling seen wins

        title_block(self.main, "Renamer", "Give every file the same name pattern. Review, edit, then apply.")
        self.drop = DropZone(self.main, "Drop a folder here, or click to browse", self.browse)
        self.drop.pack(fill="x")
        bar = ctk.CTkFrame(self.main, fg_color=BG)
        bar.pack(fill="x", pady=(14, 6))
        self.meta = ctk.CTkLabel(bar, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(side="left")
        for text, val in (("Select none", False), ("Select all", True)):
            b = ctk.CTkButton(bar, text=text, width=84, height=26, corner_radius=6, font=(FONT, 12),
                              fg_color=BG, hover_color=PANEL, text_color=TEXT, border_width=1,
                              border_color=BORDER, command=lambda v=val: self.select_all(v))
            b.pack(side="right", padx=(6, 0))
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER,
                                           progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        self._build_table()

        v = self.vars
        sw = switch_style()
        box = self.form.add("Files")
        ctk.CTkSwitch(box, text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        ctk.CTkSwitch(box, text="Include PDF and EPUB", variable=v["include_other"], **sw).pack(
            anchor="w", pady=(8, 0))
        ctk.CTkSwitch(box, text="Use ComicInfo.xml when present", variable=v["use_ci"], **sw).pack(
            anchor="w", pady=(8, 0))
        menu(self.form.add("Naming style"), v["style"], STYLES).pack(fill="x")
        self.custom_row = self.form.add("Template")
        entry(self.custom_row, v["custom"]).pack(fill="x")
        ctk.CTkLabel(self.custom_row, font=(FONT, 11), text_color=MUTED, anchor="w", justify="left",
                     wraplength=260,
                     text="Tokens: " + " ".join("{%s}" % f for f in FIELDS) +
                          "\nWrap optional parts in [ ]. They vanish when a value is missing."
                     ).pack(fill="x", pady=(6, 0))
        ctk.CTkSwitch(self.form.add("Reading-order numbers"), text="Keep the number at the start", variable=v["keep_order"],
                      **sw).pack(anchor="w")
        menu(self.form.add("Issue number"), v["pad"], list(PADS)).pack(fill="x")
        menu(self.form.add("Series capitalisation"), v["case"], CASES).pack(fill="x")
        ctk.CTkSwitch(self.form.add("Folders"), text="Move into series folders", variable=v["move"],
                      **sw).pack(anchor="w")
        self.folder_row = self.form.add("Series folder name")
        menu(self.folder_row, v["folder_style"], FOLDER_STYLES).pack(fill="x")

        self.btn_apply = button(self.footer, "Apply renames", self.apply, primary=True)
        self.btn_apply.pack(pady=(0, 8))
        self.btn_scan = button(self.footer, "Rescan folder", self.rescan)
        self.btn_scan.pack()
        self._enable(False)

        self.watch("recursive", "include_other", "use_ci", callback=self.rescan)
        self.watch("style", "custom", "pad", "case", "move", "folder_style", "keep_order", callback=self.recompute)
        self._toggle_rows()

    # --- table ---
    def _build_table(self):
        wrap, self.tree = build_tree(self.main, [
            ("sel", "", 38, False), ("old", "Current name", 210, True),
            ("new", "New name  (double-click to edit)", 250, True), ("status", "Status", 86, False)])
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<Double-1>", self._edit)

    def apply_theme(self):
        self._close_editor(False)
        apply_tree_theme(self.tree)

    def _rel(self, p):
        try:
            return str(p.relative_to(self.root_dir))
        except ValueError:
            return str(p)

    def _row_values(self, it):
        return ("☑" if it.checked else "☐", self._rel(it.src), self._rel(it.dest), it.status)

    def _row_tags(self, it):
        return ("bad",) if it.status in BAD else ("dim",) if it.status == SAME else ()

    def _refresh_row(self, it):
        self.tree.item(it.iid, values=self._row_values(it), tags=self._row_tags(it))

    def _click(self, e):
        if self.tree.identify_region(e.x, e.y) == "cell" and self.tree.identify_column(e.x) == "#1":
            iid = self.tree.identify_row(e.y)
            it = self._by_iid.get(iid)
            if it:
                it.checked = not it.checked
                self._resolve()
                return "break"
        return None

    def _edit(self, e):
        iid = self.tree.identify_row(e.y)
        if not iid or self.tree.identify_column(e.x) != "#3":
            return
        self._close_editor(commit=False)
        it = self._by_iid[iid]
        x, y, w, h = self.tree.bbox(iid, "new")
        ed = tk.Entry(self.tree, font=(FONT, 11), relief="flat", bd=0, highlightthickness=1,
                      highlightbackground=pick(ACCENT), highlightcolor=pick(ACCENT), fg=pick(TEXT), bg=pick(BG),
                      insertbackground=pick(TEXT))
        ed.insert(0, it.dest.name)
        ed.select_range(0, len(it.dest.stem))
        ed.place(x=x, y=y, width=w, height=h)
        ed.focus_set()
        ed.bind("<Return>", lambda _: self._close_editor(True))
        ed.bind("<Escape>", lambda _: self._close_editor(False))
        ed.bind("<FocusOut>", lambda _: self._close_editor(True))
        self._editor = (ed, it)

    def _close_editor(self, commit):
        if not self._editor:
            return
        ed, it = self._editor
        self._editor = None
        text = ed.get().strip()
        ed.destroy()
        if commit and text:
            suffix = it.src.suffix
            stem = text[:-len(suffix)] if text.lower().endswith(suffix.lower()) else text
            if safe_name(stem) != it.dest.stem:
                it.new_stem, it.manual = stem, True
                self._place(it)
                self._resolve()

    def select_all(self, value):
        for it in self.items:
            it.checked = value
        self._resolve()

    # --- options ---
    def _toggle_rows(self):
        Form.show(self.custom_row, self.vars["style"].get() == CUSTOM)
        Form.show(self.folder_row, self.vars["move"].get())

    def _template(self):
        o = self.vars
        return o["custom"].get() if o["style"].get() == CUSTOM else PRESETS[o["style"].get()]

    # --- scan ---
    def browse(self):
        d = filedialog.askdirectory(title="Folder of comics to rename")
        if d:
            self.set_folder(d)

    def set_folder(self, folder):
        self.root_dir = Path(folder)
        self.drop.set(str(self.root_dir))
        self.rescan()

    def _enable(self, on):
        """`on`: the table is settled. Apply is then governed by _resolve()."""
        self.btn_apply.configure(state="disabled")
        self.btn_scan.configure(state="normal" if on and self.root_dir else "disabled")

    def rescan(self):
        if not self.root_dir:
            return
        if self.q:  # a scan is running: redo it when it ends
            self._pending = True
            return
        o = self.state()
        files = find_files(self.root_dir, o["recursive"], o["include_other"])
        self._close_editor(False)
        self.tree.delete(*self.tree.get_children())
        self.items, self._by_iid, self._canon = [], {}, {}
        self.say("")
        if not files:
            self.meta.configure(text="No comic files found")
            self._enable(True)
            return
        self.meta.configure(text=f"Reading {len(files)} files…")
        self.progress.set(0)
        self._enable(False)
        self.q = queue.Queue()
        threading.Thread(target=_scan, args=(self.q, files, o["use_ci"]), daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(200):
                msg = self.q.get_nowait()
                if msg[0] == "item":
                    it = msg[1]
                    self.items.append(it)
                    self._compute(it)
                    it.iid = self.tree.insert("", "end", values=self._row_values(it), tags=self._row_tags(it))
                    self._by_iid[it.iid] = it
                    self.progress.set(msg[2] / msg[3])
                else:
                    self.q = None
                    self.progress.set(0)
                    self._enable(True)
                    self._resolve()
                    if self._pending:
                        self._pending = False
                        self.rescan()
                    return
        except queue.Empty:
            pass
        self.after(40, self._poll)

    # --- naming ---
    def _compute(self, it):
        o = self.state()
        f = merge(it.parsed, it.ci, o["use_ci"])
        it.source = "ComicInfo" if o["use_ci"] and (it.ci.get("series") or it.ci.get("issue")) else "Filename"
        if not f.get("series") and it.src.parent != self.root_dir:
            f["series"] = it.src.parent.name  # file called just '012.cbz' inside a series folder
        it.fields = f
        if not f.get("series"):
            it.new_stem, it.missing = it.src.stem, True
        else:
            it.missing = False
            if not it.manual:
                stem, _ = build_stem(f, self._template(), o["pad"], o["case"])
                it.new_stem = stem or it.src.stem
                if o["keep_order"] and it.parsed.get("order_prefix"):  # '03 - ' written by the Reading Order tool
                    it.new_stem = it.parsed["order_prefix"] + it.new_stem
        self._place(it)

    def _place(self, it):
        o = self.state()
        name = safe_name(it.new_stem) + it.src.suffix.lower()
        folder = it.src.parent
        if o["move"] and it.fields.get("series"):
            sname = series_folder(it.fields, o["folder_style"])
            folder = self.root_dir / self._canon.setdefault(sname.lower(), sname)
        it.dest = folder / name

    def recompute(self):
        self._toggle_rows()
        if not self.items or self.q:
            return
        self._canon = {}
        for it in self.items:
            self._compute(it)
        self._resolve()

    def _resolve(self):
        """Mark each row Ready / Unchanged / conflicting, refresh the table and the counts."""
        claimed = {}
        for it in self.items:
            if it.dest != it.src and it.checked:
                claimed.setdefault(str(it.dest).lower(), []).append(it)
        for it in self.items:
            if it.missing and not it.manual:
                it.status = "No series"
            elif it.dest == it.src:
                it.status = SAME
            elif len(claimed.get(str(it.dest).lower(), ())) > 1:
                it.status = "Duplicate"
            elif it.dest.exists() and str(it.dest).lower() != str(it.src).lower():
                it.status = "Exists"
            else:
                it.status = OK
            self._refresh_row(it)
        ready = sum(1 for it in self.items if it.checked and it.status == OK)
        bad = sum(1 for it in self.items if it.status in BAD)
        text = f"{len(self.items)} files · {ready} ready to rename"
        if bad:
            text += f" · {bad} need attention"
        self.meta.configure(text=text)
        self.btn_apply.configure(state="normal" if ready else "disabled")

    # --- apply ---
    def apply(self):
        self._close_editor(True)
        todo = [it for it in self.items if it.checked and it.status == OK]
        if not todo:
            return
        moving = any(it.dest.parent != it.src.parent for it in todo)
        msg = f"Rename {len(todo)} file{'s' if len(todo) != 1 else ''}?"
        if moving:
            msg += "\nSome will also be moved into series folders."
        msg += "\n\nThis changes files on disk."
        if not messagebox.askyesno("Apply renames", msg, icon="warning"):
            return
        done, errors = 0, []
        for it in todo:
            try:
                do_rename(it.src, it.dest)
                done += 1
            except OSError as e:
                errors.append(f"{it.src.name}: {e}")
        text = f"Renamed {done} file{'s' if done != 1 else ''}"
        if errors:
            text += f" · {len(errors)} failed ({errors[0]})"
        self.rescan()
        self.say(text, err=bool(errors))

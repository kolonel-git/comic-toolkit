"""Renamer page: read every file's name (and ComicInfo.xml), show it as a card you can correct one at a time or as a
list, name it with a template for its type, and apply only when you say so. Nothing on disk changes until Apply."""
import queue
import re
import threading
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import name_format as nf
from comic_core import common_root, picked_files
from name_format import (ARTICLE_MODES, CASE_MODES, CONFLICT_MODES, DEFAULT_TEMPLATES, EXT_CASES, FOLDER_PRESETS,
                         ILLEGAL_MODES, PADS, PRESETS, SEPARATORS, VOLUME_PADS)
from rename_core import (AUTO_TYPE, COLLECTED_TYPES, SINGLE_TYPES, TYPE_KEYS, TYPES, apply_edits, apply_type,
                         do_rename, find_files, merge, parse_filename, read_comicinfo)
from rename_core import OTHER_EXT, RENAME_EXT
from ui_kit import (ACCENT, BG, BORDER, DANGER, FONT, MUTED, PANEL, TEXT, DropZone, Form, Page, apply_tree_theme,
                    build_tree, button, entry, menu, pick, segmented, switch_style, title_block, Splitter, toolbar, divider)

OK, SAME, NUMBERED, SKIPPED = "Ready", "Unchanged", "Numbered", "Skipped"
BAD = ("Exists", "Duplicate", "No series")
READY = (OK, NUMBERED)
VOL_MODES = ["An issue (manga style)", "A volume (collected edition)"]
VIEWS = ["Cards", "List"]
FILTERS = ["All files", "Needs attention", "Issues", "Collected editions", "Edited by hand"]
TABS = ["Detect", "Names", "Text", "Folders"]
PRESET_HINT = "Choose a preset…"
FIELD_LABELS = {"series": "Series", "title": "Title", "issue": "Issue", "volume": "Volume", "range": "Issue range",
                "year": "Year", "year_end": "Year end", "count": "Issue count"}
STATUS_HELP = {
    "Exists": "A file with this name is already in the destination, so it is not renamed.",
    "Duplicate": "Another ticked file would get exactly this name, so neither is renamed until one changes.",
    "No series": "No series could be found in the name. Type one in Series.",
    SAME: "Already named correctly.",
    NUMBERED: "The name was taken, so a number was added.",
    SKIPPED: "Ticked off: this file will not be renamed.",
}


@dataclass
class Item:
    src: Path
    ci: dict
    parsed: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)  # what the name is built from (detected + ComicInfo + edits)
    edits: dict = field(default_factory=dict)  # values typed in the card: field -> text
    type_override: str = None
    manual_stem: str = None  # a name typed by hand
    auto_stem: str = ""
    new_stem: str = ""
    base_dest: Path = None
    dest: Path = None
    checked: bool = True
    status: str = ""
    kind: str = ""
    missing: bool = False  # no series could be found
    iid: str = field(default="", repr=False)  # row in the list view
    nav: str = field(default="", repr=False)  # row in the card view's file list

    @property
    def touched(self):
        return bool(self.edits or self.type_override or self.manual_stem)


def _scan(q, files, use_ci):
    for k, p in enumerate(files):
        q.put(("item", Item(p, read_comicinfo(p) if use_ci else {}), k + 1, len(files)))
    q.put(("done",))


class RenamePage(Page):
    defaults = {"recursive": True, "include_other": True, "use_ci": True, "detect_collected": True,
                "vol_mode": VOL_MODES[0], "cur_type": "Issue",
                "pad": nf.DEFAULT_OPTIONS["pad"], "vpad": nf.DEFAULT_OPTIONS["vpad"],
                "series_case": CASE_MODES[0], "title_case": CASE_MODES[0], "article": ARTICLE_MODES[0],
                "separator": "Spaces", "illegal": ILLEGAL_MODES[0], "ext_case": EXT_CASES[0], "max_len": "0",
                "keep_order": False, "move": False, "folder_tpl": FOLDER_PRESETS["Series"], "collected_sub": False,
                "collected_sub_name": "Collected Editions", "conflict": CONFLICT_MODES[0], "view": VIEWS[0],
                "filter": FILTERS[0], **{f"t_{nf.slug(t)}": tpl for t, tpl in DEFAULT_TEMPLATES.items()}}
    choices = {"vol_mode": VOL_MODES, "cur_type": TYPE_KEYS, "pad": list(PADS), "vpad": list(VOLUME_PADS),
               "series_case": CASE_MODES, "title_case": CASE_MODES, "article": ARTICLE_MODES,
               "separator": list(SEPARATORS), "illegal": ILLEGAL_MODES, "ext_case": EXT_CASES,
               "conflict": CONFLICT_MODES, "view": VIEWS, "filter": FILTERS}

    def __init__(self, parent):
        super().__init__(parent)
        self.root_dir = None
        self.picked = None  # files chosen one by one instead of a folder
        self.items = []
        self.q = None
        self._editor = None
        self._by_iid, self._by_nav = {}, {}
        self._pending = False
        self._canon = {}  # series folder spelling: first one seen wins
        self._cur = None  # the item shown in the card
        self._loading = False  # true while the card is being filled (no edits to record)
        self._lock_nav = False
        self._after = None
        self._tpl_busy = False
        self._guide = None

        title_block(self.main, "Renamer", "Check each file, correct what is wrong, then rename. Nothing changes until Apply.")
        self.drop = DropZone(self.main, "Drop a folder here, or add a folder or comics below", self.browse,
                             self.browse, self.browse_files)
        self.drop.pack(fill="x")
        bar = ctk.CTkFrame(self.main, fg_color=BG)
        bar.pack(fill="x", pady=(12, 6))
        self.meta = ctk.CTkLabel(bar, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(side="left")
        segmented(bar, self.vars["view"], VIEWS, width=150).pack(side="right")
        toolbar(bar, [("all", "Select all", 84, lambda: self.select_all(True)),
                      ("none", "Select none", 84, lambda: self.select_all(False))], side="right")
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER,
                                           progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        self.holder = ctk.CTkFrame(self.main, fg_color=BG)
        self.holder.pack(fill="both", expand=True)
        self._build_cards()
        self._build_list()
        self._build_form()

        self.btn_apply = button(self.footer, "Apply renames", self.apply, primary=True)
        self.btn_apply.pack(pady=(0, 8))
        divider(self.footer, vertical=False).pack(fill="x", pady=(2, 10))
        self.btn_scan = button(self.footer, "Rescan folder", self.rescan)
        self.btn_scan.pack()
        self._enable(False)

        self.watch("recursive", "include_other", "use_ci", callback=self.rescan)
        self.watch("detect_collected", "vol_mode", "pad", "vpad", "series_case", "title_case", "article", "separator",
                   "illegal", "ext_case", "max_len", "keep_order", "move", "folder_tpl", "collected_sub",
                   "collected_sub_name", "conflict", *(f"t_{nf.slug(t)}" for t in TYPE_KEYS), callback=self.recompute)
        self.watch("view", callback=self._show_view)
        self.watch("filter", callback=self._rebuild_nav)
        self.watch("cur_type", callback=self._load_template)
        self.tab.trace_add("write", lambda *_: self._show_tab())
        self._load_template()
        self._show_tab()
        self._show_view()
        self._show_card(None)

    # ------------------------------------------------------------------ cards view
    def _build_cards(self):
        self.cards = ctk.CTkFrame(self.holder, fg_color=BG)
        left = ctk.CTkFrame(self.cards, fg_color=BG, width=250)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        Splitter(self.cards, left, side="left", lo=190, hi=560).pack(side="left", fill="y", padx=(0, 6))
        menu(left, self.vars["filter"], FILTERS, width=250).pack(fill="x", pady=(0, 6))
        wrap, self.nav_tree = build_tree(left, [("sel", "", 30, False), ("name", "File", 140, True),
                                                ("status", "Status", 84, False)])
        wrap.pack(fill="both", expand=True)
        self.nav_tree.bind("<<TreeviewSelect>>", self._nav_select)
        self.nav_tree.bind("<Button-1>", self._nav_click)

        right = ctk.CTkFrame(self.cards, fg_color=BG)
        right.pack(side="left", fill="both", expand=True)
        top = ctk.CTkFrame(right, fg_color=BG)
        top.pack(fill="x", pady=(0, 8))
        self.btn_prev = button(top, "◀ Previous", lambda: self._step(-1), width=100)
        self.btn_prev.configure(height=28)
        self.btn_prev.pack(side="left")
        self.pos = ctk.CTkLabel(top, text="", font=(FONT, 13), text_color=TEXT, width=100)
        self.pos.pack(side="left", padx=6)
        self.btn_next = button(top, "Next ▶", lambda: self._step(1), width=90)
        self.btn_next.configure(height=28)
        self.btn_next.pack(side="left")
        self.check_var = ctk.BooleanVar(value=True)

        scroll = ctk.CTkScrollableFrame(right, fg_color=BG, border_color=BORDER, border_width=1, corner_radius=10,
                                        scrollbar_button_color=BORDER, scrollbar_button_hover_color=MUTED)
        scroll.pack(fill="both", expand=True)
        self.card_body = scroll
        self.lbl_current = ctk.CTkLabel(scroll, text="", font=(FONT, 12), text_color=MUTED, anchor="w",
                                        justify="left", wraplength=470)
        self.lbl_current.pack(fill="x", padx=14, pady=(12, 2))
        chips = ctk.CTkFrame(scroll, fg_color=BG)
        chips.pack(fill="x", padx=14, pady=(0, 6))
        self.lbl_status = ctk.CTkLabel(chips, text="", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w")
        self.lbl_status.pack(side="left")
        self.lbl_edited = ctk.CTkLabel(chips, text="", font=(FONT, 12), text_color=ACCENT, anchor="w")
        self.lbl_edited.pack(side="left", padx=(10, 0))
        ctk.CTkSwitch(chips, text="Rename", variable=self.check_var, command=self._card_checked,
                      **switch_style()).pack(side="right")

        # the result comes first, so it is always in view while the fields below are corrected
        ctk.CTkLabel(scroll, text="New name", font=(FONT, 11), text_color=MUTED, anchor="w").pack(
            fill="x", padx=14, pady=(2, 0))
        self.name_var = ctk.StringVar()
        entry(scroll, self.name_var).pack(fill="x", padx=14)
        self.name_var.trace_add("write", lambda *_: self._card_name())
        self.lbl_folder = ctk.CTkLabel(scroll, text="", font=(FONT, 12), text_color=MUTED, anchor="w", justify="left",
                                       wraplength=470)
        self.lbl_folder.pack(fill="x", padx=14, pady=(4, 8))

        self.fv = {k: ctk.StringVar() for k in FIELD_LABELS}
        self.type_var = ctk.StringVar(value=AUTO_TYPE)
        grid = ctk.CTkFrame(scroll, fg_color=BG)
        grid.pack(fill="x", padx=14)
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="f")

        def cell(row, col, key, span=1, widget=None):
            box = ctk.CTkFrame(grid, fg_color=BG)
            box.grid(row=row, column=col, columnspan=span, sticky="ew", padx=(0 if col == 0 else 6, 0), pady=(0, 8))
            ctk.CTkLabel(box, text=FIELD_LABELS.get(key, "Type"), font=(FONT, 11), text_color=MUTED,
                         anchor="w").pack(fill="x")
            (widget(box) if widget else entry(box, self.fv[key])).pack(fill="x")

        cell(0, 0, "type", 3, lambda b: menu(b, self.type_var, TYPES, width=200))
        cell(1, 0, "series", 3)
        cell(2, 0, "title", 3)
        cell(3, 0, "issue")
        cell(3, 1, "volume")
        cell(3, 2, "range")
        cell(4, 0, "year")
        cell(4, 1, "year_end")
        cell(4, 2, "count")
        for k, v in self.fv.items():
            v.trace_add("write", lambda *_, k=k: self._card_field(k))
        self.type_var.trace_add("write", lambda *_: self._card_type())

        self.lbl_note = ctk.CTkLabel(scroll, text="", font=(FONT, 12), text_color=MUTED, anchor="w", justify="left",
                                     wraplength=470)
        self.lbl_note.pack(fill="x", padx=14, pady=(4, 0))
        row = ctk.CTkFrame(scroll, fg_color=BG)
        row.pack(fill="x", padx=14, pady=(10, 14))
        button(row, "Automatic name", self._card_auto, width=130).pack(side="left")
        button(row, "Reset this card", self._card_reset, width=130).pack(side="left", padx=(8, 0))

    # ------------------------------------------------------------------ list view
    def _build_list(self):
        self.listing = ctk.CTkFrame(self.holder, fg_color=BG)
        wrap, self.tree = build_tree(self.listing, [
            ("sel", "", 38, False), ("old", "Current name", 210, True),
            ("new", "New name  (double-click to edit)", 250, True), ("type", "Type", 120, False),
            ("status", "Status", 86, False)])
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<Double-1>", self._edit)
        self.tree.bind("<Button-3>", self._type_menu)
        ctk.CTkLabel(self.listing, text="Double-click a name to type a new one, a Type to change it, or the current name "
                     "to open its card.", font=(FONT, 12), text_color=MUTED, anchor="w", justify="left",
                     wraplength=620).pack(fill="x", pady=(6, 0))

    # ------------------------------------------------------------------ side panel
    def _build_form(self):
        v = self.vars
        sw = switch_style()
        self.tab = ctk.StringVar(value=TABS[0])
        self.tab_cells = {t: [] for t in TABS}
        box = self.form.add("Settings")
        segmented(box, self.tab, TABS, width=270).pack(fill="x")

        def add(tab, label=None, heading=False):
            cell = self.form.heading(label) if heading else self.form.add(label)
            self.tab_cells[tab].append(cell)
            return cell

        def note(parent, text):
            ctk.CTkLabel(parent, text=text, font=(FONT, 11), text_color=MUTED, anchor="w", justify="left",
                         wraplength=260).pack(fill="x", pady=(6, 0))

        # --- Detect
        add("Detect", "Source", True)
        b = add("Detect", "Where to look")
        ctk.CTkSwitch(b, text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        ctk.CTkSwitch(b, text="Include PDF and EPUB", variable=v["include_other"], **sw).pack(anchor="w", pady=(8, 0))
        add("Detect", "Reading each name", True)
        b = add("Detect", "Sources")
        ctk.CTkSwitch(b, text="Use ComicInfo.xml when present", variable=v["use_ci"], **sw).pack(anchor="w")
        ctk.CTkSwitch(b, text="Detect collected editions", variable=v["detect_collected"], **sw).pack(anchor="w", pady=(8, 0))
        note(b, "ComicInfo.xml overrides the filename where it has a value. With collected-edition detection off, "
                "every file is treated as an issue.")
        menu(add("Detect", "A name with only “Vol 3” is"), v["vol_mode"], VOL_MODES).pack(fill="x")
        b = add("Detect", "Years")
        note(b, "Years are found inside any brackets: (2016) (Oct 2016) (2016, DC) (2016-10-05) (2016-2017). A volume "
                "that is really a year (v2016, or ComicInfo Volume 2016) is read as the year.")

        # --- Names
        add("Names", "Naming format for each type", True)
        b = add("Names", "Type")
        menu(b, v["cur_type"], TYPE_KEYS).pack(fill="x")
        self.lbl_group = ctk.CTkLabel(b, text="", font=(FONT, 11), text_color=MUTED, anchor="w")
        self.lbl_group.pack(fill="x", pady=(4, 0))
        b = add("Names", "Template")
        self.tpl_edit = ctk.StringVar()
        entry(b, self.tpl_edit).pack(fill="x")
        self.tpl_edit.trace_add("write", lambda *_: self._template_typed())
        self.lbl_tpl = ctk.CTkLabel(b, text="", font=(FONT, 11), text_color=MUTED, anchor="w", justify="left",
                                    wraplength=260)
        self.lbl_tpl.pack(fill="x", pady=(6, 0))
        self.lbl_example = ctk.CTkLabel(b, text="", font=(FONT, 11), text_color=TEXT, anchor="w", justify="left",
                                        wraplength=260)
        self.lbl_example.pack(fill="x", pady=(4, 0))
        b = add("Names", "Start from a preset")
        self.preset = ctk.StringVar(value=PRESET_HINT)
        menu(b, self.preset, [PRESET_HINT, *PRESETS]).pack(fill="x")
        self.preset.trace_add("write", lambda *_: self._preset_picked())
        b = add("Names", "Copy this template to")
        for text, group in (("Single issue types", SINGLE_TYPES), ("Collected types", COLLECTED_TYPES), ("Every type", TYPE_KEYS)):
            button(b, text, lambda g=group: self._copy_template(g)).pack(fill="x", pady=(0, 6))
        button(add("Names", "Reference"), "Format guide: every option…", self.show_guide).pack(fill="x")

        # --- Text
        add("Text", "Numbers", True)
        menu(add("Text", "Issue number"), v["pad"], list(PADS)).pack(fill="x")
        menu(add("Text", "Volume number (collected editions)"), v["vpad"], list(VOLUME_PADS)).pack(fill="x")
        add("Text", "Capitalisation", True)
        menu(add("Text", "Series"), v["series_case"], CASE_MODES).pack(fill="x")
        menu(add("Text", "Title"), v["title_case"], CASE_MODES).pack(fill="x")
        add("Text", "Words and symbols", True)
        menu(add("Text", "Leading “The”"), v["article"], ARTICLE_MODES).pack(fill="x")
        menu(add("Text", "Word separator"), v["separator"], list(SEPARATORS)).pack(fill="x")
        menu(add("Text", "Illegal characters ( : / ? * … )"), v["illegal"], ILLEGAL_MODES).pack(fill="x")
        add("Text", "File name", True)
        menu(add("Text", "Extension"), v["ext_case"], EXT_CASES).pack(fill="x")
        b = add("Text", "Maximum length (0 = no limit)")
        entry(b, v["max_len"]).pack(fill="x")
        ctk.CTkSwitch(add("Text", "Reading-order numbers"), text="Keep the number at the start", variable=v["keep_order"],
                      **sw).pack(anchor="w")

        # --- Folders
        add("Folders", "Series folders", True)
        ctk.CTkSwitch(add("Folders", "Move files"), text="Move into folders", variable=v["move"], **sw).pack(anchor="w")
        b = add("Folders", "Folder preset")
        self.fpreset = ctk.StringVar(value=PRESET_HINT)
        menu(b, self.fpreset, [PRESET_HINT, *FOLDER_PRESETS]).pack(fill="x")
        self.fpreset.trace_add("write", lambda *_: self._folder_preset())
        b = add("Folders", "Folder template")
        entry(b, v["folder_tpl"]).pack(fill="x")
        self.lbl_ftpl = ctk.CTkLabel(b, text="", font=(FONT, 11), text_color=MUTED, anchor="w", justify="left", wraplength=260)
        self.lbl_ftpl.pack(fill="x", pady=(6, 0))
        note(b, "Same tokens as names. “/” makes nested folders, e.g. {publisher}/{series}.")
        b = add("Folders", "Collected editions")
        ctk.CTkSwitch(b, text="Put them in a subfolder", variable=v["collected_sub"], **sw).pack(anchor="w")
        entry(b, v["collected_sub_name"]).pack(fill="x", pady=(8, 0))
        add("Folders", "When a name is taken", True)
        menu(add("Folders", "Conflicts"), v["conflict"], CONFLICT_MODES).pack(fill="x")
        v["folder_tpl"].trace_add("write", lambda *_: self._folder_msg())
        self._folder_msg()

    def _show_tab(self):
        for t, cells in self.tab_cells.items():
            for c in cells:
                Form.show(c, t == self.tab.get())

    # ------------------------------------------------------------------ templates
    def _slug_var(self, type_key):
        return self.vars[f"t_{nf.slug(type_key)}"]

    def templates(self):
        return {t: self._slug_var(t).get() for t in TYPE_KEYS}

    def _load_template(self):
        t = self.vars["cur_type"].get()
        self._tpl_busy = True
        self.tpl_edit.set(self._slug_var(t).get())
        self._tpl_busy = False
        self.lbl_group.configure(text="Applies to single issues" if t in SINGLE_TYPES else "A collected edition: its number is a volume")
        self._template_msg()

    def _template_typed(self):
        if self._tpl_busy:
            return
        self._slug_var(self.vars["cur_type"].get()).set(self.tpl_edit.get())
        self._template_msg()

    def _template_msg(self):
        text = self.tpl_edit.get()
        problems = nf.check_template(text)
        self.lbl_tpl.configure(text="; ".join(problems) if problems else "Template is valid.",
                               text_color=DANGER if problems else MUTED)
        t = self.vars["cur_type"].get()
        f = self._cur.fields if self._cur and self._cur.kind == t and self._cur.fields.get("series") else nf.sample_for(t)
        try:
            ex = nf.build_name(f, text, self._opts()) + ".cbz" if not problems else ""
        except Exception:  # noqa: BLE001 - a half-typed template must not break the page
            ex = ""
        self.lbl_example.configure(text=f"Example: {ex}" if ex else "")

    def _preset_picked(self):
        name = self.preset.get()
        if name in PRESETS:
            self.tpl_edit.set(PRESETS[name])
            self.preset.set(PRESET_HINT)

    def _copy_template(self, group):
        text = self.tpl_edit.get()
        for t in group:
            self._slug_var(t).set(text)
        self.say(f"Copied this template to {len(group)} type{'s' if len(group) != 1 else ''}.")

    def _folder_preset(self):
        name = self.fpreset.get()
        if name in FOLDER_PRESETS:
            self.vars["folder_tpl"].set(FOLDER_PRESETS[name])
            self.fpreset.set(PRESET_HINT)

    def _folder_msg(self):
        problems = nf.check_template(self.vars["folder_tpl"].get())
        self.lbl_ftpl.configure(text="; ".join(problems) if problems else "Template is valid.",
                                text_color=DANGER if problems else MUTED)

    def show_guide(self):
        if self._guide is not None and self._guide.winfo_exists():
            self._guide.lift()
            return
        win = self._guide = ctk.CTkToplevel(self)
        win.title("Naming guide")
        win.geometry("880x680")
        win.configure(fg_color=BG)
        box = ctk.CTkTextbox(win, font=("Consolas", 12), fg_color=PANEL, text_color=TEXT, border_color=BORDER,
                             border_width=1, corner_radius=8, wrap="none")
        box.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        box.insert("1.0", nf.FORMAT_GUIDE)
        box.configure(state="disabled")
        button(win, "Close", win.destroy).pack(pady=(0, 16))
        win.after(150, win.lift)

    def _opts(self):
        o = self.state()
        try:
            n = max(0, int(str(o["max_len"]).strip() or 0))
        except ValueError:
            n = 0
        return {"pad": o["pad"], "vpad": o["vpad"], "series_case": o["series_case"], "title_case": o["title_case"],
                "article": o["article"], "separator": o["separator"], "illegal": o["illegal"],
                "ext_case": o["ext_case"], "max_len": n}

    # ------------------------------------------------------------------ theme and views
    def apply_theme(self):
        self._close_editor(False)
        apply_tree_theme(self.tree)
        apply_tree_theme(self.nav_tree)

    def _show_view(self):
        self.cards.pack_forget()
        self.listing.pack_forget()
        (self.cards if self.vars["view"].get() == VIEWS[0] else self.listing).pack(fill="both", expand=True)

    # ------------------------------------------------------------------ list view interaction
    def _rel(self, p):
        try:
            return str(p.relative_to(self.root_dir))
        except ValueError:
            return str(p)

    def _row_values(self, it):
        return ("☑" if it.checked else "☐", self._rel(it.src), self._rel(it.dest) if it.dest else "", it.kind, it.status)

    def _row_tags(self, it):
        return ("bad",) if it.status in BAD else ("dim",) if it.status in (SAME, SKIPPED) else ()

    def _refresh_row(self, it):
        self.tree.item(it.iid, values=self._row_values(it), tags=self._row_tags(it))
        if it.nav and self.nav_tree.exists(it.nav):
            self.nav_tree.item(it.nav, values=("☑" if it.checked else "☐", self._rel(it.src), it.status),
                               tags=self._row_tags(it))

    def _click(self, e):
        if self.tree.identify_region(e.x, e.y) == "cell" and self.tree.identify_column(e.x) == "#1":
            it = self._by_iid.get(self.tree.identify_row(e.y))
            if it:
                it.checked = not it.checked
                self._resolve()
                return "break"
        return None

    def _edit(self, e):
        iid, col = self.tree.identify_row(e.y), self.tree.identify_column(e.x)
        it = self._by_iid.get(iid)
        if not it:
            return
        if col == "#4":
            self._type_menu(e)
            return
        if col == "#2":
            self.open_card(it)
            return
        if col != "#3":
            return
        self._close_editor(commit=False)
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
            if nf.safe_name(stem, self.vars["illegal"].get()) != it.dest.stem:
                it.manual_stem = stem
                self._compute(it)
                self._resolve()

    def _type_menu(self, e):
        """Pop up the list of types for the row under the mouse (list view)."""
        it = self._by_iid.get(self.tree.identify_row(e.y))
        if not it or self.q:
            return
        self._close_editor(False)
        pop = tk.Menu(self, tearoff=0, font=(FONT, 11))
        for t in TYPES:
            mark = "✓ " if (it.type_override or AUTO_TYPE) == t else "   "
            pop.add_command(label=mark + t, command=lambda t=t: self._set_type(it, t))
        pop.tk_popup(e.x_root, e.y_root)

    def _set_type(self, it, choice):
        it.type_override = None if choice == AUTO_TYPE else choice
        it.manual_stem = None  # a new type means a new name
        it.edits.pop("issue", None)
        it.edits.pop("volume", None)
        self._compute(it)
        self._resolve()

    def select_all(self, value):
        for it in self.items:
            it.checked = value
        self._resolve()

    # ------------------------------------------------------------------ card interaction
    def open_card(self, it):
        self.vars["view"].set(VIEWS[0])
        if not it.nav or not self.nav_tree.exists(it.nav):
            self.vars["filter"].set(FILTERS[0])
        self._select_nav(it)

    def _select_nav(self, it):
        if it.nav and self.nav_tree.exists(it.nav):
            self._lock_nav = True
            self.nav_tree.selection_set(it.nav)
            self.nav_tree.see(it.nav)
            self._lock_nav = False
        self._show_card(it)

    def _nav_select(self, _):
        if self._lock_nav:
            return
        sel = self.nav_tree.selection()
        self._show_card(self._by_nav.get(sel[0]) if sel else None)

    def _nav_click(self, e):
        if self.nav_tree.identify_region(e.x, e.y) == "cell" and self.nav_tree.identify_column(e.x) == "#1":
            it = self._by_nav.get(self.nav_tree.identify_row(e.y))
            if it:
                it.checked = not it.checked
                self._resolve()
                return "break"
        return None

    def _step(self, delta):
        kids = list(self.nav_tree.get_children())
        if not kids or not self._cur or self._cur.nav not in kids:
            return
        i = kids.index(self._cur.nav) + delta
        if 0 <= i < len(kids):
            self._select_nav(self._by_nav[kids[i]])

    def _show_card(self, it):
        self._cur = it
        kids = list(self.nav_tree.get_children())
        if it is None:
            self.pos.configure(text="")
            self.lbl_current.configure(text="Choose a folder to begin." if not self.items else "No file selected.")
            for w in (self.lbl_status, self.lbl_edited, self.lbl_folder, self.lbl_note):
                w.configure(text="")
            self._loading = True
            for v in self.fv.values():
                v.set("")
            self.name_var.set("")
            self.type_var.set(AUTO_TYPE)
            self._loading = False
            self.btn_prev.configure(state="disabled")
            self.btn_next.configure(state="disabled")
            return
        i = kids.index(it.nav) if it.nav in kids else -1
        self.pos.configure(text=f"{i + 1} of {len(kids)}" if i >= 0 else "")
        self.btn_prev.configure(state="normal" if i > 0 else "disabled")
        self.btn_next.configure(state="normal" if 0 <= i < len(kids) - 1 else "disabled")
        self._refresh_card()
        self._template_msg()

    def _refresh_card(self, skip=None):
        it = self._cur
        if it is None:
            return
        self._loading = True
        f = it.fields
        self.lbl_current.configure(text=self._rel(it.src))
        self.check_var.set(it.checked)
        self.type_var.set(it.type_override or AUTO_TYPE)
        for k, var in self.fv.items():
            if k != skip and var.get() != (f.get(k) or ""):
                var.set(f.get(k) or "")
        if skip != "name":
            self.name_var.set(it.dest.name if it.dest else "")
        self.lbl_status.configure(text=f"{it.kind or 'Unknown'}  ·  {it.status}", text_color=DANGER if it.status in BAD else MUTED)
        self.lbl_edited.configure(text="edited" if it.touched else "")
        try:
            folder = it.dest.parent.relative_to(self.root_dir)
            where = str(folder) if str(folder) != "." else "same folder"
        except (ValueError, AttributeError):
            where = str(it.dest.parent) if it.dest else ""
        self.lbl_folder.configure(text=f"Goes to: {where}")
        notes = list(it.parsed.get("notes") or [])
        if it.status in STATUS_HELP:
            notes.append(STATUS_HELP[it.status])
        if it.fields.get("tags"):
            notes.append(f"Other tags in the name: {it.fields['tags']}")
        self.lbl_note.configure(text="\n".join(notes), text_color=DANGER if it.status in BAD else MUTED)
        self._loading = False

    def _card_field(self, key):
        if self._loading or self._cur is None:
            return
        it = self._cur
        it.edits[key] = self.fv[key].get()
        it.manual_stem = None
        self._compute(it)
        self._refresh_card(skip=key)
        self._schedule_resolve()

    def _card_type(self):
        if self._loading or self._cur is None:
            return
        self._set_type(self._cur, self.type_var.get())

    def _card_name(self):
        if self._loading or self._cur is None:
            return
        it = self._cur
        text = self.name_var.get().strip()
        if not text:
            return
        suffix = it.src.suffix
        stem = text[:-len(suffix)] if text.lower().endswith(suffix.lower()) else text
        it.manual_stem = stem if stem != it.auto_stem else None
        self._compute(it)
        self._refresh_card(skip="name")
        self._schedule_resolve()

    def _card_checked(self):
        if self._cur is not None:
            self._cur.checked = self.check_var.get()
            self._resolve()

    def _card_auto(self):
        if self._cur is not None:
            self._cur.manual_stem = None
            self._compute(self._cur)
            self._resolve()

    def _card_reset(self):
        if self._cur is not None:
            it = self._cur
            it.edits, it.type_override, it.manual_stem = {}, None, None
            self._compute(it)
            self._resolve()

    def _schedule_resolve(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(150, self._resolve)

    # ------------------------------------------------------------------ nav list
    def _visible(self, it):
        f = self.vars["filter"].get()
        if f == "Needs attention":
            return it.status in BAD
        if f == "Issues":
            return not it.fields.get("collected")
        if f == "Collected editions":
            return bool(it.fields.get("collected"))
        if f == "Edited by hand":
            return it.touched
        return True

    def _rebuild_nav(self):
        keep = self._cur
        self.nav_tree.delete(*self.nav_tree.get_children())
        self._by_nav = {}
        for it in self.items:
            it.nav = ""
            if self._visible(it):
                it.nav = self.nav_tree.insert("", "end", values=("☑" if it.checked else "☐", self._rel(it.src), it.status),
                                              tags=self._row_tags(it))
                self._by_nav[it.nav] = it
        target = keep if keep is not None and keep.nav else next((self._by_nav[k] for k in self.nav_tree.get_children()), None)
        if target is not None:
            self._select_nav(target)
        else:
            self._show_card(None)

    # ------------------------------------------------------------------ scan
    def browse(self):
        d = filedialog.askdirectory(title="Folder of comics to rename")
        if d:
            self.set_folder(d)

    def browse_files(self):
        files = filedialog.askopenfilenames(title="Choose comics to rename", filetypes=[
            ("Comics and books", "*.cbz *.cbr *.pdf *.epub"), ("All", "*.*")])
        if files:
            self.set_files(files)

    def set_files(self, paths):
        """Rename these files only, instead of a whole folder."""
        files = picked_files(paths, RENAME_EXT | OTHER_EXT)
        if not files:
            self.say("None of those files can be renamed here (.cbz .cbr .pdf .epub).", err=True)
            return
        self.picked = files
        self.root_dir = common_root(files)
        self.drop.set(f"{len(files)} file{'s' if len(files) != 1 else ''} chosen from {self.root_dir}")
        self.rescan()

    def set_folder(self, folder):
        self.root_dir = Path(folder)
        self.picked = None
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
        if self.picked is not None:
            exts = RENAME_EXT | (OTHER_EXT if o["include_other"] else set())
            files = [p for p in self.picked if p.is_file() and p.suffix.lower() in exts]
        else:
            files = find_files(self.root_dir, o["recursive"], o["include_other"])
        self._close_editor(False)
        self.tree.delete(*self.tree.get_children())
        self.nav_tree.delete(*self.nav_tree.get_children())
        self.items, self._by_iid, self._by_nav, self._canon, self._cur = [], {}, {}, {}, None
        self.say("")
        if not files:
            self.meta.configure(text="No comic files found")
            self._show_card(None)
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
                    self._rebuild_nav()
                    if self._pending:
                        self._pending = False
                        self.rescan()
                    return
        except queue.Empty:
            pass
        self.after(40, self._poll)

    # ------------------------------------------------------------------ naming
    def _compute(self, it):
        o = self.state()
        it.parsed = parse_filename(it.src.stem, volume_as_issue=o["vol_mode"] == VOL_MODES[0])
        f = merge(it.parsed, it.ci, o["use_ci"])
        if not o["detect_collected"] and not it.type_override:
            f = apply_type(f, "Issue")
        f = apply_edits(apply_type(f, it.type_override), it.edits)
        if not f.get("series") and it.src.parent != self.root_dir:
            f["series"] = it.src.parent.name  # file called just '012.cbz' inside a series folder
        it.fields, it.kind = f, f.get("kind") or ""
        if not f.get("series"):
            it.missing = True
            it.auto_stem = it.src.stem
        else:
            it.missing = False
            stem = nf.build_name(f, nf.template_for(f, self.templates()), self._opts())
            if o["keep_order"] and it.parsed.get("order_prefix"):  # '03 - ' written by the Reading Order tool
                stem = it.parsed["order_prefix"] + stem
            it.auto_stem = stem
        it.new_stem = it.manual_stem or it.auto_stem
        self._place(it)

    def _place(self, it):
        o = self.state()
        opts = self._opts()
        name = nf.safe_name(it.new_stem, o["illegal"]) + nf.ext_text(it.src.suffix, o["ext_case"])
        folder = it.src.parent
        if o["move"] and it.fields.get("series"):
            parts = nf.build_folder(it.fields, o["folder_tpl"], opts)
            if parts:
                key = "/".join(re.sub(r"^(?:the|a|an)\s+", "", p.lower()) for p in parts)  # 'The X' and 'X' share a folder
                folder = self.root_dir.joinpath(*self._canon.setdefault(key, parts))
            if it.fields.get("collected") and o["collected_sub"] and o["collected_sub_name"].strip():
                folder = folder / nf.sanitize(o["collected_sub_name"].strip())
        it.base_dest = it.dest = folder / name

    def recompute(self):
        if not self.items or self.q:
            self._template_msg()
            return
        self._canon = {}
        for it in self.items:
            self._compute(it)
        self._resolve()
        self._template_msg()

    def _resolve(self):
        """Give each row its status (Ready, Unchanged, a conflict...), refresh both views and the counts."""
        self._after = None
        numbered = self.vars["conflict"].get() == CONFLICT_MODES[1]
        for it in self.items:
            it.dest = it.base_dest
        claimed = {}
        for it in self.items:
            if it.dest != it.src and it.checked:
                claimed.setdefault(str(it.dest).lower(), []).append(it)
        taken = {str(it.src).lower() for it in self.items if it.dest == it.src or not it.checked}
        for it in self.items:
            if it.missing and not it.manual_stem:
                it.status = "No series"
            elif not it.checked:
                it.status = SKIPPED
            elif it.dest == it.src:
                it.status = SAME
            elif numbered:
                d, n = it.base_dest, 2
                while str(d).lower() in taken or (d.exists() and str(d).lower() != str(it.src).lower()):
                    d = it.base_dest.with_name(f"{it.base_dest.stem} ({n}){it.base_dest.suffix}")
                    n += 1
                it.dest = d
                taken.add(str(d).lower())
                it.status = OK if d == it.base_dest else NUMBERED
            elif len(claimed.get(str(it.dest).lower(), ())) > 1:
                it.status = "Duplicate"
            elif it.dest.exists() and str(it.dest).lower() != str(it.src).lower():
                it.status = "Exists"
            else:
                it.status = OK
            self._refresh_row(it)
        ready = sum(1 for it in self.items if it.checked and it.status in READY)
        bad = sum(1 for it in self.items if it.status in BAD)
        collected = sum(1 for it in self.items if it.fields.get("collected"))
        text = f"{len(self.items)} files" + (f" ({collected} collected)" if collected else "") + f" · {ready} ready to rename"
        if bad:
            text += f" · {bad} need attention"
        self.meta.configure(text=text)
        self.btn_apply.configure(state="normal" if ready else "disabled")
        if self._cur is not None:
            self._refresh_card()

    # ------------------------------------------------------------------ apply
    def apply(self):
        self._close_editor(True)
        todo = [it for it in self.items if it.checked and it.status in READY]
        if not todo:
            return
        moving = any(it.dest.parent != it.src.parent for it in todo)
        msg = f"Rename {len(todo)} file{'s' if len(todo) != 1 else ''}?"
        if moving:
            msg += "\nSome will also be moved into folders."
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

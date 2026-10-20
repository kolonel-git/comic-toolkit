"""Renamer page: read every file's name (and ComicInfo.xml), say how sure the reading is, let you set the type of a comic and
correct what is wrong, name it with a template for its type, and apply only when you say so. Nothing on disk changes until
Apply. On the shared page shell in two columns with a divider you can drag. Left: Comics (adding files) and Review (every
file as a card with its new name, a type chip with a dot for how sure the reading is, and a status). Right, scrolling on its own:
File (the selected file's card: type and suggestions, the fields, the name), Detect, Naming and Text and folders."""
import csv
import itertools
import json
import queue
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import name_format as nf
from cardlist import CardList
from comic_core import common_root, picked_files
from flow_kit import Advanced, SegmentPage, labelled
from name_format import (ARTICLE_MODES, CASE_MODES, CONFLICT_MODES, DEFAULT_TEMPLATES, EXT_CASES, FOLDER_PRESETS,
                         ILLEGAL_MODES, PADS, PRESETS, SEPARATORS, VOLUME_PADS)
from rename_core import (AUTO_TYPE, COLLECTED_TYPES, GUESS, SINGLE_TYPES, SURE, TYPE_HELP, TYPE_KEYS, TYPE_LETTERS, TYPES,
                         UNSURE, apply_edits, apply_type, assess, count_pages, do_rename, find_files, merge, parse_filename,
                         read_comicinfo, shape)
from rename_core import OTHER_EXT, RENAME_EXT
from ui_kit import (ACCENT_TEXT, BORDER, DANGER, FONT, MUTED, PANEL, TEXT, TYPE_BODY, TYPE_HINT, DropZone, FlowRow, Toggle,
                    button, divider, entry, menu, popup_menu, switch_style, textbox, tool_button)

OK, SAME, NUMBERED, SKIPPED = "Ready", "Unchanged", "Numbered", "Skipped"
BAD = ("Exists", "Duplicate", "No series")
READY = (OK, NUMBERED)
VOL_MODES = ["An issue (manga style)", "A volume (collected edition)"]
FILTERS = ["All files", "Needs your input", "Needs attention", "Issues", "Collected editions", "Edited by hand"]
PRESET_HINT = "Choose a preset…"
DOT = {SURE: "green", UNSURE: "amber", GUESS: "red"}
SURENESS = {SURE: "Sure", UNSURE: "Not sure", GUESS: "A guess"}
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
ADVANCED_DEFAULTS = {"article": ARTICLE_MODES[0], "separator": "Spaces", "illegal": ILLEGAL_MODES[0], "ext_case": EXT_CASES[0],
                     "max_len": "0", "keep_order": False, "conflict": CONFLICT_MODES[0], "collected_sub": False}


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


@dataclass
class Item:
    src: Path
    ci: dict
    pages: int = None
    parsed: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)  # what the name is built from (detected + ComicInfo + edits)
    edits: dict = field(default_factory=dict)  # values typed in the card: field -> text
    type_override: str = None
    by_rule: str = None  # the type a saved rule gave it
    manual_stem: str = None  # a name typed by hand
    auto_stem: str = ""
    new_stem: str = ""
    base_dest: Path = None
    dest: Path = None
    checked: bool = True
    status: str = ""
    kind: str = ""
    missing: bool = False  # no series could be found
    confidence: str = SURE
    suggestions: list = field(default_factory=list)  # [(type, reason)] when the reading is not sure
    iid: str = field(default="", repr=False)

    @property
    def touched(self):
        return bool(self.edits or self.type_override or self.manual_stem)

    @property
    def needs_input(self):
        return self.confidence != SURE


def _scan(q, files, use_ci):
    for k, p in enumerate(files):
        q.put(("item", Item(p, read_comicinfo(p) if use_ci else {}, count_pages(p)), k + 1, len(files)))
    q.put(("done",))


class RenamePage(SegmentPage):
    title = "Renamer"
    subtitle = "Give every comic a clean, consistent name."
    defaults = {"recursive": True, "include_other": True, "use_ci": True, "detect_collected": True,
                "vol_mode": VOL_MODES[0], "cur_type": "Issue", "rules": "{}",
                "pad": nf.DEFAULT_OPTIONS["pad"], "vpad": nf.DEFAULT_OPTIONS["vpad"],
                "series_case": CASE_MODES[0], "title_case": CASE_MODES[0], "article": ARTICLE_MODES[0],
                "separator": "Spaces", "illegal": ILLEGAL_MODES[0], "ext_case": EXT_CASES[0], "max_len": "0",
                "keep_order": False, "move": False, "folder_tpl": FOLDER_PRESETS["Series"], "collected_sub": False,
                "collected_sub_name": "Collected Editions", "conflict": CONFLICT_MODES[0],
                "filter": FILTERS[0], **{f"t_{nf.slug(t)}": tpl for t, tpl in DEFAULT_TEMPLATES.items()}}
    choices = {"vol_mode": VOL_MODES, "cur_type": TYPE_KEYS, "pad": list(PADS), "vpad": list(VOLUME_PADS),
               "series_case": CASE_MODES, "title_case": CASE_MODES, "article": ARTICLE_MODES,
               "separator": list(SEPARATORS), "illegal": ILLEGAL_MODES, "ext_case": EXT_CASES,
               "conflict": CONFLICT_MODES, "filter": FILTERS}
    split = True
    show_auto = False
    max_width = 1600

    def __init__(self, parent):
        super().__init__(parent)
        self.root_dir = None
        self.picked = None  # files chosen one by one instead of a folder
        self.items = []
        self.q = None
        self._by_iid = {}
        self._ids = itertools.count(1)
        self._pending = False
        self._canon = {}  # series folder spelling: first one seen wins
        self._cur = None  # the item shown in the card (when exactly one is selected)
        self._loading = False  # true while the card is being filled (no edits to record)
        self._after = None
        self._tpl_busy = False
        self._guide = None
        self._rule_rows = []
        v = self.vars
        sw = switch_style()

        # ---- Comics
        self.make_panes(right_width=520, lo=420)
        self.s1 = self.add_block("Comics", side="left")
        self.drop = DropZone(self.s1.body, "Drop a folder of comics here", self.browse, self.browse, self.browse_files, compact=True)
        self.drop.pack(fill="x", padx=(0, 6))
        row = ctk.CTkFrame(self.s1.body, fg_color="transparent")
        row.pack(fill="x", pady=(2, 0))
        Toggle(row, text="Include subfolders", variable=v["recursive"], **sw).pack(side="left", padx=(0, 18))
        Toggle(row, text="Include PDF and EPUB", variable=v["include_other"], **sw).pack(side="left")

        # ---- Review
        self.s2 = self.add_block("Review", side="left", grow=True)
        body = self.s2.body
        self.meta = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=TEXT, anchor="w")   # (kept up to date; the summary says it)
        bar = FlowRow(body)
        bar.pack(fill="x", pady=(0, 2))
        self.btn_filter = tool_button(bar, FILTERS[0] + " ▾", self._filter_menu, 190)
        self.btn_all = tool_button(bar, "Select all", lambda: self.select_all(True), 90)
        self.btn_none = tool_button(bar, "Select none", lambda: self.select_all(False), 100)
        self.btn_settype = tool_button(bar, "Set type ▾", self._bulk_type_menu, 100)
        for w in (self.btn_filter,):
            bar.add(w)
        bar.add(divider(bar), divider=True)
        for w in (self.btn_all, self.btn_none):
            bar.add(w)
        bar.add(divider(bar), divider=True)
        bar.add(self.btn_settype)
        self.hint = ctk.CTkLabel(body, text="Click a file to see its card on the right. Tick a file to rename it. Click the type chip to change a "
                                 "type, or select files and press a letter: I issue, T TPB, H hardcover, V volume… (0 = automatic).",
                                 font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=560)
        self.hint.pack(side="bottom", fill="x", pady=(2, 0))
        self.status = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left", wraplength=560)
        self.progress = ctk.CTkProgressBar(body, height=14, corner_radius=0, border_width=3, border_color=BORDER, fg_color=BORDER,
                                           progress_color=("#FFD60A", "#FFD60A"))
        self.progress.set(0)
        self.cards = CardList(body, self._render, on_tick=self._tick, noun="file", reorder=False, on_key=self._typed,
                              on_button=self._chip, on_select=self._selected,
                              empty="Add a folder above to start.", busy=lambda: bool(self.q), card_h=58)
        self.cards.pack(fill="both", expand=True, padx=(0, 6), pady=(4, 0))
        body.bind("<Configure>", lambda e: [w.configure(wraplength=max(200, int(e.width / self._get_widget_scaling()) - 20))
                                            for w in (self.hint, self.status)], add="+")

        # ---- File: the card of the selected file
        self.s3 = self.add_block("File")
        self._build_card(self.s3.body)

        # ---- Detect
        self.s4 = self.add_block("Detect")
        body = self.s4.body
        Toggle(body, text="Use ComicInfo.xml when present", variable=v["use_ci"], **sw).pack(anchor="w", pady=(0, 8))
        Toggle(body, text="Detect collected editions", variable=v["detect_collected"], **sw).pack(anchor="w")
        ctk.CTkLabel(body, text="ComicInfo.xml overrides the filename where it has a value. With collected-edition detection off, "
                     "every file is treated as an issue.", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                     wraplength=440).pack(fill="x", pady=(6, 10))
        row = labelled(body, "A name with only “Vol 3” is")
        menu(row.cell, v["vol_mode"], VOL_MODES).pack(fill="x")
        row.pack(fill="x", pady=(0, 6))
        self.adv_detect = Advanced(body)
        self.adv_detect.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(self.adv_detect.body, text="Years are found inside any brackets: (2016) (Oct 2016) (2016, DC) (2016-10-05) "
                     "(2016-2017). A volume that is really a year (v2016, or ComicInfo Volume 2016) is read as the year.",
                     font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=420).pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(self.adv_detect.body, text="Saved rules", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w").pack(fill="x")
        self.rules_box = ctk.CTkFrame(self.adv_detect.body, fg_color="transparent")
        self.rules_box.pack(fill="x", pady=(4, 0))

        # ---- Naming
        self.s5 = self.add_block("Naming")
        body = self.s5.body
        row = labelled(body, "A name for each type of comic")
        menu(row.cell, v["cur_type"], TYPE_KEYS).pack(fill="x")
        self.lbl_group = ctk.CTkLabel(row.cell, text="", font=TYPE_HINT, text_color=MUTED, anchor="w")
        self.lbl_group.pack(fill="x", pady=(4, 0))
        row.pack(fill="x", pady=(0, 10))
        row = labelled(body, "Template")
        self.tpl_edit = ctk.StringVar()
        entry(row.cell, self.tpl_edit).pack(fill="x")
        self.tpl_edit.trace_add("write", lambda *_: self._template_typed())
        self.lbl_tpl = ctk.CTkLabel(row.cell, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.lbl_tpl.pack(fill="x", pady=(6, 0))
        self.lbl_example = ctk.CTkLabel(row.cell, text="", font=TYPE_HINT, text_color=TEXT, anchor="w", justify="left", wraplength=440)
        self.lbl_example.pack(fill="x", pady=(4, 0))
        row.pack(fill="x", pady=(0, 10))
        row = labelled(body, "Start from a preset")
        self.preset = ctk.StringVar(value=PRESET_HINT)
        menu(row.cell, self.preset, [PRESET_HINT, *PRESETS]).pack(fill="x")
        self.preset.trace_add("write", lambda *_: self._preset_picked())
        row.pack(fill="x", pady=(0, 6))
        self.adv_names = Advanced(body)
        self.adv_names.pack(fill="x", pady=(6, 0))
        row = labelled(self.adv_names.body, "Copy this template to")
        bar2 = FlowRow(row.cell)
        bar2.pack(fill="x")
        for text, group in (("Single issue types", SINGLE_TYPES), ("Collected types", COLLECTED_TYPES), ("Every type", TYPE_KEYS)):
            bar2.add(tool_button(bar2, text, lambda g=group: self._copy_template(g), 150))
        row.pack(fill="x", pady=(0, 10))
        tool_button(self.adv_names.body, "Format guide: every option…", self.show_guide, 230).pack(anchor="w")

        # ---- Text and folders
        self.s6 = self.add_block("Text and folders")
        body = self.s6.body
        for text, key, vals in (("Issue number", "pad", list(PADS)), ("Volume number (collected editions)", "vpad", list(VOLUME_PADS)),
                                ("Series capitalisation", "series_case", CASE_MODES), ("Title capitalisation", "title_case", CASE_MODES)):
            row = labelled(body, text)
            menu(row.cell, v[key], vals).pack(fill="x")
            row.pack(fill="x", pady=(0, 10))
        Toggle(body, text="Move files into series folders", variable=v["move"], **sw).pack(anchor="w", pady=(0, 10))
        row = labelled(body, "Folder preset")
        self.fpreset = ctk.StringVar(value=PRESET_HINT)
        menu(row.cell, self.fpreset, [PRESET_HINT, *FOLDER_PRESETS]).pack(fill="x")
        self.fpreset.trace_add("write", lambda *_: self._folder_preset())
        row.pack(fill="x", pady=(0, 6))
        self.adv_text = Advanced(body)
        self.adv_text.pack(fill="x", pady=(6, 0))
        ab = self.adv_text.body
        for text, key, vals in (("Leading “The”", "article", ARTICLE_MODES), ("Word separator", "separator", list(SEPARATORS)),
                                ("Illegal characters ( : / ? * … )", "illegal", ILLEGAL_MODES), ("Extension", "ext_case", EXT_CASES),
                                ("When a name is taken", "conflict", CONFLICT_MODES)):
            row = labelled(ab, text)
            menu(row.cell, v[key], vals).pack(fill="x")
            row.pack(fill="x", pady=(0, 10))
        row = labelled(ab, "Maximum length (0 = no limit)")
        entry(row.cell, v["max_len"]).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        Toggle(ab, text="Keep a reading-order number at the start", variable=v["keep_order"], **sw).pack(anchor="w", pady=(0, 10))
        row = labelled(ab, "Folder template")
        entry(row.cell, v["folder_tpl"]).pack(fill="x")
        self.lbl_ftpl = ctk.CTkLabel(row.cell, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.lbl_ftpl.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(row.cell, text="Same tokens as names. “/” makes nested folders, e.g. {publisher}/{series}.", font=TYPE_HINT,
                     text_color=MUTED, anchor="w", justify="left", wraplength=440).pack(fill="x", pady=(2, 0))
        row.pack(fill="x", pady=(0, 10))
        Toggle(ab, text="Put collected editions in a subfolder", variable=v["collected_sub"], **sw).pack(anchor="w", pady=(0, 6))
        entry(ab, v["collected_sub_name"]).pack(fill="x")
        self.adv_text.track(v, ADVANCED_DEFAULTS)

        self.fit_right(self.lbl_tpl, self.lbl_example, self.lbl_ftpl)
        self.watch("recursive", "include_other", "use_ci", callback=self.rescan)
        self.watch("detect_collected", "vol_mode", "pad", "vpad", "series_case", "title_case", "article", "separator",
                   "illegal", "ext_case", "max_len", "keep_order", "move", "folder_tpl", "collected_sub",
                   "collected_sub_name", "conflict", "rules", *(f"t_{nf.slug(t)}" for t in TYPE_KEYS), callback=self.recompute)
        self.watch("filter", callback=self._filter_changed)
        self.watch("cur_type", callback=self._load_template)
        v["folder_tpl"].trace_add("write", lambda *_: self._folder_msg())
        self._folder_msg()
        self._load_template()
        self._rules_view()
        self._show_card()
        self._footer()

    # ------------------------------------------------------------------ the card of one file
    def _build_card(self, body):
        self.card_empty = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.card_empty.pack(fill="x")
        self.card_box = ctk.CTkFrame(body, fg_color="transparent")
        box = self.card_box
        top = ctk.CTkFrame(box, fg_color="transparent")
        top.pack(fill="x")
        self.lbl_current = ctk.CTkLabel(top, text="", font=(FONT, 12, "bold"), text_color=TEXT, anchor="w", justify="left", wraplength=360)
        self.lbl_current.pack(side="left", fill="x", expand=True)
        self.pos = ctk.CTkLabel(top, text="", font=TYPE_HINT, text_color=MUTED, width=70)
        self.pos.pack(side="right")
        chips = ctk.CTkFrame(box, fg_color="transparent")
        chips.pack(fill="x", pady=(2, 6))
        self.lbl_status = ctk.CTkLabel(chips, text="", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w")
        self.lbl_status.pack(side="left")
        self.lbl_edited = ctk.CTkLabel(chips, text="", font=TYPE_HINT, text_color=ACCENT_TEXT, anchor="w")
        self.lbl_edited.pack(side="left", padx=(10, 0))
        self.check_var = ctk.BooleanVar(value=True)
        Toggle(chips, text="Rename", variable=self.check_var, command=self._card_checked, **switch_style()).pack(side="right")

        # how sure the reading is, and what is suggested when it is not
        self.lbl_sure = ctk.CTkLabel(box, text="", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.lbl_sure.pack(fill="x")
        self.sugg = ctk.CTkFrame(box, fg_color="transparent")
        self.sugg.pack(fill="x", pady=(2, 6))

        ctk.CTkLabel(box, text="New name", font=TYPE_HINT, text_color=MUTED, anchor="w").pack(fill="x", pady=(2, 0))
        self.name_var = ctk.StringVar()
        entry(box, self.name_var).pack(fill="x")
        self.name_var.trace_add("write", lambda *_: self._card_name())
        self.lbl_folder = ctk.CTkLabel(box, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.lbl_folder.pack(fill="x", pady=(4, 8))

        self.fv = {k: ctk.StringVar() for k in FIELD_LABELS}
        self.type_var = ctk.StringVar(value=AUTO_TYPE)
        grid = ctk.CTkFrame(box, fg_color="transparent")
        grid.pack(fill="x")
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="f")

        def cell(row, col, key, span=1, widget=None):
            b = ctk.CTkFrame(grid, fg_color="transparent")
            b.grid(row=row, column=col, columnspan=span, sticky="ew", padx=(0 if col == 0 else 6, 0), pady=(0, 8))
            ctk.CTkLabel(b, text=FIELD_LABELS.get(key, "Type"), font=TYPE_HINT, text_color=MUTED, anchor="w").pack(fill="x")
            (widget(b) if widget else entry(b, self.fv[key])).pack(fill="x")

        cell(0, 0, "type", 3, lambda b: menu(b, self.type_var, TYPES, width=200))
        cell(1, 0, "series", 3)
        cell(2, 0, "title", 3)
        cell(3, 0, "issue")
        cell(3, 1, "volume")
        cell(3, 2, "range")
        cell(4, 0, "year")
        cell(4, 1, "year_end")
        cell(4, 2, "count")
        for k, var in self.fv.items():
            var.trace_add("write", lambda *_, k=k: self._card_field(k))
        self.type_var.trace_add("write", lambda *_: self._card_type())
        self.remember_var = ctk.BooleanVar(value=False)
        self.chk_remember = Toggle(box, text="", variable=self.remember_var, command=self._remember_toggled, **switch_style())
        self.chk_remember.pack(anchor="w", pady=(2, 8))
        self.lbl_note = ctk.CTkLabel(box, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.lbl_note.pack(fill="x", pady=(0, 6))
        row = FlowRow(box)
        row.pack(fill="x")
        for text, cmd, w in (("Automatic name", self._card_auto, 130), ("Reset this file", self._card_reset, 120),
                             ("Apply to similar files", self.apply_to_similar, 170), ("◀", lambda: self._step(-1), 40),
                             ("▶", lambda: self._step(1), 40)):
            row.add(tool_button(row, text, cmd, w))

    # ------------------------------------------------------------------ the cards
    def _render(self, iid):
        it = self._by_iid.get(iid)
        if it is None:
            return {"title": str(iid)}
        status = it.status
        tone = "bad" if status in BAD else "warn" if it.needs_input and status != SKIPPED else "dim" if status in (SAME, SKIPPED) else ""
        new = self._rel(it.dest) if it.dest and it.dest != it.src else ""
        return {"num": None, "title": self._rel(it.src), "sub": ("→ " + new) if new else "", "status": status, "tone": tone,
                "checked": it.checked, "buttons": [("type", it.kind or "Unknown", DOT[it.confidence])]}

    def _rel(self, p):
        try:
            return str(p.relative_to(self.root_dir))
        except (ValueError, TypeError):
            return str(p)

    def _tick(self, iid):
        sel = self.cards.sel
        its = [self._by_iid[i] for i in self.cards.selected()] if iid in sel and len(sel) > 1 else [self._by_iid[iid]]
        value = not self._by_iid[iid].checked
        for it in its:
            it.checked = value
        self._resolve()

    def select_all(self, value):
        for it in self.items:
            it.checked = value
        self._resolve()

    def _selected(self):
        """The selection in the list changed: show the card of the one file, or say how many are selected."""
        sel = [self._by_iid[i] for i in self.cards.selected() if i in self._by_iid]
        self._cur = sel[0] if len(sel) == 1 else None
        self._show_card(len(sel))
        self._buttons()

    def _targets(self):
        sel = [self._by_iid[i] for i in self.cards.selected() if i in self._by_iid]
        return sel or ([self._cur] if self._cur else [])

    # ------------------------------------------------------------------ the type: a chip, a menu, keys
    def _type_items(self, targets, with_auto=True):
        out = []
        current = {t.type_override or AUTO_TYPE for t in targets}
        for t in ([AUTO_TYPE] if with_auto else []) + TYPE_KEYS:
            letter = next((k for k, name in TYPE_LETTERS.items() if name == t), "")
            hint = TYPE_HELP.get(t, ("Let the name decide.", ""))[0]
            mark = "✓ " if current == {t} else "   "
            out.append((f"{mark}{t}   [{letter.upper()}]   {hint}", lambda t=t, targets=list(targets): self._set_types(targets, t)))
        return out

    def _chip(self, iid, key):
        """A click on the type chip of a file: a menu of every type, each with what it is."""
        it = self._by_iid.get(iid)
        if it is None or key != "type":
            return
        targets = [self._by_iid[i] for i in self.cards.selected()] if iid in self.cards.sel else [it]
        if iid not in self.cards.sel:
            self.cards.select([iid])
        x, y = self.winfo_pointerxy()
        popup_menu(self.cards.canvas, self._type_items(targets), at=(x, y))

    def _bulk_type_menu(self):
        targets = self._targets()
        if not targets:
            self.say("Select the files to set a type for first.", err=True)
            return
        popup_menu(self.btn_settype, self._type_items(targets))

    def _filter_menu(self):
        popup_menu(self.btn_filter, [(f"{'✓ ' if f == self.vars['filter'].get() else '   '}{f}", lambda f=f: self.vars["filter"].set(f))
                                     for f in FILTERS])

    def _typed(self, ch):
        """A key typed in the list: its letter picks a type for the selected files, and the next file is selected."""
        choice = TYPE_LETTERS.get(ch.lower())
        targets = self._targets()
        if choice is None or not targets:
            return
        last = max(self.cards.order.index(t.iid) for t in targets if t.iid in self.cards.order)
        self._set_types(targets, choice)
        order = self.cards.order
        if last + 1 < len(order):
            self.cards.select([order[last + 1]])
            self.cards.see(order[last + 1])

    def _set_types(self, targets, choice):
        for it in targets:
            it.type_override = None if choice == AUTO_TYPE else choice
            it.manual_stem = None  # a new type means a new name
            it.edits.pop("issue", None)
            it.edits.pop("volume", None)
            if choice == AUTO_TYPE:
                self._forget_rule(it)
            self._compute(it)
        self._resolve()

    def _set_type(self, it, choice):
        self._set_types([it], choice)

    def apply_to_similar(self):
        """Give every file whose name looks like this one's (the same words, other numbers) the same type."""
        it = self._cur
        if it is None:
            self.say("Select one file first.", err=True)
            return
        want = it.type_override or it.kind
        key = shape(it.src.stem)
        like = [o for o in self.items if o is not it and shape(o.src.stem) == key]
        for o in like:
            o.type_override = want if want in TYPE_KEYS else None
            o.manual_stem = None
            self._compute(o)
        self._resolve()
        self.say(f"Set {_plural(len(like), 'other file')} with a name like this one to {want}." if like else
                 "No other file has a name like this one.")

    # ---- saved rules: names like this are always this type
    def rules(self):
        try:
            data = json.loads(self.vars["rules"].get() or "{}")
        except ValueError:
            return {}
        return {k: v for k, v in data.items() if isinstance(k, str) and v in TYPE_KEYS} if isinstance(data, dict) else {}

    def _save_rules(self, rules):
        self.vars["rules"].set(json.dumps(rules, sort_keys=True))
        self._rules_view()

    def _remember_toggled(self):
        it = self._cur
        if it is None:
            return
        rules = self.rules()
        key = shape(it.src.stem)
        if self.remember_var.get() and (it.type_override or it.kind) in TYPE_KEYS:
            rules[key] = it.type_override or it.kind
            self.say(f"Names like “{key}” will always be a {rules[key]}.")
        else:
            rules.pop(key, None)
        self._save_rules(rules)

    def _forget_rule(self, it):
        rules = self.rules()
        if rules.pop(shape(it.src.stem), None) is not None:
            self._save_rules(rules)

    def _rules_view(self):
        for w in self.rules_box.winfo_children():
            w.destroy()
        rules = self.rules()
        if not rules:
            ctk.CTkLabel(self.rules_box, text="None yet. Choose “Always treat names like this as …” on a file's card.",
                         font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=400).pack(fill="x")
            return
        for key, t in sorted(rules.items()):
            row = ctk.CTkFrame(self.rules_box, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{key}   →   {t}", font=(FONT, 12), text_color=TEXT, anchor="w").pack(side="left", fill="x", expand=True)
            tool_button(row, "Delete", lambda k=key: self._delete_rule(k), 70).pack(side="right")

    def _delete_rule(self, key):
        rules = self.rules()
        rules.pop(key, None)
        self._save_rules(rules)

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
        box = textbox(win, font=("Consolas", 12), fg_color=PANEL, text_color=TEXT, border_color=BORDER,
                      border_width=3, corner_radius=0, wrap="none")
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

    def apply_theme(self):
        super().apply_theme()
        self.cards.apply_theme()

    # ------------------------------------------------------------------ the card
    def _show_card(self, n_selected=None):
        it = self._cur
        if it is None:
            self.card_box.pack_forget()
            n = len(self.cards.sel) if n_selected is None else n_selected
            self.card_empty.configure(text=(f"{_plural(n, 'file')} selected. Set their type with the chip on any of them, the Set type "
                                            "button above the list, or a letter key." if n > 1 else
                                            "Choose a folder to begin." if not self.items else "Click a file in the list to see its card."))
            self.card_empty.pack(fill="x")
            self.s3.set_summary(_plural(n, "file") + " selected" if n > 1 else "")
            return
        self.card_empty.pack_forget()
        self.card_box.pack(fill="x")
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
        order = self.cards.order
        self.pos.configure(text=f"{order.index(it.iid) + 1} of {len(order)}" if it.iid in order else "")
        self.lbl_status.configure(text=f"{it.kind or 'Unknown'}  ·  {it.status}", text_color=DANGER if it.status in BAD else MUTED)
        self.lbl_edited.configure(text="edited" if it.touched else "")
        why = {SURE: "Sure of the type", UNSURE: "Not sure of the type", GUESS: "A guess: nothing says what this is"}[it.confidence]
        if it.by_rule:
            why = f"A saved rule says: {it.by_rule}"
        elif it.type_override:
            why = f"You set the type: {it.type_override}"
        self.lbl_sure.configure(text=f"●  {why}", text_color=DANGER if it.confidence == GUESS and not it.type_override else
                                ACCENT_TEXT if it.confidence == UNSURE else MUTED)
        self._suggestions(it)
        eff = it.type_override or it.kind
        self.chk_remember.label.configure(text=f"Always treat names like “{shape(it.src.stem)}” as {eff or '…'}")
        self.remember_var.set(shape(it.src.stem) in self.rules())
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
        if it.pages is not None:
            notes.append(f"{_plural(it.pages, 'page')}")
        self.lbl_note.configure(text="\n".join(notes), text_color=DANGER if it.status in BAD else MUTED)
        self.s3.set_summary(it.src.name)
        self._loading = False

    def _suggestions(self, it):
        for w in self.sugg.winfo_children():
            w.destroy()
        if it.type_override or it.by_rule or not it.suggestions:
            return
        for t, reason in it.suggestions:
            row = ctk.CTkFrame(self.sugg, fg_color="transparent")
            row.pack(fill="x", pady=2)
            tool_button(row, f"Use {t}", lambda t=t: self._set_types([it], t), max(96, 40 + 8 * len(t))).pack(side="left")
            ctk.CTkLabel(row, text=reason, font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=300).pack(
                side="left", padx=(10, 0), fill="x", expand=True)

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
        self._set_types([self._cur], self.type_var.get())

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
            self._forget_rule(it)
            self._compute(it)
            self._resolve()

    def _step(self, delta):
        order = self.cards.order
        if not order or self._cur is None or self._cur.iid not in order:
            return
        i = order.index(self._cur.iid) + delta
        if 0 <= i < len(order):
            self.cards.select([order[i]])
            self.cards.see(order[i])

    def open_card(self, it):
        """Show a file's card (it is selected in the list)."""
        if it.iid not in self.cards.order:
            self.vars["filter"].set(FILTERS[0])
        self.cards.select([it.iid])
        self.cards.see(it.iid)

    def _schedule_resolve(self):
        if self._after:
            self.after_cancel(self._after)
        self._after = self.after(150, self._resolve)

    # ------------------------------------------------------------------ the list: filter and order
    def _visible(self, it):
        f = self.vars["filter"].get()
        if f == "Needs your input":
            return it.needs_input
        if f == "Needs attention":
            return it.status in BAD
        if f == "Issues":
            return not it.fields.get("collected")
        if f == "Collected editions":
            return bool(it.fields.get("collected"))
        if f == "Edited by hand":
            return it.touched
        return True

    def _filter_changed(self):
        self.btn_filter.configure(text=f"{self.vars['filter'].get()} ▾")
        self._fill()

    def _fill(self):
        """Put the files that pass the filter in the list, the ones that need your input first."""
        before = set(self.cards.sel)
        show = [it for it in self.items if self._visible(it)]
        show.sort(key=lambda it: (not it.needs_input,))   # (a stable sort: the files stay in their own order)
        self.cards.order = [it.iid for it in show]
        self.cards.sel &= set(self.cards.order)
        self.cards.forget()
        self.cards.refresh()
        if set(self.cards.sel) != before:
            self._selected()

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
        self.drop.set(f"{_plural(len(files), 'file')} chosen from {self.root_dir}")
        self.rescan()

    def set_folder(self, folder):
        self.root_dir = Path(folder)
        self.picked = None
        self.drop.set(str(self.root_dir))
        self.rescan()

    def add_paths(self, paths):
        paths = [Path(p) for p in paths]
        if len(paths) == 1 and paths[0].is_dir():
            self.set_folder(paths[0])
        else:
            self.set_files(paths)

    def say(self, msg, err=False):
        super().say(msg, err)
        if msg:
            self.status.pack(side="bottom", fill="x", pady=(4, 0), after=self.hint)
        else:
            self.status.pack_forget()

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
        self.items, self._by_iid, self._canon, self._cur = [], {}, {}, None
        self.cards.set_order([])
        self.say("")
        self._show_card()
        if not files:
            self.meta.configure(text="No comic files found")
            self.s1.set_summary("No comic files found")
            self._buttons()
            self._footer()
            return
        self.meta.configure(text=f"Reading {len(files)} files…")
        self.s1.set_summary(f"Reading {len(files)} files…")
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 4), before=self.cards)
        self.q = queue.Queue()
        self._buttons()
        self._footer()
        threading.Thread(target=_scan, args=(self.q, files, o["use_ci"]), daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(200):
                msg = self.q.get_nowait()
                if msg[0] == "item":
                    it = msg[1]
                    it.iid = f"f{next(self._ids)}"
                    self.items.append(it)
                    self._by_iid[it.iid] = it
                    self._compute(it)
                    self.progress.set(msg[2] / msg[3])
                else:
                    self.q = None
                    self.progress.pack_forget()
                    self._resolve()
                    self._fill()
                    if self.cards.order and not self.cards.sel:
                        self.cards.select([self.cards.order[0]])
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
        rule = self.rules().get(shape(it.src.stem))
        it.by_rule = rule if rule and not it.type_override else None
        override = it.type_override or it.by_rule
        f = merge(it.parsed, it.ci, o["use_ci"])
        if not o["detect_collected"] and not override:
            f = apply_type(f, "Issue")
        f = apply_edits(apply_type(f, override), it.edits)
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
        it.confidence, it.suggestions = assess(it.parsed, f, it.pages, decided=bool(override))
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
        """Give each row its status (Ready, Unchanged, a conflict...), refresh the list, the card and the counts."""
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
        self._fill()
        ready = sum(1 for it in self.items if it.checked and it.status in READY)
        bad = sum(1 for it in self.items if it.status in BAD)
        need = sum(1 for it in self.items if it.needs_input)
        collected = sum(1 for it in self.items if it.fields.get("collected"))
        text = f"{len(self.items)} files" + (f" ({collected} collected)" if collected else "") + f" · {ready} ready to rename"
        if bad:
            text += f" · {bad} need attention"
        self.meta.configure(text=text)
        self.s1.set_summary(f"{_plural(len(self.items), 'file')}" + (f" · {need} need your input" if need else "") if self.items else "")
        self.s2.set_summary(f"{ready} ready" + (f" · {bad} need attention" if bad else "") if self.items else "")
        self.s1.set_state("done" if self.items else "active")
        self.s2.set_state("active" if self.items else "locked")
        if self._cur is not None:
            self._refresh_card()
        self._buttons()
        self._footer()

    def _buttons(self):
        idle = not self.q
        n = len(self.items)
        for b in (self.btn_all, self.btn_none, self.btn_filter):
            b.configure(state="normal" if idle and n else "disabled")
        self.btn_settype.configure(state="normal" if idle and self.cards.sel else "disabled")

    def _footer(self):
        ready = sum(1 for it in self.items if it.checked and it.status in READY)
        need = sum(1 for it in self.items if it.needs_input and it.checked and it.status in READY)
        if self.q:
            self.set_footer("Reading the files…", "Apply renames", self.apply, enabled=False)
        elif not self.items:
            self.set_footer("Add a folder of comics to begin.", "Apply renames", self.apply, enabled=False)
        else:
            self.set_footer(f"{_plural(ready, 'rename')} ready" + (f"; {need} of them not sure yet" if need else "") + ".",
                            f"Apply {_plural(ready, 'rename')}" if ready else "Apply renames", self.apply, enabled=bool(ready),
                            secondary=[("Export plan", self.export_plan), ("Rescan folder", self.rescan)])

    # ------------------------------------------------------------------ export and apply
    def export_plan(self):
        """Save what would happen (every file's old and new name, type and status) as a spreadsheet, without renaming."""
        if not self.items:
            return
        out = filedialog.asksaveasfilename(title="Save the plan", defaultextension=".csv", initialfile="rename plan.csv",
                                           filetypes=[("Spreadsheet", "*.csv")])
        if not out:
            return
        try:
            with open(out, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Current name", "New name", "Type", "How sure", "Status"])
                for it in self.items:
                    w.writerow([self._rel(it.src), self._rel(it.dest) if it.dest else "", it.kind, SURENESS[it.confidence], it.status])
        except OSError as e:
            self.say(f"Couldn't save the plan: {e}", err=True)
            return
        self.say(f"Saved the plan for {_plural(len(self.items), 'file')}: {Path(out).name}")

    def apply(self):
        todo = [it for it in self.items if it.checked and it.status in READY]
        if not todo:
            return
        left = sum(1 for it in self.items if it.status in BAD)
        moving = any(it.dest.parent != it.src.parent for it in todo)
        msg = f"Rename {_plural(len(todo), 'file')}?"
        if moving:
            msg += "\nSome will also be moved into folders."
        if left:
            msg += f"\n{_plural(left, 'file')} that need attention keep their name."
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
        text = f"Renamed {_plural(done, 'file')}"
        if left:
            text += f" · {left} left as they were"
        if errors:
            text += f" · {len(errors)} failed ({errors[0]})"
        self.rescan()
        self.say(text, err=bool(errors))

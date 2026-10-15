"""Library audit page: scan a library once, see every problem in one list (broken files, duplicates, missing
issues, junk files, CBR files, warnings, and the reading-order folders that are left out), tick what to fix and fix it.
Built on the page shell: Library, Checks (both fold once the first scan is done) and Findings, which opens with a strip of
counts and a Details panel that opens over the right half of the page and points to the tool that fixes each kind of
problem. Findings can be ignored for good, and the Archive folders that fixes fill up can be reviewed and purged."""
import csv
import json
import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import audit_core as ac
from comic_core import COMIC_EXT, common_root, picked_files
from flow_kit import Advanced, LazyTable, Segment, SegmentPage, facts, labelled, section
from library_scan import scan_library
from reading_orders import ReadingOrders
from ui_kit import (ACCENT, BG, BORDER, EDGE, FONT, MUTED, ON_ACCENT, PANEL, PINK, RAISED, SCROLL, TEXT, TYPE_BODY, TYPE_HINT,
                    TYPE_SEGMENT, DropZone, Toggle, build_tree, button, entry, menu, pick, switch_style,
                    tool_button)

ALL = "All"
CHIPS = [(ALL, "All"), (ac.BROKEN, "Broken"), (ac.DUPLICATE, "Duplicates"), (ac.MISSING, "Missing"),
         (ac.JUNK, "Junk"), (ac.CBR, "CBR"), (ac.WARNING, "Warnings"), (ac.ORDER, "Reading orders")]
FILTERS = [c[0] for c in CHIPS]
CHECKS = [(ac.BROKEN, "check_broken", "Broken files"), (ac.DUPLICATE, "check_dups", "Duplicates"),
          (ac.MISSING, "check_missing", "Missing issues"), (ac.JUNK, "check_junk", "Junk files"),
          (ac.CBR, "check_cbr", "CBR files"), (ac.WARNING, "check_warn", "Warnings")]
CHECK_VAR = {kind: name for kind, name, _ in CHECKS}
COLUMNS = [("sel", "", 38, False), ("kind", "Type", 96, False), ("what", "File or series", 300, True),
           ("detail", "Details", 380, True)]
EMPTY = {ALL: "No problems found.", ac.BROKEN: "No broken files found.", ac.DUPLICATE: "No duplicates found.",
         ac.MISSING: "No gaps found.", ac.JUNK: "No junk files found.", ac.CBR: "No CBR files found.",
         ac.WARNING: "Nothing to warn about.", ac.ORDER: "No reading-order folders are marked."}
WORD = {ALL: ("problem", "problems"), ac.BROKEN: ("broken file", "broken files"),
        ac.DUPLICATE: ("group of duplicates", "groups of duplicates"), ac.MISSING: ("series with gaps", "series with gaps"),
        ac.JUNK: ("comic with junk", "comics with junk"), ac.CBR: ("CBR file", "CBR files"), ac.WARNING: ("warning", "warnings"),
        ac.ORDER: ("comic in reading orders", "comics in reading orders")}
HINTS = {
    ALL: "Everything except warnings and reading orders. Junk files and CBR files are ticked for fixing; tick anything else you "
         "want fixed, then press Fix checked.",
    ac.BROKEN: "Files that would not open or failed the integrity test. Fixing one moves it to an Archive folder (as .bak).",
    ac.DUPLICATE: "The best copy of each group (an original outside a reading-order folder first, then most pages, then the taller "
                  "cover, then the larger file) is kept. Tick the others to move them to an Archive folder (as .bak); nothing "
                  "is deleted.",
    ac.MISSING: "Gaps are tracked separately for issues and for each kind of collected edition. Ignore hides what a row "
                "shows; numbers that go missing later still appear.",
    ac.JUNK: "Thumbs.db, .nfo, __MACOSX and the like. ComicInfo.xml is always kept.",
    ac.CBR: "Fixing converts to a verified CBZ, removes its junk, then deletes the .cbr.",
    ac.WARNING: "Unusual page counts, file sizes and cover resolutions. Nothing to fix automatically; change the limits "
                "under Advanced options in Checks.",
    ac.ORDER: "Folders you marked as reading orders hold deliberate copies. They are left out of Duplicates (turn on "
              "Include reading orders in duplicates in Checks to compare them). Mark or unmark folders in Library stats.",
}
LIMITS = ("min_pages", "max_pages", "small_mb", "big_mb", "low_cover")
ADVANCED = {"integrity": False, "deep_cbr": False, "similar": False, "similarity": "Normal", "from_one": False,
            "min_pages": "10", "max_pages": "300", "small_mb": "1", "big_mb": "500", "low_cover": "800"}


def reveal(path):
    """Show a file in Windows Explorer."""
    try:
        subprocess.Popen(["explorer", "/select,", str(path)])
    except OSError:
        pass


def _plural(n, word):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def _run(q, root, o, stop, only=None, orders=None):
    """Worker: scan, optionally test integrity, then find duplicates and gaps. No Tk calls."""
    try:
        _audit(q, root, o, stop, only, orders)
    except Exception as e:  # noqa: BLE001 - whatever goes wrong, the page must stop waiting
        q.put(("error", f"{type(e).__name__}: {e}"))


def _audit(q, root, o, stop, only=None, orders=None):
    res = scan_library(root, o["recursive"], deep=True, deep_cbr=o["deep_cbr"],
                       progress=lambda d, t, i: q.put(("prog", "Scanning", d, t)), stop=stop, only=only)
    issues = res.issues
    broken = []
    if o["integrity"] and o.get("check_broken", True) and not res.stopped:
        todo = [i for i in issues if i.ext in (".cbz", ".cbr")]
        for k, i in enumerate(todo):
            if stop.is_set():
                res.stopped = True
                break
            q.put(("prog", "Testing", k + 1, len(todo)))
            if i.ext == ".cbr" and not i.ci_read and not o["deep_cbr"]:
                continue  # a real RAR, and the user didn't ask for those
            problems = ac.check_integrity(i.path)
            if problems:
                broken.append((i, problems))
    else:
        broken = [(i, [i.error]) for i in issues if i.error]
    dups, left_out = ac.duplicates_for(issues, orders, o.get("with_orders", False), o["similar"], ac.SIMILARITY[o["similarity"]])
    gaps, ignored = ac.find_missing(issues, o["from_one"])
    q.put(("result", {"issues": issues, "broken": broken, "dups": dups, "gaps": gaps, "ignored_files": ignored,
                      "junk": ac.find_junk(issues), "cbr": ac.find_cbr(issues), "stopped": res.stopped,
                      "seconds": res.seconds, "integrity": o["integrity"], "cache_hits": res.cache_hits,
                      "orders": ac.reading_order_rows(issues, orders), "left_out": left_out}))


def _fix(q, plan, stop):
    for k, (path, action, _) in enumerate(plan):
        if stop.is_set():
            q.put(("fix_stopped",))
            return
        q.put(("prog", "Fixing", k + 1, len(plan)))
        try:
            q.put(("fixed", path, action, ac.apply_fix(path, action)))
        except Exception as e:  # noqa: BLE001 - one bad file must not stop the rest
            q.put(("fix_failed", path, action, " ".join(str(e).split()) or type(e).__name__))
    q.put(("fix_done",))


class AuditPage(SegmentPage):
    title = "Library audit"
    subtitle = "Find broken, duplicate, missing and untidy comics, then fix them."
    defaults = {"recursive": True, "deep_cbr": False, "integrity": False, "similar": False, "similarity": "Normal",
                "from_one": False, "filter": ALL, "min_pages": "10", "max_pages": "300", "small_mb": "1",
                "big_mb": "500", "low_cover": "800", "ignored": "", "with_orders": False,
                "check_broken": True, "check_dups": True, "check_missing": True, "check_junk": True, "check_cbr": True,
                "check_warn": True}
    choices = {"similarity": list(ac.SIMILARITY), "filter": FILTERS}
    split = True
    show_auto = False
    max_width = 1500

    def __init__(self, parent):
        super().__init__(parent)
        self.orders = ReadingOrders()   # the app replaces this with the one it saves in settings.json
        self.open_tool = None           # the app gives a function opening another tool: open_tool(key, view=None)
        self.root_dir = None
        self.picked = None  # comics chosen one by one instead of a folder
        self.results = None
        self.findings, self.rows = [], []
        self.q = None
        self.stop = threading.Event()
        self.ticks = {}  # (kind, key) -> ticked, remembered across list refreshes
        self.fail_notes = {}  # lower-cased path -> why the last fix failed
        self._fix_note = ""
        self._later_id = None
        self._folded = False   # the first scan of a folder folds Library and Checks; later scans leave them as they are
        self._strip_sig = None
        self.busy_text = ""
        self.fixed = self.failed = 0
        self.first_error = ""
        v, sw = self.vars, switch_style()

        # ---- left: the library, then the findings (which take the height that is left)
        left, _right = self.make_panes(right_width=420, lo=340)   # the divider between the columns can be dragged
        self.s1 = Segment(left, "Library")   # folds once the first scan is done
        self.s1.pack(fill="x", pady=(0, 14))
        self.segments.append(self.s1)
        self.drop = DropZone(self.s1.body, "Drop a library folder here, or add a folder or comics below", self.browse,
                             self.browse, self.browse_files)
        self.drop.pack(fill="x", padx=(0, 6), pady=(0, 10))
        Toggle(self.s1.body, text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        self.scan_text = ctk.CTkLabel(self.s1.body, text="", font=TYPE_BODY, text_color=TEXT, anchor="w")
        self.scan_text.pack(fill="x", pady=(10, 4))
        self.progress = ctk.CTkProgressBar(self.s1.body, height=14, corner_radius=0, border_width=3, border_color=BORDER,
                                           fg_color=BORDER, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 6))
        self.status = ctk.CTkLabel(self.s1.body, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                                   wraplength=520)
        self.status.pack(fill="x")

        self.s3 = self.add_block("Findings", side="left", grow=True)
        top = ctk.CTkFrame(self.s3.body, fg_color="transparent")
        top.pack(fill="x", pady=(0, 6))
        tool_button(top, "Details", self.toggle_details, 84).pack(side="right", anchor="n")
        self.strip_box = ctk.CTkFrame(top, fg_color="transparent", height=0)
        self.strip_box.pack(side="left", fill="x", expand=True)
        self.chip_bar = ctk.CTkFrame(self.s3.body, fg_color="transparent")
        self.chip_bar.pack(fill="x", pady=(0, 4))
        self.chips = {}
        for key, label in CHIPS:
            self.chips[key] = tool_button(self.chip_bar, label, lambda k=key: v["filter"].set(k), max(70, 24 + 9 * len(label)))
        self._flows = {}   # frame -> (items, width): what is laid out in rows that wrap
        for frame in (self.strip_box, self.chip_bar):
            frame.bind("<Configure>", lambda e, f=frame: self._reflow(f, e.width), "+")
        tools = ctk.CTkFrame(self.s3.body, fg_color="transparent")
        tools.pack(fill="x", pady=(0, 8))
        tool_button(tools, "Tick all", lambda: self.tick_all(True), 80).pack(side="left", padx=(0, 6))
        tool_button(tools, "Untick all", lambda: self.tick_all(False), 90).pack(side="left", padx=(0, 6))
        self.btn_ignore = tool_button(tools, "Ignore selected", self.ignore_selected, 130)
        self.btn_ignore.pack(side="left", padx=(0, 6))
        self.btn_open = tool_button(tools, "Open folder", self.open_selected, 104)
        self.btn_open.pack(side="left")
        self.extras = ctk.CTkFrame(self.s3.body, fg_color="transparent", height=0)   # buttons that belong to one chip only (height 0: an empty frame is 200 px tall otherwise)
        self.extras.pack(fill="x")
        self.btn_copy = tool_button(self.extras, "Copy wishlist", self.copy_wishlist, 116)
        self.btn_save = tool_button(self.extras, "Save wishlist…", self.save_wishlist, 126)
        self.btn_convert = tool_button(self.extras, "Convert in bulk", lambda: self._open("convert"), 130)
        self.meta = ctk.CTkLabel(self.s3.body, text="", font=TYPE_BODY, text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(2, 6))
        self.hint = ctk.CTkLabel(self.s3.body, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                                 wraplength=520)
        self.hint.pack(side="bottom", fill="x", pady=(6, 0))
        self.table = LazyTable(self.s3.body, COLUMNS, rows=10, empty="Scan the library to see what needs attention.",
                               filterable=True, grow=True)
        self.table.pack(fill="both", expand=True)
        self.tree = self.table.tree
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._sync_buttons())
        self.panes.bind("<Configure>", lambda e: self.hint.configure(wraplength=max(260, int(self.left.winfo_width() / self._get_widget_scaling()) - 40)), "+")

        # ---- right: the checks
        self.s2 = self.add_block("Checks")
        grid = ctk.CTkFrame(self.s2.body, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 6))
        for kind, name, label in CHECKS:
            Toggle(grid, text=label, variable=v[name], **sw).pack(anchor="w", pady=(0, 8))
        Toggle(self.s2.body, text="Include reading orders in duplicates", variable=v["with_orders"], **sw).pack(anchor="w", pady=(6, 2))
        self.orders_note = ctk.CTkLabel(self.s2.body, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                                        wraplength=340)
        self.orders_note.pack(fill="x", pady=(0, 12))
        self.adv = Advanced(self.s2.body)
        self.adv.pack(fill="x")
        Toggle(self.adv.body, text="Full integrity test (slow)", variable=v["integrity"], **sw).pack(anchor="w")
        note1 = ctk.CTkLabel(self.adv.body, text="Reads every file completely. Off: only problems the scan notices.", font=TYPE_HINT,
                             text_color=MUTED, anchor="w", justify="left", wraplength=340)
        note1.pack(fill="x", pady=(4, 10))
        Toggle(self.adv.body, text="Open real .cbr files (slow)", variable=v["deep_cbr"], **sw).pack(anchor="w")
        note2 = ctk.CTkLabel(self.adv.body, text="A RAR is extracted whole to be read.", font=TYPE_HINT, text_color=MUTED,
                             anchor="w", justify="left", wraplength=340)
        note2.pack(fill="x", pady=(4, 10))
        Toggle(self.adv.body, text="Compare cover images", variable=v["similar"], **sw).pack(anchor="w")
        menu(self.adv.body, v["similarity"], list(ac.SIMILARITY)).pack(anchor="w", pady=(8, 10))
        Toggle(self.adv.body, text="Expect issues from #1", variable=v["from_one"], **sw).pack(anchor="w")
        note3 = ctk.CTkLabel(self.adv.body, text="Off: a series is checked from the lowest number you own.", font=TYPE_HINT,
                             text_color=MUTED, anchor="w", justify="left", wraplength=340)
        note3.pack(fill="x", pady=(4, 12))
        ctk.CTkLabel(self.adv.body, text="Warn about", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w").pack(fill="x")
        lim = ctk.CTkFrame(self.adv.body, fg_color="transparent")
        lim.pack(fill="x", pady=(6, 0))
        lim.grid_columnconfigure((0, 1), weight=1, uniform="limits")
        for n, (key, label) in enumerate((("min_pages", "Fewer pages than"), ("max_pages", "More pages than"),
                                          ("small_mb", "Smaller than (MB)"), ("big_mb", "Larger than (MB)"),
                                          ("low_cover", "Cover shorter than (px)"))):
            box = labelled(lim, label)
            entry(box.cell, v[key]).pack(fill="x")
            box.grid(row=n // 2, column=n % 2, sticky="ew", padx=(0, 10), pady=(0, 8))
        self.adv.track(v, ADVANCED)
        self.fit_right(self.orders_note, note1, note2, note3)

        # ---- the Details panel: opens over the right half of the page, down to the footer
        self.panel = ctk.CTkFrame(self, fg_color=PANEL, border_color=BORDER, border_width=EDGE, corner_radius=0)
        bar = ctk.CTkFrame(self.panel, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkLabel(bar, text="Audit details", font=TYPE_SEGMENT, text_color=TEXT, anchor="w").pack(side="left")
        tool_button(bar, "Close", self.close_details, 64).pack(side="right")
        self.panel_body = ctk.CTkScrollableFrame(self.panel, fg_color=PANEL, corner_radius=0, scrollbar_button_color=SCROLL,
                                                 scrollbar_button_hover_color=MUTED)
        self.panel_body.pack(fill="both", expand=True, padx=(10, 4), pady=(0, 10))
        self.panel_open = False
        self.actions = {}   # the buttons of the open panel, by action key (so the tests can press them)

        for n in ("filter", "min_pages", "max_pages", "small_mb", "big_mb", "low_cover", *CHECK_VAR.values()):
            self.vars[n].trace_add("write", lambda *_: self._later())
        self.watch("with_orders", callback=self._orders_toggled)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._sync_buttons())
        self._refresh()

    # ------------------------------------------------------------------ theme and folder
    def apply_theme(self):
        super().apply_theme()
        self.table.apply_theme()
        self._style_chips()

    def browse(self):
        d = filedialog.askdirectory(title="Library folder")
        if d:
            self.set_folder(d)

    def browse_files(self):
        files = filedialog.askopenfilenames(title="Choose comics to audit", filetypes=[
            ("Comic archives", "*.cbz *.cbr"), ("All", "*.*")])
        if files:
            self.set_files(files)

    def set_files(self, paths):
        """Audit just these comics (duplicates and gaps are then judged among them only)."""
        if self.q:
            return
        files = picked_files(paths, COMIC_EXT)
        if not files:
            self.say("None of those files are .cbz or .cbr comics.", err=True)
            return
        self.set_folder(common_root(files), files)
        self.drop.set(f"{_plural(len(files), 'comic')} chosen from {self.root_dir}")

    def set_folder(self, folder, picked=None):
        if self.q:
            return
        self.root_dir = Path(folder)
        self.picked = picked
        self.drop.set(str(self.root_dir))
        self.results = None
        self.ticks = {}
        self._folded = False
        self.s1.set_open(True)
        self.s2.set_open(True)
        self.close_details()
        self.say("")
        self._refresh()

    def stop_action(self):
        if self.q:
            self.stop.set()

    def _open(self, key, view=None):
        if self.open_tool:
            self.open_tool(key, view)

    # ------------------------------------------------------------------ ignore list (kept as JSON in a setting)
    def ignored(self):
        """{key: label} of everything the user has chosen to ignore."""
        try:
            data = json.loads(self.vars["ignored"].get() or "{}")
            return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
        except ValueError:
            return {}

    def _set_ignored(self, d):
        self.vars["ignored"].set(json.dumps(d))

    def ignore_selected(self):
        sel = self.selected()
        if not sel or self.q:
            return
        d = self.ignored()
        for f in sel:
            for k in f.keys:
                d[k] = f.label
        self._set_ignored(d)
        self._refresh()
        self.say(f"Ignored {_plural(len(sel), 'finding')}. Ignored… lists what you've hidden.")

    def selected(self):
        return [self.rows[i] for i in self.table.selected() if i < len(self.rows)]

    def show_ignored(self):
        d = self.ignored()
        win = ctk.CTkToplevel(self)
        win.title("Ignored findings")
        win.geometry("560x420")
        win.configure(fg_color=BG)
        win.transient(self.winfo_toplevel())
        ctk.CTkLabel(win, text="These are hidden from every scan until you restore them.", font=(FONT, 12),
                     text_color=MUTED, anchor="w").pack(fill="x", padx=14, pady=(12, 6))
        box = tk.Listbox(win, selectmode="extended", activestyle="none", exportselection=False, font=(FONT, 11), bd=0,
                         highlightthickness=1, bg=pick(BG), fg=pick(TEXT), selectbackground=pick(ACCENT),
                         highlightbackground=pick(BORDER))
        box.pack(fill="both", expand=True, padx=14)
        labels = []

        def fill():
            labels[:] = list(dict.fromkeys(d.values()))
            box.delete(0, "end")
            for lab in labels:
                box.insert("end", lab)

        def restore(only_selected):
            chosen = {labels[i] for i in box.curselection()} if only_selected else set(labels)
            for k in [k for k, lab in d.items() if lab in chosen]:
                del d[k]
            self._set_ignored(d)
            fill()
            self._refresh()

        row = ctk.CTkFrame(win, fg_color=BG)
        row.pack(fill="x", padx=14, pady=10)
        button(row, "Restore selected", lambda: restore(True), width=140).pack(side="left")
        button(row, "Restore all", lambda: restore(False), width=110).pack(side="left", padx=6)
        button(row, "Close", win.destroy, width=90).pack(side="right")
        fill()
        self._ignored_win = win
        self._ignored_ui = {"box": box, "restore": restore, "labels": labels}

    # ------------------------------------------------------------------ the Archive folders
    def show_archive(self):
        if not self.root_dir:
            return
        root = self.root_dir
        win = ctk.CTkToplevel(self)
        win.title("Archive folders")
        win.geometry("760x520")
        win.configure(fg_color=BG)
        win.transient(self.winfo_toplevel())
        info = ctk.CTkLabel(win, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        info.pack(fill="x", padx=14, pady=(12, 6))
        wrap, tree = build_tree(win, [("sel", "", 38, False), ("file", "File", 520, True), ("size", "Size", 90, False)],
                                selectmode="extended")
        wrap.pack(fill="both", expand=True, padx=14)
        ticked, rows = set(), {}
        ctk.CTkLabel(win, text="Fixes park files here as .bak. Purging deletes them for good (they do not go to the "
                               "Recycle Bin).", font=(FONT, 12), text_color=MUTED, anchor="w", justify="left",
                     wraplength=700).pack(fill="x", padx=14, pady=(6, 0))

        def fill():
            tree.delete(*tree.get_children())
            rows.clear()
            files = ac.archive_files(root)
            for p, size in files:
                iid = tree.insert("", "end", values=("☑" if p in ticked else "☐", str(p.relative_to(root)),
                                                     ac.size_text(size)))
                rows[iid] = p
            total = sum(s for _, s in files)
            n = len(files)
            info.configure(text=f"{n} file{'s' if n != 1 else ''} in Archive folders, {ac.size_text(total)}" if n
                           else "The Archive folders are empty.")
            btn_purge.configure(state="normal" if ticked & set(rows.values()) else "disabled")

        def click(e):
            if tree.identify_region(e.x, e.y) == "cell" and tree.identify_column(e.x) == "#1":
                p = rows.get(tree.identify_row(e.y))
                if p:
                    ticked.symmetric_difference_update({p})
                    tree.set(tree.identify_row(e.y), "sel", "☑" if p in ticked else "☐")
                    btn_purge.configure(state="normal" if ticked & set(rows.values()) else "disabled")
                    return "break"
            return None

        def tick(value):
            ticked.clear()
            if value:
                ticked.update(rows.values())
            fill()

        def purge():
            todo = sorted(ticked & set(rows.values()))
            if not todo:
                return
            size = sum(p.stat().st_size for p in todo if p.exists())
            if not messagebox.askyesno("Purge Archive", f"Permanently delete {len(todo)} file"
                                       f"{'s' if len(todo) != 1 else ''} ({ac.size_text(size)})?\n\n"
                                       "This cannot be undone.", icon="warning", parent=win):
                return
            n, errors = ac.purge_archive(todo)
            ticked.clear()
            fill()
            self.say(f"Purged {n} file{'s' if n != 1 else ''}" + (f" · {len(errors)} failed ({errors[0]})" if errors else ""),
                     err=bool(errors))

        tree.bind("<Button-1>", click)
        row = ctk.CTkFrame(win, fg_color=BG)
        row.pack(fill="x", padx=14, pady=10)
        button(row, "Tick all", lambda: tick(True), width=90).pack(side="left")
        button(row, "Untick all", lambda: tick(False), width=90).pack(side="left", padx=6)
        btn_purge = button(row, "Purge ticked…", purge, width=130)
        btn_purge.pack(side="left", padx=6)
        button(row, "Open folder", lambda: os.startfile(root), width=110).pack(side="left")
        button(row, "Close", win.destroy, width=90).pack(side="right")
        fill()
        self._archive_win = win
        self._archive = {"tree": tree, "rows": rows, "ticked": ticked, "purge": purge, "fill": fill, "info": info}

    # ------------------------------------------------------------------ scanning
    def scan(self):
        if not self.root_dir or self.q:
            return
        self.results = None
        self.findings = []
        self.stop.clear()
        self.q = queue.Queue()
        self.progress.set(0)
        self.close_details()
        self.busy_text = "Scanning…"
        self.scan_text.configure(text="Scanning…")
        self._refresh()
        snapshot = ReadingOrders.from_dict(self.orders.to_dict())   # the worker reads its own copy
        threading.Thread(target=_run, args=(self.q, self.root_dir, self.state(), self.stop, self.picked, snapshot),
                         daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(100):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "prog":
                    self.progress.set(msg[2] / max(1, msg[3]))
                    self.busy_text = f"{msg[1]} {msg[2]:,} of {msg[3]:,}…"
                    self.scan_text.configure(text=self.busy_text)
                    self.bar_text.configure(text=self.busy_text)
                elif kind == "error":
                    self.q = None
                    self.progress.set(0)
                    self.scan_text.configure(text="")
                    self._refresh()
                    self.say(f"Scan failed: {msg[1]}", err=True)
                    return
                elif kind == "result":
                    self._finish(msg[1])
                    return
                elif kind == "fixed":
                    self.fixed += 1
                    self.fail_notes.pop(str(msg[1]).lower(), None)
                elif kind == "fix_failed":
                    self.failed += 1
                    self.fail_notes[str(msg[1]).lower()] = msg[3]
                    self.first_error = self.first_error or f"{Path(msg[1]).name}: {msg[3]}"
                elif kind in ("fix_done", "fix_stopped"):
                    self._finish_fix(kind == "fix_stopped")
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish(self, res):
        self.q = None
        self.results = res
        self.progress.set(0 if res["stopped"] else 1)
        self.scan_text.configure(text="")
        self._refresh()
        note = f"{_plural(len(res['issues']), 'file')} in {res['seconds']:.1f}s"
        if res["cache_hits"]:
            note += f" ({res['cache_hits']} from cache)"
        text = ("Stopped · " if res["stopped"] else "Done · ") + note
        self.say((self._fix_note + " · " if self._fix_note else "") + text, err=bool(self._fix_note and self.failed))
        self._fix_note = ""
        if not self._folded and not res["stopped"]:
            self._folded = True
            if self.auto.get():   # the settings are done with: fold them away and show the findings
                self.s1.set_open(False)
                self.s2.set_open(False)
                self.s3.set_open(True)
                self.update_idletasks()
                self.reveal(self.s3)

    # ------------------------------------------------------------------ the list
    def _later(self):
        if self._later_id is not None:
            self.after_cancel(self._later_id)
        self._later_id = self.after(250, self._refresh)

    def _on(self, kind):
        """Is the check for this kind of finding switched on?"""
        name = CHECK_VAR.get(kind)
        return True if name is None else bool(self.vars[name].get())

    def _data(self):
        res = self.results
        lim = ac.limits_from(self.state())
        return {**res, "quality": ac.find_quality(res["issues"], lim)}

    def _tick_id(self, f):
        return (f.kind, str(f.path).lower() if f.path else f.key)

    def _build(self):
        if not self.results:
            self.findings = []
            return
        found = ac.build_findings(self._data(), self.ignored())
        self.findings = [f for f in found if self._on(f.kind)]
        for f in self.findings:
            if f.fix:
                f.checked = self.ticks.get(self._tick_id(f), f.checked)
            note = self.fail_notes.get(str(f.path).lower()) if f.path else None
            if note and f.fix:
                f.detail += f" · Fix failed: {note}"

    def visible(self):
        flt = self.vars["filter"].get()
        return [f for f in self.findings if (f.kind not in (ac.WARNING, ac.ORDER) if flt == ALL else f.kind == flt)]

    def _counts(self):
        counts = {k: 0 for k in FILTERS}
        seen = set()
        for f in self.findings:
            if f.kind == ac.DUPLICATE:
                if f.group in seen:
                    continue
                seen.add(f.group)
            counts[f.kind] += f.count
            if f.kind not in (ac.WARNING, ac.ORDER):
                counts[ALL] += f.count
        return counts

    def _style_chips(self):
        flt = self.vars["filter"].get()
        for key, b in self.chips.items():
            b.configure(fg_color=PINK if key == flt else RAISED, text_color=ON_ACCENT if key == flt else TEXT)

    def _shown_chip(self, key, counts):
        if key == ALL:
            return True
        if key == ac.ORDER:
            return bool(len(self.orders) or counts[ac.ORDER])
        return self._on(key)

    def _draw_strip(self, counts):
        """The summary strip: "3 broken files · 12 groups of duplicates · …", each part selecting its list."""
        parts = [(k, _plural(counts[k], WORD[k][0]) if counts[k] == 1 else f"{counts[k]:,} {WORD[k][1]}")
                 for k, _n, _l in CHECKS if self._on(k) and counts[k]]
        sig = (bool(self.results), tuple(parts))
        if sig == self._strip_sig:
            return
        self._strip_sig = sig
        for w in self.strip_box.winfo_children():
            w.destroy()
        items = []
        if not self.results:
            lab = ctk.CTkLabel(self.strip_box, text="Nothing scanned yet", font=TYPE_BODY, text_color=MUTED, anchor="w")
            items.append((lab, 150))
        elif not parts:
            lab = ctk.CTkLabel(self.strip_box, text="No problems found", font=(FONT, 13, "bold"), text_color=TEXT, anchor="w")
            items.append((lab, 150))
        self.strip_labels = {}
        for n, (kind, text) in enumerate(parts):
            shown = text + ("  ·" if n < len(parts) - 1 else "")
            lab = ctk.CTkLabel(self.strip_box, text=shown, font=(FONT, 13, "bold"), text_color=TEXT, cursor="hand2")
            lab.bind("<Button-1>", lambda _, k=kind: self.vars["filter"].set(k))
            self.strip_labels[kind] = lab
            items.append((lab, 8 * len(shown) + 14))
        self._flow(self.strip_box, items)

    def _flow(self, frame, items):
        """Lay `items` [(widget, estimated width)] out in rows that wrap at the width of `frame`."""
        self._flows[frame] = (items, 0)
        self._reflow(frame, frame.winfo_width(), force=True)

    def _reflow(self, frame, width, force=False):
        items, last = self._flows.get(frame, ([], 0))
        if not force and abs(width - last) < 8:
            return
        self._flows[frame] = (items, width)
        avail = max(160, width / frame._get_widget_scaling() - 6)
        x = row = col = 0
        for w, est in items:
            if col and x + est > avail:
                row, col, x = row + 1, 0, 0
            w.grid(row=row, column=col, sticky="w", padx=(0, 4), pady=(0, 4))
            x += est + 4
            col += 1

    @staticmethod
    def _values(f):
        return (("☑" if f.checked else "☐") if f.fix else "", f.kind, f.title, f.detail)

    def _refresh(self):
        self._later_id = None
        self._build()
        counts = self._counts()
        flt = self.vars["filter"].get()
        if flt != ALL and not self._shown_chip(flt, counts):
            flt = ALL
            self.vars["filter"].set(ALL)
        shown = []
        for key, label in CHIPS:
            b = self.chips[key]
            b.grid_forget()
            if self._shown_chip(key, counts):
                text = f"{label} {counts[key]}" if self.results else label
                width = max(60, 22 + 8 * len(text))
                b.configure(text=text, width=width)
                shown.append((b, width + 8))
        self._flow(self.chip_bar, shown)
        self._style_chips()
        self._draw_strip(counts)
        self.rows = rows = self.visible()
        self.table.box.set_empty(EMPTY[flt] if self.results else "Scan the library to see what needs attention.")
        self.table.set_rows([self._values(f) for f in rows],
                            tags=[("bad",) if f.kind == ac.BROKEN else ("dim",) if f.keep or f.kind in (ac.WARNING, ac.ORDER)
                                  else () for f in rows])
        res = self.results
        if not res:
            self.meta.configure(text="Choose a folder, then press Scan library." if not self.root_dir else
                                ("" if self.q else "Press Scan library to begin."))
        else:
            n = counts[flt]
            one, more = WORD[flt]
            text = f"{n:,} {one if n == 1 else more}" if n else EMPTY[flt]
            fixable = sum(1 for f in rows if f.checked and f.fix)
            if fixable:
                text += f" · {fixable} ticked to fix"
            if res["stopped"]:
                text += " (partial: scan was stopped)"
            self.meta.configure(text=text)
        hint = HINTS[flt]
        if flt == ac.MISSING and res:
            hint += f" {res['ignored_files']} file(s) skipped: specials, annuals, decimals or no number."
        self.hint.configure(text=hint)
        self._orders_note()
        self._extras_row(flt)
        if self.panel_open:
            self._fill_details()
        self._sync()

    def _orders_note(self):
        res = self.results
        if res:
            left = res.get("left_out", 0)
            text = (f"{_plural(left, 'comic')} left out of Duplicates" if left and not self.vars["with_orders"].get()
                    else ("included" if self.vars["with_orders"].get() and res.get("orders") else ""))
        else:
            n = len(self.orders)
            text = f"{_plural(n, 'folder')} marked" if n else "none marked yet: mark them in Library stats"
        if self.orders_note.cget("text") != text:
            self.orders_note.configure(text=text)

    def _orders_toggled(self):
        if self.results:
            self.say("Rescan to apply the change to Duplicates.")
        self._sync()

    def _extras_row(self, flt):
        for b in (self.btn_copy, self.btn_save, self.btn_convert):
            b.pack_forget()
        have = bool(self.results) and not self.q
        if flt == ac.MISSING:
            self.btn_copy.pack(side="left", padx=(0, 6))
            self.btn_save.pack(side="left")
            for b in (self.btn_copy, self.btn_save):
                b.configure(state="normal" if have and any(f.kind == ac.MISSING for f in self.findings) else "disabled")
        elif flt == ac.CBR:
            self.btn_convert.pack(side="left")
            self.btn_convert.configure(state="normal" if have and self.open_tool and any(f.kind == ac.CBR for f in self.findings)
                                       else "disabled")

    def _sync_buttons(self):
        busy = bool(self.q)
        ok = bool(self.results) and not busy
        sel = self.selected()
        self.btn_ignore.configure(state="normal" if ok and sel else "disabled")
        self.btn_open.configure(state="normal" if sel and sel[0].path else "disabled")
        self._sync()

    # ------------------------------------------------------------------ segments and footer
    def _sync(self):
        busy, res, root = bool(self.q), self.results, self.root_dir
        s1, s2, s3 = self.s1, self.s2, self.s3
        counts = self._counts()
        on = sum(1 for _k, name, _l in CHECKS if self.vars[name].get())
        extra = ([f"covers {self.vars['similarity'].get().split(' ')[0].lower()}"] if self.vars["similar"].get() else []) + \
                (["integrity test"] if self.vars["integrity"].get() else [])
        s2.set_summary(" · ".join([_plural(on, "check")] + extra))
        s1.set_summary(str(root) if root else "")
        if not res:
            s1.set_state("active")
            s2.set_state("idle")
            s3.set_state("locked")
            s3.set_summary("")
        else:
            s1.set_state("done")
            s2.set_state("done")
            s3.set_state("active" if counts[ALL] else "done")
            s3.set_summary(_plural(counts[ALL], "problem") if counts[ALL] else "Nothing to fix")
        if busy:
            self.set_footer(self.busy_text or "Working…", "Stop", self.stop.set)
            return
        status = self.status.cget("text")
        if not res:
            self.set_footer(status or ("Press Scan library to begin." if root else "Choose a library folder."),
                            "Scan library", self.scan, enabled=bool(root))
            return
        n = sum(1 for f in self.visible() if f.checked and f.fix)
        self.set_footer(status or (f"{n} ticked to fix" if n else "Tick what to fix, or open Details."),
                        f"Fix {n} checked" if n else "Fix checked", self.fix_checked, enabled=n > 0,
                        secondary=[("Rescan", self.scan), ("Ignored…", self.show_ignored), ("Archive…", self.show_archive)])

    def say(self, msg, err=False):
        super().say(msg, err)
        if hasattr(self, "s3") and not self.q:
            self._sync()

    # ------------------------------------------------------------------ the Details panel
    def toggle_details(self):
        if self.panel_open:
            self.close_details()
        else:
            self.show_details()

    def show_details(self):
        if not self.results:
            self.say("Scan the library first; the details describe that scan.")
            return
        self._fill_details()
        self.update_idletasks()
        # (customtkinter's own place() refuses a height, so go through tkinter's; the panel covers the right half down to the footer)
        tk.Frame.place_configure(self.panel, relx=1.0, y=0, anchor="ne", relwidth=0.5, relheight=1.0,
                                 height=-self.footer.winfo_height())
        self.panel.lift()
        self.panel_open = True

    def close_details(self):
        self.panel.place_forget()
        self.panel_open = False

    def _fill_details(self):
        for w in self.panel_body.winfo_children():
            w.destroy()
        self.actions = {}
        res = self.results
        if not res:
            return
        checks = [k for k, name, _l in CHECKS if self.vars[name].get()]
        d = ac.build_details(res, self._counts(), len(self.ignored()), bool(self.vars["with_orders"].get()), checks)
        section(self.panel_body, "This scan").pack(fill="x", pady=(0, 8), padx=(0, 10))
        rows = facts(self.panel_body, [k for k, _t in d["scan"]], wrap=330)
        for k, text in d["scan"]:
            rows[k].configure(text=text)
        rows["_grid"].pack(fill="x", pady=(0, 16), padx=(0, 10))
        section(self.panel_body, "What was found, and what to do").pack(fill="x", pady=(0, 8), padx=(0, 10))
        for item in d["found"]:
            box = ctk.CTkFrame(self.panel_body, fg_color=RAISED, border_color=BORDER, border_width=EDGE, corner_radius=0)
            box.pack(fill="x", pady=(0, 10), padx=(0, 10))
            ctk.CTkLabel(box, text=item["title"], font=(FONT, 13, "bold"), text_color=TEXT, anchor="w", justify="left",
                         wraplength=360).pack(fill="x", padx=12, pady=(10, 2))
            ctk.CTkLabel(box, text=item["text"], font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                         wraplength=360).pack(fill="x", padx=12)
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=(8, 10))
            for label, action in item["actions"]:
                b = tool_button(row, label, lambda a=action: self._detail_action(a), max(90, 24 + 8 * len(label)))
                b.pack(side="left", padx=(0, 6), pady=(0, 4))
                self.actions[(item["kind"], action)] = b

    def _detail_action(self, action):
        """A button of the Details panel: show a list here, or open the tool that fixes that kind of problem."""
        head, _, rest = action.partition(":")
        self.close_details()
        if head == "show":
            self.vars["filter"].set(rest)
            self.s3.set_open(True)
            self._refresh()
            self.update_idletasks()
            self.reveal(self.s3)
        elif head == "tool":
            key, _, view = rest.partition(":")
            self._open(key, view or None)

    # ------------------------------------------------------------------ ticking and fixing
    def _click(self, e):
        iid = self.tree.identify_row(e.y)
        box = self.tree.bbox(iid, "sel") if iid else None   # (the table has a hidden picture column before "sel")
        if box and box[0] <= e.x < box[0] + box[2]:
            i = int(iid)
            if 0 <= i < len(self.rows):
                f = self.rows[i]
                if f.fix and not self.q:
                    f.checked = not f.checked
                    self.ticks[self._tick_id(f)] = f.checked
                    self.table.update_row(i, self._values(f))
                    self._refresh_meta()
                    return "break"
        return None

    def _refresh_meta(self):
        text = self.meta.cget("text").split(" · ")[0]
        fixable = sum(1 for f in self.visible() if f.checked and f.fix)
        self.meta.configure(text=text + (f" · {fixable} ticked to fix" if fixable else ""))
        self._sync_buttons()

    def tick_all(self, value):
        if self.q:
            return
        for f in self.visible():
            if f.fix:
                f.checked = value
                self.ticks[self._tick_id(f)] = value
        self._refresh()

    def open_selected(self):
        sel = self.selected()
        if sel and sel[0].path:
            reveal(sel[0].path)

    def _confirm_fix(self, plan):
        """Ask before fixing: what will happen in a few lines, and a Details button listing every file, where it goes
        and whether that can be undone. Returns True to go ahead."""
        lines = ac.plan_lines(plan)
        desc = ac.describe_plan(plan, self.root_dir)
        final = any(not undo for *_x, undo in desc)
        win = ctk.CTkToplevel(self)
        win.title("Fix checked")
        win.geometry("760x270")
        win.configure(fg_color=BG)
        win.transient(self.winfo_toplevel())
        ctk.CTkLabel(win, text="This will:", font=(FONT, 14, "bold"), text_color=TEXT, anchor="w").pack(fill="x", padx=18, pady=(16, 6))
        for line in lines:
            ctk.CTkLabel(win, text="•  " + line, font=TYPE_BODY, text_color=TEXT, anchor="w", justify="left",
                         wraplength=720).pack(fill="x", padx=18)
        ctk.CTkLabel(win, text=("Moving a file to Archive can be undone (move the .bak back and drop the suffix). "
                                + ("Deleting a .cbr after its conversion and removing junk cannot be undone." if final else "")).strip(),
                     font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=720).pack(fill="x", padx=18, pady=(8, 0))
        box, tree = build_tree(win, [("file", "File", 300, True), ("where", "What happens", 330, True), ("undo", "Undo", 60, False)],
                               selectmode="browse")
        for name, where, undo in desc:
            tree.insert("", "end", values=(name, where, "yes" if undo else "no"))
        result = {"ok": False, "shown": False}
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(side="bottom", fill="x", padx=18, pady=14)

        def finish(ok):
            result["ok"] = ok
            win.destroy()

        def details():
            result["shown"] = not result["shown"]
            if result["shown"]:
                win.geometry("760x520")
                box.pack(fill="both", expand=True, padx=18, pady=(10, 0), before=row)
            else:
                box.pack_forget()
                win.geometry("760x270")
            b_details.configure(text="Hide details" if result["shown"] else "Details")

        b_details = tool_button(row, "Details", details, 100)
        b_details.pack(side="left")
        b_ok = button(row, f"Fix {_plural(len(plan), 'file')}", lambda: finish(True), primary=True, width=170)
        b_ok.pack(side="right")
        b_cancel = tool_button(row, "Cancel", lambda: finish(False), 90)
        b_cancel.pack(side="right", padx=(0, 10))
        win.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        self._fix_dialog = {"win": win, "details": b_details, "ok": b_ok, "cancel": b_cancel, "tree": tree, "box": box,
                            "lines": lines}
        try:
            win.grab_set()
        except tk.TclError:
            pass
        self.wait_window(win)
        return result["ok"]

    def fix_checked(self):
        if not self.results or self.q:
            return
        plan = ac.plan_fixes(self.visible())
        if not plan:
            return
        if not self._confirm_fix(plan):
            return
        self.fixed = self.failed = 0
        self.first_error = ""
        for path, _, _ in plan:
            self.fail_notes.pop(str(path).lower(), None)
        self.stop.clear()
        self.q = queue.Queue()
        self.progress.set(0)
        self.busy_text = "Fixing…"
        self.say("")
        self._sync()
        threading.Thread(target=_fix, args=(self.q, plan, self.stop), daemon=True).start()
        self._poll()

    def _finish_fix(self, stopped):
        self.q = None
        text = f"Fixed {_plural(self.fixed, 'file')}"
        if self.failed:
            text += f" · {self.failed} failed ({self.first_error})"
        if stopped:
            text = "Stopped · " + text
        self._fix_note = text
        self.say(text, err=bool(self.failed))
        self.scan()  # the cache makes this quick; it also shows what is left and clears what was fixed
        if not self.q:  # no folder to rescan
            self._refresh()

    # ------------------------------------------------------------------ wishlist
    def _gaps(self):
        return [g for f in self.findings if f.kind == ac.MISSING for g in f.gaps]

    def _lines(self):
        ign = set(self.ignored())
        out = []
        for g in self._gaps():
            nums = [n for n in g.missing if ac.missing_key(g, n) not in ign]
            out += ac.wishlist_lines([ac.Gap(g.series, g.volume, g.owned, g.first, g.last, nums, g.from_count, g.kind)])
        return out

    def copy_wishlist(self):
        lines = self._lines()
        if lines:
            self.clipboard_clear()
            self.clipboard_append("\n".join(lines))
            self.say(f"Copied {len(lines)} wishlist line{'s' if len(lines) != 1 else ''}.")

    def save_wishlist(self):
        lines = self._lines()
        if not lines:
            return
        path = filedialog.asksaveasfilename(title="Save wishlist", defaultextension=".txt", initialfile="wishlist.txt",
                                            filetypes=[("Text", "*.txt"), ("CSV", "*.csv")])
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                ign = set(self.ignored())
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow(["Series", "Volume", "Type", "Number"])
                    for g in self._gaps():
                        w.writerows([g.series, g.volume, g.kind, n] for n in g.missing if ac.missing_key(g, n) not in ign)
            else:
                Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.say(f"Saved {len(lines)} lines.")
        except OSError as e:
            self.say(f"Could not save: {e}", err=True)

"""Library audit page: scan a library once, see every problem in one list (broken files, duplicates, missing
issues, junk files, CBR files, warnings), tick what to fix and fix it. Findings can be ignored for good, and the
Archive folders that fixes fill up can be reviewed and purged."""
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
from library_scan import scan_library
from ui_kit import (PINK, RAISED, ON_ACCENT, Toggle, ACCENT, BG, BORDER, FONT, MUTED, TEXT, DropZone, Page, apply_tree_theme, build_tree,
                    button, divider, entry, menu, pick, switch_style, title_block, tool_button, toolbar)

ALL = "All"
CHIPS = [(ALL, "All"), (ac.BROKEN, "Broken"), (ac.DUPLICATE, "Duplicates"), (ac.MISSING, "Missing"),
         (ac.JUNK, "Junk"), (ac.CBR, "CBR"), (ac.WARNING, "Warnings")]
FILTERS = [c[0] for c in CHIPS]
COLUMNS = [("sel", "", 38, False), ("kind", "Type", 84, False), ("what", "File or series", 300, True),
           ("detail", "Details", 380, True)]
EMPTY = {ALL: "No problems found.", ac.BROKEN: "No broken files found.", ac.DUPLICATE: "No duplicates found.",
         ac.MISSING: "No gaps found.", ac.JUNK: "No junk files found.", ac.CBR: "No CBR files found.",
         ac.WARNING: "Nothing to warn about."}
HINTS = {
    ALL: "Everything except warnings. Junk files and CBR files are ticked for fixing; tick anything else you want fixed, "
         "then press Fix checked.",
    ac.BROKEN: "Files that would not open or failed the integrity test. Fixing one moves it to an Archive folder (as .bak).",
    ac.DUPLICATE: "The best copy of each group (most pages, then the taller cover, then the larger file) is kept. Tick the "
                  "others to move them to an Archive folder (as .bak); nothing is deleted.",
    ac.MISSING: "Gaps are tracked separately for issues and for each kind of collected edition. Ignore hides what a row "
                "shows; numbers that go missing later still appear.",
    ac.JUNK: "Thumbs.db, .nfo, __MACOSX and the like. ComicInfo.xml is always kept.",
    ac.CBR: "Fixing converts to a verified CBZ, removes its junk, then deletes the .cbr.",
    ac.WARNING: "Unusual page counts, file sizes and cover resolutions. Nothing to fix automatically; change the limits "
                "under Warnings in the options.",
}


def reveal(path):
    """Show a file in Windows Explorer."""
    try:
        subprocess.Popen(["explorer", "/select,", str(path)])
    except OSError:
        pass


def _run(q, root, o, stop, only=None):
    """Worker: scan, optionally test integrity, then find duplicates and gaps. No Tk calls."""
    try:
        _audit(q, root, o, stop, only)
    except Exception as e:  # noqa: BLE001 - whatever goes wrong, the page must stop waiting
        q.put(("error", f"{type(e).__name__}: {e}"))


def _audit(q, root, o, stop, only=None):
    res = scan_library(root, o["recursive"], deep=True, deep_cbr=o["deep_cbr"],
                       progress=lambda d, t, i: q.put(("prog", "Scanning", d, t)), stop=stop, only=only)
    issues = res.issues
    broken = []
    if o["integrity"] and not res.stopped:
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
    dups = ac.find_duplicates(issues, o["similar"], ac.SIMILARITY[o["similarity"]])
    gaps, ignored = ac.find_missing(issues, o["from_one"])
    q.put(("result", {"issues": issues, "broken": broken, "dups": dups, "gaps": gaps, "ignored_files": ignored,
                      "junk": ac.find_junk(issues), "cbr": ac.find_cbr(issues), "stopped": res.stopped,
                      "seconds": res.seconds, "integrity": o["integrity"], "cache_hits": res.cache_hits}))


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


class AuditPage(Page):
    defaults = {"recursive": True, "deep_cbr": False, "integrity": False, "similar": False, "similarity": "Normal",
                "from_one": False, "filter": ALL, "min_pages": "10", "max_pages": "300", "small_mb": "1",
                "big_mb": "500", "low_cover": "800", "ignored": ""}
    choices = {"similarity": list(ac.SIMILARITY), "filter": FILTERS}

    def __init__(self, parent):
        super().__init__(parent)
        self.root_dir = None
        self.picked = None  # comics chosen one by one instead of a folder
        self.results = None
        self.findings = []
        self.q = None
        self.stop = threading.Event()
        self.ticks = {}  # (kind, key) -> ticked, remembered across list refreshes
        self.fail_notes = {}  # lower-cased path -> why the last fix failed
        self.by_iid = {}
        self._fix_note = ""
        self._later_id = None
        self.fixed = self.failed = 0
        self.first_error = ""

        title_block(self.main, "Library audit", "Scan your library, see what needs attention, and fix it.")
        self.drop = DropZone(self.main, "Drop a library folder here, or add a folder or comics below", self.browse,
                             self.browse, self.browse_files)
        self.drop.pack(fill="x")
        bar = ctk.CTkFrame(self.main, fg_color=BG)
        bar.pack(fill="x", pady=(14, 6))
        self.chips = {}
        for key, label in CHIPS:
            b = tool_button(bar, label, lambda k=key: self.vars["filter"].set(k), max(70, 24 + 9 * len(label)))
            b.pack(side="left", padx=(0, 4))
            self.chips[key] = b
        toolbar(bar, [("all", "Tick all", 74, lambda: self.tick_all(True)),
                      ("none", "Untick all", 80, lambda: self.tick_all(False))], side="right")
        self.meta = ctk.CTkLabel(self.main, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(2, 6))
        self.progress = ctk.CTkProgressBar(self.main, height=14, corner_radius=0, border_width=3, border_color=BORDER, fg_color=BORDER, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        wrap, self.tree = build_tree(self.main, COLUMNS, selectmode="extended")
        wrap.pack(fill="both", expand=True)
        wrap.set_empty("Press Scan library to check your collection. Problems appear here.")
        self.tree.bind("<Button-1>", self._click)
        self.hint = ctk.CTkLabel(self.main, text="", font=(FONT, 12), text_color=MUTED, anchor="w", justify="left",
                                 wraplength=620)
        self.hint.pack(fill="x", pady=(6, 0))

        v, sw = self.vars, switch_style()
        self.form.heading("Source")
        box = self.form.add("Scan")
        Toggle(box, text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        Toggle(box, text="Open real .cbr files (slow)", variable=v["deep_cbr"], **sw).pack(anchor="w", pady=(8, 0))
        self.form.heading("Checks")
        box = self.form.add("Broken files")
        Toggle(box, text="Full integrity test (slow)", variable=v["integrity"], **sw).pack(anchor="w")
        ctk.CTkLabel(box, text="Reads every file completely. Off: only problems the scan notices.", font=(FONT, 11),
                     text_color=MUTED, anchor="w", justify="left", wraplength=260).pack(fill="x", pady=(4, 0))
        box = self.form.add("Duplicates")
        Toggle(box, text="Compare cover images", variable=v["similar"], **sw).pack(anchor="w")
        menu(box, v["similarity"], list(ac.SIMILARITY)).pack(fill="x", pady=(8, 0))
        box = self.form.add("Missing")
        Toggle(box, text="Expect issues from #1", variable=v["from_one"], **sw).pack(anchor="w")
        ctk.CTkLabel(box, text="Off: a series is checked from the lowest number you own.", font=(FONT, 11),
                     text_color=MUTED, anchor="w", justify="left", wraplength=260).pack(fill="x", pady=(4, 0))
        self.form.heading("Warnings", collapsible=True, open=False)
        for key, label in (("min_pages", "Fewer pages than"), ("max_pages", "More pages than"),
                           ("small_mb", "Smaller than (MB)"), ("big_mb", "Larger than (MB)"),
                           ("low_cover", "Cover shorter than (px)")):
            entry(self.form.add(label), v[key]).pack(fill="x")

        self.btn_scan = button(self.footer, "Scan library", self.scan, primary=True)
        self.btn_scan.pack(pady=(0, 8))
        self.btn_fix = button(self.footer, "Fix checked", self.fix_checked, color=PINK)
        self.btn_fix.pack(pady=(0, 8))
        divider(self.footer, vertical=False).pack(fill="x", pady=(2, 8))
        self.btn_ignore, self.btn_open = self._pair(self.footer, ("Ignore", self.ignore_selected),
                                                    ("Open folder", self.open_selected))
        self.btn_ignored, self.btn_archive = self._pair(self.footer, ("Ignored…", self.show_ignored),
                                                        ("Archive…", self.show_archive))
        self.wish_row = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.btn_copy = button(self.wish_row, "Copy wishlist", self.copy_wishlist, width=108)
        self.btn_copy.pack(side="left", padx=(0, 6))
        self.btn_save = button(self.wish_row, "Save wishlist…", self.save_wishlist, width=108)
        self.btn_save.pack(side="left")
        self.btn_stop = button(self.footer, "Stop", self.stop.set)

        for n in ("filter", "min_pages", "max_pages", "small_mb", "big_mb", "low_cover"):
            self.vars[n].trace_add("write", lambda *_: self._later())
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._sync_buttons())
        self._refresh()

    def _pair(self, parent, a, b):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(pady=(0, 8))
        ba = button(row, a[0], a[1], width=108)
        ba.pack(side="left", padx=(0, 6))
        bb = button(row, b[0], b[1], width=108)
        bb.pack(side="left")
        return ba, bb

    # ------------------------------------------------------------------ theme and folder
    def apply_theme(self):
        apply_tree_theme(self.tree)
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
        self.drop.set(f"{len(files)} comic{'s' if len(files) != 1 else ''} chosen from {self.root_dir}")

    def set_folder(self, folder, picked=None):
        if self.q:
            return
        self.root_dir = Path(folder)
        self.picked = picked
        self.drop.set(str(self.root_dir))
        self.results = None
        self.ticks = {}
        self.say("")
        self._refresh()

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
        sel = [self.by_iid[i] for i in self.tree.selection() if i in self.by_iid]
        if not sel or self.q:
            return
        d = self.ignored()
        for f in sel:
            for k in f.keys:
                d[k] = f.label
        self._set_ignored(d)
        self._refresh()
        self.say(f"Ignored {len(sel)} finding{'s' if len(sel) != 1 else ''}. Ignored… lists what you've hidden.")

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
    def _idle(self):
        busy = bool(self.q)
        self.btn_scan.configure(state="normal" if self.root_dir and not busy else "disabled")
        self.btn_stop.pack_forget()
        if busy:
            self.btn_stop.pack()
        self._sync_buttons()

    def scan(self):
        if not self.root_dir or self.q:
            return
        self.results = None
        self.findings = []
        self.stop.clear()
        self.q = queue.Queue()
        self.progress.set(0)
        self._refresh()
        self.meta.configure(text="Scanning…")
        threading.Thread(target=_run, args=(self.q, self.root_dir, self.state(), self.stop, self.picked),
                         daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(100):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "prog":
                    self.progress.set(msg[2] / max(1, msg[3]))
                    self.meta.configure(text=f"{msg[1]} {msg[2]} of {msg[3]}…")
                elif kind == "error":
                    self.q = None
                    self.progress.set(0)
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
        self._refresh()
        note = f"{len(res['issues'])} files in {res['seconds']:.1f}s"
        if res["cache_hits"]:
            note += f" ({res['cache_hits']} from cache)"
        text = ("Stopped · " if res["stopped"] else "Done · ") + note
        self.say((self._fix_note + " · " if self._fix_note else "") + text, err=bool(self._fix_note and self.failed))
        self._fix_note = ""

    # ------------------------------------------------------------------ the list
    def _later(self):
        if self._later_id is not None:
            self.after_cancel(self._later_id)
        self._later_id = self.after(250, self._refresh)

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
        self.findings = ac.build_findings(self._data(), self.ignored())
        for f in self.findings:
            if f.fix:
                f.checked = self.ticks.get(self._tick_id(f), f.checked)
            note = self.fail_notes.get(str(f.path).lower()) if f.path else None
            if note and f.fix:
                f.detail += f" · Fix failed: {note}"

    def visible(self):
        flt = self.vars["filter"].get()
        return [f for f in self.findings if (f.kind != ac.WARNING if flt == ALL else f.kind == flt)]

    def _counts(self):
        counts = {k: 0 for k in FILTERS}
        seen = set()
        for f in self.findings:
            if f.kind == ac.DUPLICATE:
                if f.group in seen:
                    continue
                seen.add(f.group)
            counts[f.kind] += 1
            if f.kind != ac.WARNING:
                counts[ALL] += 1
        return counts

    def _style_chips(self):
        flt = self.vars["filter"].get()
        for key, b in self.chips.items():
            b.configure(fg_color=PINK if key == flt else RAISED, text_color=ON_ACCENT if key == flt else TEXT)

    def _refresh(self):
        self._later_id = None
        self._build()
        counts = self._counts()
        for key, label in CHIPS:
            self.chips[key].configure(text=f"{label} {counts[key]}" if self.results else label,
                                      width=max(60, 22 + 8 * len(f"{label} {counts[key]}")))
        self._style_chips()
        flt = self.vars["filter"].get()
        self.tree.delete(*self.tree.get_children())
        self.by_iid = {}
        rows = self.visible()
        for f in rows:
            sel = ("☑" if f.checked else "☐") if f.fix else ""
            tags = ("bad",) if f.kind == ac.BROKEN else ("dim",) if f.keep or f.kind == ac.WARNING else ()
            iid = self.tree.insert("", "end", values=(sel, f.kind, f.title, f.detail), tags=tags)
            self.by_iid[iid] = f
        res = self.results
        if not res:
            if not self.q:
                self.meta.configure(text="Choose a folder, then press Scan library." if not self.root_dir
                                    else "Press Scan library to begin.")
        else:
            n = counts[flt]
            word = {ALL: "problem", ac.BROKEN: "broken file", ac.DUPLICATE: "group of duplicates", ac.MISSING:
                    "series with gaps", ac.JUNK: "comic with junk", ac.CBR: "CBR file", ac.WARNING: "warning"}[flt]
            text = f"{n} {word}{'s' if n != 1 else ''}" if n else EMPTY[flt]
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
        self._idle()

    def _sync_buttons(self):
        busy = bool(self.q)
        rows = self.visible()
        ok = bool(self.results) and not busy
        self.btn_fix.configure(state="normal" if ok and any(f.checked and f.fix for f in rows) else "disabled")
        sel = [self.by_iid[i] for i in self.tree.selection() if i in self.by_iid]
        self.btn_ignore.configure(state="normal" if ok and sel else "disabled")
        self.btn_open.configure(state="normal" if sel and sel[0].path else "disabled")
        self.btn_ignored.configure(state="normal" if self.ignored() else "disabled")
        self.btn_archive.configure(state="normal" if self.root_dir and not busy else "disabled")
        show = self.vars["filter"].get() == ac.MISSING
        if show:
            self.wish_row.pack(pady=(0, 8))
        else:
            self.wish_row.pack_forget()
        have = ok and any(f.kind == ac.MISSING for f in self.findings)
        for b in (self.btn_copy, self.btn_save):
            b.configure(state="normal" if have else "disabled")

    # ------------------------------------------------------------------ ticking and fixing
    def _click(self, e):
        if self.tree.identify_region(e.x, e.y) == "cell" and self.tree.identify_column(e.x) == "#1":
            f = self.by_iid.get(self.tree.identify_row(e.y))
            if f and f.fix and not self.q:
                f.checked = not f.checked
                self.ticks[self._tick_id(f)] = f.checked
                self.tree.set(self.tree.identify_row(e.y), "sel", "☑" if f.checked else "☐")
                self._refresh_meta()
                return "break"
        return None

    def _refresh_meta(self):
        rows = self.visible()
        text = self.meta.cget("text").split(" · ")[0]
        fixable = sum(1 for f in rows if f.checked and f.fix)
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
        sel = [self.by_iid[i] for i in self.tree.selection() if i in self.by_iid]
        if sel and sel[0].path:
            reveal(sel[0].path)

    def fix_checked(self):
        if not self.results or self.q:
            return
        plan = ac.plan_fixes(self.visible())
        if not plan:
            return
        n = {a: sum(1 for _, x, _ in plan if x == a) for a in (ac.CLEAN, ac.CONVERT, ac.ARCHIVE)}
        lines = []
        if n[ac.CLEAN]:
            lines.append(f"• Remove junk files from {n[ac.CLEAN]} comic{'s' if n[ac.CLEAN] != 1 else ''}")
        if n[ac.CONVERT]:
            lines.append(f"• Convert {n[ac.CONVERT]} CBR file{'s' if n[ac.CONVERT] != 1 else ''} to CBZ (each .cbr is "
                         "deleted once its CBZ has been verified)")
        if n[ac.ARCHIVE]:
            lines.append(f"• Move {n[ac.ARCHIVE]} file{'s' if n[ac.ARCHIVE] != 1 else ''} to Archive folders (as .bak)")
        if not messagebox.askyesno("Fix checked", "This will:\n\n" + "\n".join(lines) + "\n\nContinue?", icon="warning"):
            return
        self.fixed = self.failed = 0
        self.first_error = ""
        for path, _, _ in plan:
            self.fail_notes.pop(str(path).lower(), None)
        self.stop.clear()
        self.q = queue.Queue()
        self.progress.set(0)
        self.say("")
        self._idle()
        threading.Thread(target=_fix, args=(self.q, plan, self.stop), daemon=True).start()
        self._poll()

    def _finish_fix(self, stopped):
        self.q = None
        text = f"Fixed {self.fixed} file{'s' if self.fixed != 1 else ''}"
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

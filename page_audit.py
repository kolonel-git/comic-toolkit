"""Library Audit page: scan a library once, then browse four reports (broken files, duplicates,
missing issues, quality). Reports never change files; the only action is moving checked
duplicates into an Archive folder as .bak backups."""
import csv
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import audit_core as ac
from archive_tools import move_to_archive
from library_scan import scan_library
from ui_kit import (ACCENT, BG, BORDER, FONT, MUTED, TEXT, DropZone, Page, apply_tree_theme, build_tree, button,
                    menu, segmented, switch_style, title_block)

BROKEN, DUPES, MISSING, QUALITY = "Broken", "Duplicates", "Missing", "Quality"
REPORTS = [BROKEN, DUPES, MISSING, QUALITY]
COLUMNS = {
    BROKEN: [("file", "File", 260, True), ("problem", "Problem", 300, True)],
    DUPES: [("sel", "", 38, False), ("group", "#", 40, False), ("why", "Why", 190, False),
            ("file", "File", 240, True), ("size", "Size", 74, False), ("pages", "Pages", 56, False)],
    MISSING: [("series", "Series", 220, True), ("volume", "Vol", 56, False), ("owned", "Owned", 62, False),
              ("missing", "Missing", 320, True)],
    QUALITY: [("file", "File", 260, True), ("flags", "Flags", 300, True)],
}
EMPTY = {BROKEN: "No broken files found.", DUPES: "No duplicates found.", MISSING: "No gaps found.",
         QUALITY: "Nothing flagged."}


def _run(q, root, o, stop):
    """Worker: scan, optionally test integrity, then compute all four reports. No Tk calls."""
    deep = o["deep"] or o["similar"]
    res = scan_library(root, o["recursive"], deep=deep, deep_cbr=o["deep_cbr"],
                       progress=lambda d, t, i: q.put(("prog", "Scanning", d, t)), stop=stop)
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
    q.put(("result", {"issues": issues, "broken": broken, "dups": dups, "gaps": gaps, "ignored": ignored,
                      "quality": ac.find_quality(issues), "stopped": res.stopped, "seconds": res.seconds,
                      "integrity": o["integrity"], "deep": deep, "cache_hits": res.cache_hits}))


class AuditPage(Page):
    defaults = {"recursive": True, "deep": True, "deep_cbr": False, "integrity": False, "similar": False,
                "similarity": "Normal", "from_one": False, "report": BROKEN}
    choices = {"similarity": list(ac.SIMILARITY), "report": REPORTS}

    def __init__(self, parent):
        super().__init__(parent)
        self.root_dir = None
        self.results = None
        self.q = None
        self.stop = threading.Event()
        self.checked = set()  # lower-cased paths ticked in the Duplicates table
        self.by_iid = {}

        title_block(self.main, "Library audit", "Scan a library once, then check it for problems.")
        self.drop = DropZone(self.main, "Drop a library folder here, or click to browse", self.browse)
        self.drop.pack(fill="x")
        bar = ctk.CTkFrame(self.main, fg_color=BG)
        bar.pack(fill="x", pady=(14, 6))
        segmented(bar, self.vars["report"], REPORTS, width=360).pack(side="left")
        self.meta = ctk.CTkLabel(self.main, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(2, 6))
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER,
                                           progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        self.holder = ctk.CTkFrame(self.main, fg_color=BG)
        self.holder.pack(fill="both", expand=True)
        self.trees = {}
        for r in REPORTS:
            wrap, tree = build_tree(self.holder, COLUMNS[r])
            self.trees[r] = (wrap, tree)
        self.trees[DUPES][1].bind("<Button-1>", self._click)
        self.hint = ctk.CTkLabel(self.main, text="", font=(FONT, 12), text_color=MUTED, anchor="w",
                                 justify="left", wraplength=620)
        self.hint.pack(fill="x", pady=(6, 0))

        v = self.vars
        sw = switch_style()
        box = self.form.add("Scan")
        ctk.CTkSwitch(box, text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        ctk.CTkSwitch(box, text="Read page counts and covers", variable=v["deep"], **sw).pack(anchor="w", pady=(8, 0))
        ctk.CTkSwitch(box, text="Open real .cbr files (slow)", variable=v["deep_cbr"], **sw).pack(anchor="w", pady=(8, 0))
        box = self.form.add("Broken files")
        ctk.CTkSwitch(box, text="Full integrity test (slow)", variable=v["integrity"], **sw).pack(anchor="w")
        ctk.CTkLabel(box, text="Reads every file completely. Off: only problems the quick scan notices.",
                     font=(FONT, 11), text_color=MUTED, anchor="w", justify="left",
                     wraplength=260).pack(fill="x", pady=(4, 0))
        box = self.form.add("Duplicates")
        ctk.CTkSwitch(box, text="Compare cover images", variable=v["similar"], **sw).pack(anchor="w")
        menu(box, v["similarity"], list(ac.SIMILARITY)).pack(fill="x", pady=(8, 0))
        box = self.form.add("Missing issues")
        ctk.CTkSwitch(box, text="Expect issues from #1", variable=v["from_one"], **sw).pack(anchor="w")
        ctk.CTkLabel(box, text="Off: a series is checked from the lowest issue you own.",
                     font=(FONT, 11), text_color=MUTED, anchor="w", justify="left",
                     wraplength=260).pack(fill="x", pady=(4, 0))

        self.btn_scan = button(self.footer, "Scan library", self.scan, primary=True)
        self.btn_scan.pack(pady=(0, 8))
        self.extras = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.extras.pack(fill="x")
        self.btn_move = button(self.extras, "Move checked to Archive", self.move_checked)
        self.btn_copy = button(self.extras, "Copy wishlist", self.copy_wishlist)
        self.btn_save = button(self.extras, "Save wishlist…", self.save_wishlist)
        self.btn_csv = button(self.footer, "Export CSV…", self.export_csv)
        self.btn_csv.pack(pady=(0, 8))
        self.btn_stop = button(self.footer, "Stop", self.stop.set)
        self.watch("report", callback=self._show_report)
        self._show_report()
        self._idle()

    # --- theme ---
    def apply_theme(self):
        for _, tree in self.trees.values():
            apply_tree_theme(tree)

    # --- folder ---
    def browse(self):
        d = filedialog.askdirectory(title="Library folder")
        if d:
            self.set_folder(d)

    def set_folder(self, folder):
        if self.q:
            return
        self.root_dir = Path(folder)
        self.drop.set(str(self.root_dir))
        self.results = None
        self.checked = set()
        self.say("")
        self._show_report()
        self._idle()

    # --- running ---
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
        self.checked = set()
        self.stop.clear()
        self.q = queue.Queue()
        self.progress.set(0)
        self.say("")
        self._show_report()
        self.meta.configure(text="Scanning…")
        self._idle()
        threading.Thread(target=_run, args=(self.q, self.root_dir, self.state(), self.stop), daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(100):
                msg = self.q.get_nowait()
                if msg[0] == "prog":
                    self.progress.set(msg[2] / max(1, msg[3]))
                    self.meta.configure(text=f"{msg[1]} {msg[2]} of {msg[3]}…")
                else:
                    self._finish(msg[1])
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish(self, res):
        self.q = None
        self.results = res
        self.progress.set(0 if res["stopped"] else 1)
        # pre-tick every copy except the biggest in each duplicate group
        self.checked = {str(i.path).lower() for g in res["dups"] for i in g.issues[1:]}
        self._show_report()
        self._idle()
        total = len(res["issues"])
        note = f"{total} files in {res['seconds']:.1f}s"
        if res["cache_hits"]:
            note += f" ({res['cache_hits']} from cache)"
        self.say(("Stopped · " if res["stopped"] else "Done · ") + note)

    # --- reports ---
    def _show_report(self):
        report = self.vars["report"].get()
        for r, (wrap, _) in self.trees.items():
            wrap.pack_forget()
        wrap, tree = self.trees[report]
        wrap.pack(fill="both", expand=True)
        self._fill(report)
        self._sync_buttons()

    def _fill(self, report):
        tree = self.trees[report][1]
        tree.delete(*tree.get_children())
        self.by_iid = {}
        res = self.results
        if not res:
            if not self.q:
                self.meta.configure(text="Choose a folder, then press Scan library." if not self.root_dir
                                    else "Press Scan library to begin.")
            self.hint.configure(text="")
            return
        if report == BROKEN:
            for i, problems in res["broken"]:
                for p in problems:
                    tree.insert("", "end", values=(i.rel, p), tags=("bad",))
            n = len(res["broken"])
            self.meta.configure(text=f"{n} file{'s' if n != 1 else ''} with problems" if n else EMPTY[BROKEN])
            self.hint.configure(text="Only problems from the quick scan." if not res["integrity"] else
                                "Full integrity test: zip CRC check plus cover, middle and last page decoded.")
        elif report == DUPES:
            for gi, g in enumerate(res["dups"], 1):
                for i in g.issues:
                    iid = tree.insert("", "end", values=(
                        "☑" if str(i.path).lower() in self.checked else "☐", gi, g.why, i.rel,
                        ac.size_text(i.size), i.pages if i.pages is not None else ""))
                    self.by_iid[iid] = i
            n = len(res["dups"])
            self.meta.configure(text=f"{n} group{'s' if n != 1 else ''} of probable duplicates" if n else EMPTY[DUPES])
            self.hint.configure(text="The biggest file in each group is left unticked. Ticked files can be moved "
                                     "to an Archive folder (as .bak); nothing is deleted.")
        elif report == MISSING:
            for g in res["gaps"]:
                tree.insert("", "end", values=(g.series, g.volume, g.owned, ac.ranges(g.missing)))
            n = sum(len(g.missing) for g in res["gaps"])
            self.meta.configure(text=f"{n} missing issue{'s' if n != 1 else ''} in {len(res['gaps'])} series"
                                if n else EMPTY[MISSING])
            self.hint.configure(text=f"{res['ignored']} file(s) ignored: specials, annuals, decimals or no issue number. "
                                     "A series is checked up to the highest issue you own or its issue count.")
        else:
            for i, flags in res["quality"]:
                tree.insert("", "end", values=(i.rel, " · ".join(flags)))
            n = len(res["quality"])
            self.meta.configure(text=f"{n} file{'s' if n != 1 else ''} flagged" if n else EMPTY[QUALITY])
            self.hint.configure(text=(f"Flags: under {ac.MIN_PAGES} or over {ac.MAX_PAGES} pages, under "
                                      f"{ac.SMALL_BYTES // 1_000_000} MB or over {ac.BIG_BYTES // 1_000_000} MB, "
                                      f"cover under {ac.LOW_COVER_HEIGHT}px tall." +
                                      ("" if res["deep"] else " Page and cover checks need 'Read page counts and covers'.")))
        if res["stopped"]:
            self.meta.configure(text=self.meta.cget("text") + " (partial: scan was stopped)")

    def _sync_buttons(self):
        for b in (self.btn_move, self.btn_copy, self.btn_save):
            b.pack_forget()
        report, res, busy = self.vars["report"].get(), self.results, bool(self.q)
        if report == DUPES:
            self.btn_move.pack(pady=(0, 8))
            self.btn_move.configure(state="normal" if res and self.checked and not busy else "disabled")
        elif report == MISSING:
            for b in (self.btn_copy, self.btn_save):
                b.pack(pady=(0, 8))
                b.configure(state="normal" if res and res["gaps"] and not busy else "disabled")
        self.btn_csv.configure(state="normal" if res and not busy else "disabled")

    # --- duplicates: ticking and moving ---
    def _click(self, e):
        tree = self.trees[DUPES][1]
        if tree.identify_region(e.x, e.y) == "cell" and tree.identify_column(e.x) == "#1":
            i = self.by_iid.get(tree.identify_row(e.y))
            if i:
                key = str(i.path).lower()
                self.checked.symmetric_difference_update({key})
                tree.set(tree.identify_row(e.y), "sel", "☑" if key in self.checked else "☐")
                self._sync_buttons()
                return "break"
        return None

    def move_checked(self):
        if not self.results or self.q:
            return
        todo = [i for g in self.results["dups"] for i in g.issues if str(i.path).lower() in self.checked]
        if not todo:
            return
        if not messagebox.askyesno(
                "Move to Archive",
                f"Move {len(todo)} file{'s' if len(todo) != 1 else ''} into Archive folders?\n\n"
                "Each is renamed with a .bak suffix, so nothing is deleted and you can restore it by hand.",
                icon="warning"):
            return
        moved, failed = set(), []
        for i in todo:
            try:
                move_to_archive(i.path)
                moved.add(str(i.path).lower())
            except OSError as e:
                failed.append(f"{i.path.name}: {e}")
        res = self.results
        for g in res["dups"]:
            g.issues = [i for i in g.issues if str(i.path).lower() not in moved]
        res["dups"] = [g for g in res["dups"] if len(g.issues) > 1]
        res["issues"] = [i for i in res["issues"] if str(i.path).lower() not in moved]
        self.checked -= moved
        self._fill(DUPES)
        self._sync_buttons()
        text = f"Moved {len(moved)} file{'s' if len(moved) != 1 else ''} to Archive"
        self.say(text + (f" · {len(failed)} failed ({failed[0]})" if failed else ""), err=bool(failed))

    # --- exports ---
    def _lines(self):
        return ac.wishlist_lines(self.results["gaps"]) if self.results else []

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
        path = filedialog.asksaveasfilename(title="Save wishlist", defaultextension=".txt",
                                            initialfile="wishlist.txt",
                                            filetypes=[("Text", "*.txt"), ("CSV", "*.csv")])
        if not path:
            return
        try:
            if path.lower().endswith(".csv"):
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow(["Series", "Volume", "Issue"])
                    for g in self.results["gaps"]:
                        w.writerows([g.series, g.volume, n] for n in g.missing)
            else:
                Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.say(f"Saved {len(lines)} lines.")
        except OSError as e:
            self.say(f"Could not save: {e}", err=True)

    def report_rows(self, report):
        """(header, rows) for the CSV export of one report."""
        res = self.results
        if report == BROKEN:
            return ["File", "Problem"], [[i.rel, p] for i, ps in res["broken"] for p in ps]
        if report == DUPES:
            return (["Group", "Why", "File", "Size (bytes)", "Pages", "Cover hash"],
                    [[gi, g.why, i.rel, i.size, i.pages if i.pages is not None else "", i.cover_hash or ""]
                     for gi, g in enumerate(res["dups"], 1) for i in g.issues])
        if report == MISSING:
            return (["Series", "Volume", "Owned", "Missing", "End from issue count"],
                    [[g.series, g.volume, g.owned, ac.ranges(g.missing), "yes" if g.from_count else "no"]
                     for g in res["gaps"]])
        return ["File", "Flags"], [[i.rel, " | ".join(f)] for i, f in res["quality"]]

    def export_csv(self):
        if not self.results:
            return
        report = self.vars["report"].get()
        path = filedialog.asksaveasfilename(title=f"Export {report} report", defaultextension=".csv",
                                            initialfile=f"audit-{report.lower()}.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        header, rows = self.report_rows(report)
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(header)
                w.writerows(rows)
            self.say(f"Exported {len(rows)} row{'s' if len(rows) != 1 else ''}.")
        except OSError as e:
            self.say(f"Could not save: {e}", err=True)

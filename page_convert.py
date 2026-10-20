"""CBR to CBZ page: repack RAR comics as ZIP, verified, in bulk, on the shared page shell in two columns with a divider
you can drag. Left: Comics (the .cbr files found). Right, scrolling on its own: Convert (what happens to the original and
to a .cbz that already exists), then Review (what will happen, then the run)."""
import os
import queue
import shutil
import threading
import time
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from archive_tools import DELETE, KEEP, MOVE, convert_one, dispose_original
from comic_core import common_root, find_extractor, in_archive, natural_key, picked_files, unique
from flow_kit import Advanced, ChoiceCards, LazyTable, SegmentPage, section
from ui_kit import (BORDER, DANGER, EDGE, FONT, HEAD, MUTED, PANEL, TEXT, TYPE_BODY, TYPE_HINT, DropZone, Toggle,
                    eta_text, flash_taskbar, switch_style, textbox, tool_button)

SKIP, BOTH, OVER = "Skip", "Keep both", "Overwrite"
EXISTS = [SKIP, BOTH, OVER]
ADVANCED_DEFAULTS = {"junk": False, "rename": False}
WORD = {MOVE: "original moved to Archive", KEEP: "original kept", DELETE: "original deleted"}


def _size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def find_cbr(folder, recursive):
    it = Path(folder).rglob("*") if recursive else Path(folder).iterdir()
    files = [p for p in it if p.is_file() and p.suffix.lower() == ".cbr" and not in_archive(p, folder)]
    return sorted(files, key=lambda p: natural_key(p.relative_to(folder)))


def _check(files, gen, q):
    """Look at every file without extracting it: is it really a RAR, a ZIP with the wrong name, or unreadable here?
    Posts ("kind", path, "RAR" | "ZIP"), ("bad", path, reason), ("progress", done, total) and ("checked", gen)."""
    have_rar = find_extractor() is not None
    for i, p in enumerate(files):
        try:
            if zipfile.is_zipfile(p):
                q.put(("kind", p, "ZIP"))
            elif not have_rar:
                q.put(("bad", p, "Needs a RAR extractor (7-Zip or unrar)"))
            else:
                q.put(("kind", p, "RAR"))
        except OSError as e:
            q.put(("bad", p, str(e) or "Cannot be opened"))
        if i % 25 == 0:
            q.put(("progress", i, len(files)))
    q.put(("checked", gen))


def _worker(q, files, o, stop):
    used = set()
    for k, src in enumerate(files):
        if stop.is_set():
            q.put(("stopped",))
            return
        q.put(("start", k, len(files)))
        try:
            dest = src.with_suffix(".cbz")
            if dest.exists():
                if o["exists"] == SKIP:
                    q.put(("skipped", src, f"{dest.name} already exists"))
                    continue
                if o["exists"] == BOTH:
                    dest = unique(dest, used)
            used.add(str(dest).lower())
            pages = convert_one(src, dest, o["junk"], o["rename"])
            try:
                dispose_original(src, o["original"])
            except OSError as e:
                q.put(("failed", src, f"Converted to {dest.name}, but the .cbr could not be dealt with: {e}"))
                continue
            q.put(("ok", src, dest, pages))
        except Exception as e:  # noqa: BLE001 - one bad file must not stop the batch; its original is untouched
            q.put(("failed", src, str(e)))
    q.put(("done",))


class ConvertPage(SegmentPage):
    title = "CBR to CBZ"
    subtitle = "Repack RAR comics as ZIP, checked before anything is replaced."
    defaults = {"recursive": True, "original": MOVE, "exists": SKIP, "junk": False, "rename": False}
    choices = {"original": [MOVE, KEEP, DELETE], "exists": EXISTS}
    split = True
    show_auto = False
    max_width = 1500

    def __init__(self, parent):
        super().__init__(parent)
        self.folder = None
        self.picked = None   # files chosen one by one instead of a folder
        self.files = []
        self.q = None
        self.stop = threading.Event()
        self.result = None   # counts of the last finished run
        self.failed = []     # [(path, reason)] of the last run
        self.reviewed = False
        self.dry = False
        self._t0 = 0
        self.kind = {}       # path -> "RAR" | "ZIP"
        self.bad = {}        # path -> why it cannot be read
        self.checking = None
        self.check_q = None
        self._gen = 0
        self._last_refresh = 0
        self._pending_refresh = False
        v = self.vars

        # ---- Comics
        self.make_panes(right_width=560, lo=400)
        self.s1 = self.add_block("Comics", side="left", grow=True)
        self.drop = DropZone(self.s1.body, "Drop a folder here, or add a folder or comics", self.browse, self.browse,
                             self.browse_files)
        self.drop.pack(fill="x", padx=(0, 6), pady=(0, 12))
        Toggle(self.s1.body, text="Include comics in subfolders", variable=v["recursive"],
               **switch_style()).pack(anchor="w", pady=(0, 10))
        self.comics = LazyTable(self.s1.body, [
            ("name", "File", 230, True), ("where", "Folder", 150, True), ("kind", "Kind", 70, False),
            ("size", "Size", 74, False)], rows=8, grow=True,
            empty="No .cbr files yet. Add a folder or pick some comics above.")
        self.comics.pack(fill="both", expand=True)

        # ---- Convert
        self.s2 = self.add_block("Convert")
        body = self.s2.body
        section(body, "What happens to the original").pack(fill="x", pady=(0, 10))
        ChoiceCards(body, v["original"], [
            (MOVE, "Move to Archive", "Kept as .cbr.bak in an Archive folder; drop the .bak to restore it"),
            (KEEP, "Keep it", "Stays beside the new .cbz, so a reader may list both"),
            (DELETE, "Delete it", "Gone for good once the .cbz is verified")], columns=3).pack(fill="x")
        section(body, "If the .cbz already exists").pack(fill="x", pady=(8, 10))
        ChoiceCards(body, v["exists"], [
            (SKIP, "Skip", "Leave that comic alone"),
            (BOTH, "Keep both", "Give the new .cbz a number"),
            (OVER, "Replace", "Write the new .cbz over it")], columns=3).pack(fill="x")
        self.adv = Advanced(body)
        self.adv.pack(fill="x", pady=(8, 12))
        Toggle(self.adv.body, text="Remove junk files (anything that is not a page)", variable=v["junk"],
               **switch_style()).pack(anchor="w", pady=(0, 10))
        Toggle(self.adv.body, text="Rename pages 001.jpg, 002.jpg…", variable=v["rename"],
               **switch_style()).pack(anchor="w")
        self.adv.track(v, ADVANCED_DEFAULTS)
        tool_button(body, "Review the files", self.go_review, 150).pack(anchor="e")

        # ---- Review
        self.s3 = self.add_block("Review")
        self.headline = ctk.CTkLabel(self.s3.body, text="", font=(HEAD, 16), text_color=TEXT, anchor="w", justify="left",
                                     wraplength=480)
        self.headline.pack(fill="x")
        self.subline = ctk.CTkLabel(self.s3.body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                                    wraplength=480)
        self.subline.pack(fill="x", pady=(2, 4))
        self.verified = ctk.CTkLabel(
            self.s3.body, text="Converted only if verified: each new file must open, have the same number of pages and "
            "pass the zip test before the original is touched.", font=TYPE_HINT, text_color=MUTED, anchor="w",
            justify="left", wraplength=480)
        self.verified.pack(fill="x", pady=(0, 8))
        self.problems = ctk.CTkFrame(self.s3.body, fg_color="transparent", height=0)  # (an empty frame is 200 px tall otherwise)
        self.problems.pack(fill="x")
        self.review = LazyTable(self.s3.body, [("src", "File", 190, True), ("dest", "Becomes", 190, True),
                                                ("state", "Status", 100, False)], rows=9,
                                empty="Choose .cbr files to see what will happen to each.")
        self.review.pack(fill="x", pady=(4, 0))
        self.progress = ctk.CTkProgressBar(self.s3.body, height=14, corner_radius=0, border_width=3, border_color=BORDER,
                                           fg_color=BORDER, progress_color=("#FFD60A", "#FFD60A"))
        self.progress.set(0)
        self.status = ctk.CTkLabel(self.s3.body, text="", font=(FONT, 12), text_color=MUTED, anchor="w")
        self.result_box = ctk.CTkFrame(self.s3.body, fg_color=PANEL, border_color=BORDER, border_width=EDGE, corner_radius=0)
        self.result_title = ctk.CTkLabel(self.result_box, text="", font=(HEAD, 18), text_color=TEXT, anchor="w")
        self.result_title.pack(fill="x", padx=16, pady=(14, 0))
        self.result_sub = ctk.CTkLabel(self.result_box, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                                       wraplength=440)
        self.result_sub.pack(fill="x", padx=16, pady=(2, 14))
        self.log_label = ctk.CTkLabel(self.s3.body, text="Every file", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w")
        self.log = textbox(self.s3.body, font=("Consolas", 12), height=150, wrap="none")
        self.log.configure(state="disabled")

        self.fit_right(self.headline, self.subline, self.verified, self.result_sub)
        self.watch("recursive", callback=self.rescan)
        self.watch("original", "exists", "junk", "rename", callback=self.refresh)
        self.refresh()
        self._poll_check()

    # --- choosing files ---
    def browse(self):
        d = filedialog.askdirectory(title="Folder with .cbr files")
        if d:
            self.set_folder(d)

    def browse_files(self):
        files = filedialog.askopenfilenames(title="Choose .cbr files", filetypes=[("RAR comics", "*.cbr"), ("All", "*.*")])
        if files:
            self.set_files(files)

    def set_files(self, paths):
        """Convert these .cbr files only, instead of a whole folder."""
        files = picked_files(paths, {".cbr"})
        if not files:
            self.say("None of those files are .cbr comics.", err=True)
            return
        self.picked = files
        self.folder = common_root(files)
        self.clear_origin()
        self.drop.set(f"{_plural(len(files), '.cbr file')} chosen from {self.folder}")
        self.say("")
        self._new_files()

    def set_folder(self, folder):
        self.folder = Path(folder)
        self.picked = None
        self.clear_origin()
        self.drop.set(str(self.folder))
        self._new_files()

    def add_paths(self, paths):
        """Dropped on the window: a folder, or some files."""
        paths = [Path(p) for p in paths]
        if len(paths) == 1 and paths[0].is_dir():
            self.set_folder(paths[0])
        else:
            self.set_files(paths)

    def open_with(self, folder, view=None, origin=None, back=None):
        """Open a folder from another tool (the Library audit's CBR chip), with a chip saying where you came from and a
        Back button."""
        self.set_folder(folder)
        if origin:
            self.show_origin(f"From {origin}  ·  {_plural(len(self.files), '.cbr file')}", back, f"Back to {origin}")

    def _new_files(self):
        self.result = None
        self.reviewed = False
        self.dry = False
        self.rescan()
        if self.files:
            self.advance(self.s1)

    def go_review(self):
        """The Convert settings are done: bring the review into view."""
        self.reviewed = True
        self.refresh()
        self.advance(self.s2)

    def rescan(self):
        if self.picked is not None:
            self.files = [p for p in self.picked if p.exists()]
        else:
            self.files = find_cbr(self.folder, self.vars["recursive"].get()) if self.folder else []
        self._fill_files()
        self._start_check()
        self.refresh()

    def reset(self):
        """Start over with another folder."""
        if self.q:
            return
        self.folder = self.picked = None
        self.files = []
        self.result = None
        self.reviewed = self.dry = False
        self.clear_origin()
        self.drop.set(None)
        self._log(None)
        self.say("")
        self._fill_files()
        self._start_check()
        self.refresh()
        self.update_idletasks()
        self.reveal(self.s1)

    def again(self):
        self.result = None
        self.dry = False
        self.rescan()

    def _sizes(self):
        out = {}
        for p in self.files:
            try:
                out[p] = p.stat().st_size
            except OSError:
                out[p] = 0
        return out

    def _fill_files(self):
        sizes = self._sizes()
        rows = []
        for p in self.files:
            try:
                where = str(p.parent.relative_to(self.folder)) if self.folder else str(p.parent)
            except ValueError:
                where = str(p.parent)
            kind = {"RAR": "RAR", "ZIP": "ZIP inside"}.get(self.kind.get(p), "Unreadable" if p in self.bad else "…")
            rows.append((p.name, where, kind, _size(sizes[p])))
        self.comics.set_rows(rows)

    # --- looking at the files in the background ---
    def _start_check(self):
        self._gen += 1
        self.kind, self.bad = {}, {}
        self.check_q = queue.Queue()
        if self.files:
            self.checking = (0, len(self.files))
            threading.Thread(target=_check, args=(list(self.files), self._gen, self.check_q), daemon=True).start()
        else:
            self.checking = None

    def _poll_check(self):
        changed = False
        try:
            for _ in range(200):
                msg = self.check_q.get_nowait() if self.check_q else None
                if msg is None:
                    break
                if msg[0] == "bad":
                    self.bad[msg[1]] = msg[2]
                elif msg[0] == "kind":
                    self.kind[msg[1]] = msg[2]
                elif msg[0] == "progress":
                    self.checking = (msg[1], msg[2])
                elif msg[0] == "checked" and msg[1] == self._gen:
                    self.checking = None
                    self._last_refresh = 0  # the last answer arrived: draw it now
                changed = True
        except queue.Empty:
            pass
        if (changed or self._pending_refresh) and time.time() - self._last_refresh > 0.8:
            self._pending_refresh = False
            self._last_refresh = time.time()
            self._fill_files()
            self.refresh()
        elif changed:
            self._pending_refresh = True   # a long check must not redraw the tables every tick
        try:
            self.after(150, self._poll_check)
        except Exception:  # noqa: BLE001 - the page is gone
            pass

    # --- keep the screen in step ---
    def options(self):
        return self.state()

    def review_rows(self, sizes=None):
        """The Review table: [(values, path, tag)], the counts that go with it and how many bytes will be converted."""
        o = self.options()
        sizes = sizes or {}
        used, rows, need = set(), [], 0
        c = {"new": 0, "exists": 0, "bad": 0}
        for src in self.files:
            dest = src.with_suffix(".cbz")
            if src in self.bad:
                key, tag = "bad", "bad"
                c["bad"] += 1
            elif dest.exists() or str(dest).lower() in used:
                tag = "dim"
                if o["exists"] == BOTH:
                    dest, key = unique(dest, used), "number"
                    c["new"] += 1
                else:
                    key = "skip" if o["exists"] == SKIP else "replace"
                    c["exists"] += 1
            else:
                key, tag = "new", ""
                c["new"] += 1
            used.add(str(dest).lower())
            if key not in ("bad", "skip"):
                need += sizes.get(src, 0)
            word = {"bad": ("Unreadable", "Would fail"), "new": ("New", "Would convert"),
                    "number": ("Gets a number", "Would number"), "skip": ("Skipped", "Would skip"),
                    "replace": ("Replaces it", "Would replace")}[key][1 if self.dry else 0]
            rows.append(((src.stem, dest.name, word), src, (tag,) if tag else ()))
        return rows, c, need

    def refresh(self):
        n = len(self.files)
        o = self.options()
        sizes = self._sizes() if n else {}
        total = sum(sizes.values())
        if n:
            where = str(self.folder) if self.picked is None else f"{self.folder} (files you picked)"
            self.s1.set_summary(f"{_plural(n, '.cbr file')} · {_size(total)} · {where}")
        else:
            self.s1.set_summary("")
        self.s2.set_summary(f"{WORD[o['original']].capitalize()} · existing .cbz: "
                            f"{'replace' if o['exists'] == OVER else o['exists'].lower()}")
        rows, c, need = self.review_rows(sizes)
        will = c["new"] + (c["exists"] if o["exists"] == OVER else 0)
        line = f"Will convert {_plural(will, 'file')}"
        if o["exists"] == SKIP and c["exists"]:
            line += f"  ·  {c['exists']} already have a .cbz and are skipped"
        elif c["exists"]:
            line += f"  ·  {c['exists']} replace a .cbz"
        if c["bad"]:
            line += f"  ·  {c['bad']} unreadable"
        if self.checking:
            line += f"  ·  checking files {self.checking[0]} of {self.checking[1]}…"
        self.headline.configure(text=("Dry run, nothing is written.  " if self.dry else "") + line if n else
                                "Choose some .cbr files first.")
        sub = f"About {_size(need)} to convert; pages are stored as they are, so the new files are about the same size." if n else ""
        warn = self._free_note(need)
        self.subline.configure(text=sub + (f"\n{warn}" if warn else ""), text_color=DANGER if warn else MUTED)
        for w in self.problems.winfo_children():
            w.destroy()
        notes = [f"✗  {p.name}: {self.bad[p]}" for p in list(self.bad)[:3]]
        if len(self.bad) > 3:
            notes.append(f"…and {len(self.bad) - 3} more that cannot be read")
        if o["original"] == DELETE:
            notes.append("⚠  Each .cbr is deleted for good once its .cbz is verified.")
        for text in notes:
            ctk.CTkLabel(self.problems, text=text, font=TYPE_BODY, text_color=DANGER, anchor="w", justify="left",
                         wraplength=max(240, int(self.right_width) - 70)).pack(fill="x", pady=1)
        self.review.set_rows([r[0] for r in rows], keys=[r[1] for r in rows], tags=[r[2] for r in rows])
        self._counts = c
        self._sync_segments()

    def _free_note(self, need):
        """A warning when the drive that will hold the new files looks too small, else ''."""
        if not need or not self.folder:
            return ""
        place = self.folder
        while not place.exists() and place != place.parent:
            place = place.parent
        try:
            free = shutil.disk_usage(place).free
        except OSError:
            return ""
        return f"Only {_size(free)} free on that drive." if need > free else ""

    def _sync_segments(self):
        n, running, done = len(self.files), bool(self.q), self.result is not None
        s1, s2, s3 = self.s1, self.s2, self.s3
        if not n:
            s1.set_state("active")
            s2.set_state("locked")
            s3.set_state("locked")
            s3.set_summary("")
        else:
            s1.set_state("done")
            if running or done:
                s2.set_state("done")
                s3.set_state("active" if running else "done")
            elif self.reviewed:
                s2.set_state("done")
                s3.set_state("active")
            else:
                s2.set_state("active")
                s3.set_state("idle")
            c = getattr(self, "_counts", {"new": 0, "exists": 0})
            s3.set_summary(self.result_text() if done else f"{_plural(c['new'], 'file')} to convert")
        # the run area: progress while running, the result and the file list after it
        for w in (self.progress, self.status, self.result_box, self.log_label, self.log):
            w.pack_forget()
        if running:
            self.progress.pack(fill="x", pady=(10, 0))
        if running or self.status.cget("text"):
            self.status.pack(fill="x", pady=(6, 0))
        if done:
            self.result_box.pack(fill="x", padx=(0, 6), pady=(12, 0))
        if running or done:
            self.log_label.pack(fill="x", pady=(14, 4))
            self.log.pack(fill="x", padx=(0, 6))
        # the footer: one thing to press
        retry = [(f"Retry {len(self.failed)} failed", self.retry)] if done and self.failed else []
        if running:
            self.set_footer(self.status.cget("text") or "Working…", "Stop", self.start)
        elif done:
            word = "Stopped" if self.result["stopped"] else "Done"
            self.set_footer(f"{word}  ·  {self.result_text()}", "Open the folder", self.open_out,
                            enabled=bool(self.folder and self.folder.exists()),
                            secondary=[("Convert again", self.again), ("Do another folder", self.reset)] + retry)
        elif not n:
            self.set_footer("Choose some .cbr files to begin.", "Choose files first", self.start, enabled=False)
        else:
            dry = [("Back to normal", self.leave_dry)] if self.dry else [("Dry run", self.dry_run)]
            self.set_footer("Dry run: nothing is written." if self.dry else f"{_plural(n, '.cbr file')} ready.",
                            f"Convert {_plural(n, 'file')}", self.start, secondary=dry)

    def result_text(self):
        r = self.result
        text = f"{r['ok']} converted"
        if r["skipped"]:
            text += f", {r['skipped']} skipped"
        if r["failed"]:
            text += f", {r['failed']} failed"
        return text

    def dry_run(self):
        """Show the review as if the run had happened, without writing anything."""
        self.dry = True
        self.reviewed = True
        self.refresh()
        self.update_idletasks()
        self.reveal(self.s3)

    def leave_dry(self):
        self.dry = False
        self.refresh()

    # --- run ---
    def stop_action(self):
        if self.q:
            self.stop.set()

    def start(self, only=None):
        if self.q:  # running: this button is "Stop"
            self.stop.set()
            self.bar_btn.configure(state="disabled", text="Stopping…")
            return
        o = self.options()
        files = list(only) if only else [p for p in self.files if p not in self.bad]
        if not self.folder or not files:
            self.say("Choose some .cbr files first.", err=True)
            return
        if o["original"] == DELETE and not messagebox.askyesno(
                "Delete the originals",
                f"Each .cbr is deleted for good once its .cbz has been verified.\n\n{_plural(len(files), '.cbr file')} "
                "will be converted. Continue?", icon="warning"):
            return
        self.counts = {"ok": 0, "skipped": 0, "failed": 0}
        self.failed = []
        self.dry = False
        self.reviewed = True
        self.stop.clear()
        self.q = queue.Queue()
        self.result = None
        self._t0 = time.time()
        self._log(None)
        self.say("")
        self.progress.set(0)
        self.refresh()
        self.update_idletasks()
        self.reveal(self.s3)
        threading.Thread(target=_worker, args=(self.q, files, o, self.stop), daemon=True).start()
        self.after(60, self._poll)  # (not at once: a fast run would be over before the page showed Stop)

    def retry(self):
        """Run again on just the files that failed."""
        self.start(only=[p for p, _why in self.failed])

    def _poll(self):
        try:
            for _ in range(50):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "start":
                    self.progress.set(msg[1] / msg[2])
                    c = self.counts
                    self.say(eta_text(msg[1], msg[2], self._t0) + f"  ·  {c['ok']} converted"
                             + (f", {c['skipped']} skipped" if c["skipped"] else "")
                             + (f", {c['failed']} failed" if c["failed"] else ""))
                    self.bar_text.configure(text=self.status.cget("text"))
                    if not self.status.winfo_ismapped():
                        self.refresh()
                elif kind == "ok":
                    self.counts["ok"] += 1
                    self._log(f"✓  {msg[1].name}  →  {msg[2].name}  ({msg[3]} pages)")
                elif kind == "skipped":
                    self.counts["skipped"] += 1
                    self._log(f"↷  {msg[1].name}  {msg[2]}")
                elif kind == "failed":
                    self.counts["failed"] += 1
                    self.failed.append((msg[1], msg[2]))
                    self._log(f"✗  {msg[1].name}  {msg[2]}")
                else:
                    self._finish(kind == "stopped")
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish(self, stopped):
        self.q = None
        c = self.counts
        self.result = dict(c, stopped=stopped)
        self.progress.set(0 if stopped else 1)
        if time.time() - self._t0 > 5:
            flash_taskbar(self.winfo_toplevel())
        self.result_title.configure(text=("Stopped. " if stopped else "Done. ") + f"{c['ok']} converted")
        parts = []
        if c["skipped"]:
            parts.append(f"{c['skipped']} skipped because the .cbz already existed")
        if c["failed"]:
            parts.append(f"{c['failed']} failed; their originals were not touched")
        sub = ". ".join(parts) if parts else "Nothing went wrong."
        if c["failed"]:
            sub += "\n" + "\n".join(f"{p.name}: {why}" for p, why in self.failed[:3]) + ("\n…" if len(self.failed) > 3 else "")
        self.result_sub.configure(text=sub)
        self.say("")
        self.refresh()
        if not stopped and c["ok"] and self.folder:
            self.show_next([("Check the library for duplicates", self.link("audit", folder=self.folder))])

    def _log(self, line):
        self.log.configure(state="normal")
        if line is None:
            self.log.delete("1.0", "end")
        else:
            self.log.insert("end", line + "\n")
            self.log.see("end")
        self.log.configure(state="disabled")

    def open_out(self):
        if self.folder and self.folder.exists():
            os.startfile(self.folder)  # Windows

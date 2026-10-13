"""Add to library page: drop comics in (or scan an inbox folder), review what each will become, then convert,
clean and rename them into the Ready folder in one go."""
import os
import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import intake_core as ic
from archive_tools import DELETE, KEEP, MOVE
from rename_core import read_comicinfo
from ui_kit import (ACCENT, BG, BORDER, FONT, MUTED, TEXT, DropZone, Page, apply_tree_theme, build_tree, button,
                    divider, entry, menu, switch_style, title_block, toolbar)

COLS = [("sel", "", 38, False), ("file", "Comic", 200, True), ("dest", "Becomes", 260, True),
        ("steps", "Steps", 150, False), ("status", "Status", 84, False)]
BAD = (ic.DUPLICATE, ic.EXISTS, ic.NO_SERIES, ic.FAILED)


def _read_all(q, items):
    for k, it in enumerate(items):
        try:
            ci = read_comicinfo(it.src)
        except Exception:  # noqa: BLE001 - a bad archive is reported when it is processed
            ci = {}
        q.put(("ci", it, ci, k + 1, len(items)))
    q.put(("read_done",))


def _run(q, todo, o):
    for k, it in enumerate(todo):
        q.put(("start", k, len(todo)))
        try:
            r = ic.add_comic(it.src, it.dest, o["junk"], o["patterns"], o["pages"], o["original"])
            q.put(("ok", it, r))
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            q.put(("fail", it, str(e) or type(e).__name__))
    q.put(("finished",))


class IntakePage(Page):
    defaults = {"inbox": "", "ready": "", "recursive": True, "rename": True, "folders": True, "junk": True,
                "patterns": "", "pages": False, "original": DELETE}
    choices = {"original": [DELETE, MOVE, KEEP]}

    def __init__(self, parent):
        super().__init__(parent)
        self.items, self.by_iid = [], {}
        self.q = None
        self.busy = None  # 'read' | 'run'
        self.rename_source = None  # callable giving the Renamer's settings; the app wires it up
        self._later_id = None
        self.done = {"ok": 0, "fail": 0}

        title_block(self.main, "Add to library", "Convert, clean and rename new comics, then file them in your Ready folder.")
        self.drop = DropZone(self.main, "Drop comics or folders here, or scan your inbox", self.browse_files,
                             self.browse_folder, self.browse_files)
        self.drop.pack(fill="x")
        bar = ctk.CTkFrame(self.main, fg_color=BG)
        bar.pack(fill="x", pady=(14, 6))
        self.meta = ctk.CTkLabel(bar, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(side="left")
        toolbar(bar, [("all", "Select all", 84, lambda: self.select_all(True)),
                      ("none", "Select none", 84, lambda: self.select_all(False))],
                [("clear", "Clear list", 84, self.clear)], side="right")
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER, progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        wrap, self.tree = build_tree(self.main, COLS, selectmode="browse")
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<Button-1>", self._click)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._show_note())
        self.note = ctk.CTkLabel(self.main, text="", font=(FONT, 12), text_color=MUTED, anchor="w", justify="left",
                                 wraplength=640)
        self.note.pack(fill="x", pady=(6, 0))

        v, sw = self.vars, switch_style()
        self.form.heading("Source")
        self.path_row(self.form.add("Inbox folder"), v["inbox"], "Folder where new comics land")
        ctk.CTkSwitch(self.form.add("Subfolders"), text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        self.form.heading("Output")
        self.path_row(self.form.add("Ready folder"), v["ready"], "Folder for finished comics")
        ctk.CTkSwitch(self.form.add("Folders"), text="File into series folders", variable=v["folders"], **sw).pack(anchor="w")
        self.form.heading("Steps")
        ctk.CTkLabel(self.form.add("Convert"), text="Every comic is saved as a verified .cbz.", font=(FONT, 12),
                     text_color=MUTED, anchor="w", justify="left", wraplength=260).pack(fill="x")
        ctk.CTkSwitch(self.form.add("Name"), text="Rename like the Renamer", variable=v["rename"], **sw).pack(anchor="w")
        ctk.CTkSwitch(self.form.add("Junk"), text="Remove junk files", variable=v["junk"], **sw).pack(anchor="w")
        entry(self.form.add("Also remove files matching"), v["patterns"], placeholder_text="zzz*, *.txt").pack(fill="x")
        ctk.CTkSwitch(self.form.add("Page names"), text="Rename pages 001.jpg, 002.jpg…", variable=v["pages"],
                      **sw).pack(anchor="w")
        self.form.heading("When it is done")
        menu(self.form.add("The original comic"), v["original"], [DELETE, MOVE, KEEP]).pack(fill="x")

        self.btn_apply = button(self.footer, "Add to library", self.apply, primary=True)
        self.btn_apply.pack(pady=(0, 8))
        self.btn_scan = button(self.footer, "Scan inbox", self.scan_inbox)
        self.btn_scan.pack(pady=(0, 8))
        divider(self.footer, vertical=False).pack(fill="x", pady=(2, 10))
        self.btn_open = button(self.footer, "Open Ready folder", self.open_ready)
        self.btn_open.pack()
        self.watch("ready", "folders", "rename", "junk", "pages", callback=self._later)
        self._idle()

    # ------------------------------------------------------------------ settings and state
    def rename_settings(self):
        return ic.rename_settings(self.rename_source() if self.rename_source else None)

    def options(self):
        return self.state()

    def on_show(self):
        """The Renamer's settings may have changed since this page was last open."""
        self.recompute()

    def _later(self):
        if self._later_id is not None:
            self.after_cancel(self._later_id)
        self._later_id = self.after(350, self.recompute)

    def _idle(self):
        free = not self.busy
        ready = free and any(it.checked and it.status in ic.PROCESSABLE for it in self.items)
        self.btn_apply.configure(state="normal" if ready else "disabled")
        self.btn_scan.configure(state="normal" if free else "disabled")
        self.btn_open.configure(state="normal" if self.vars["ready"].get().strip() else "disabled")

    # ------------------------------------------------------------------ adding comics
    def browse_folder(self):
        d = filedialog.askdirectory(title="Add a folder of comics")
        if d:
            self.add_paths([Path(d)])

    def browse_files(self):
        files = filedialog.askopenfilenames(title="Choose comics", filetypes=[("Comics", "*.cbz *.cbr"), ("All", "*.*")])
        if files:
            self.add_paths([Path(f) for f in files])

    def set_folder(self, folder):  # a folder dropped on the page
        self.add_paths([Path(folder)])

    def scan_inbox(self):
        inbox = self.vars["inbox"].get().strip()
        if not inbox or not Path(inbox).is_dir():
            self.say("Choose an Inbox folder first.", err=True)
            return
        n = self.add_paths([Path(inbox)])
        if n == 0:
            self.say("No new comics in the inbox.")

    def add_paths(self, paths):
        """Add comics and folders of comics; ones already in the list are skipped. Returns how many were new."""
        if self.busy:
            return 0
        have = {str(it.src).lower() for it in self.items}
        new = [ic.Item(p) for p in ic.find_sources(paths, self.vars["recursive"].get()) if str(p).lower() not in have]
        if not new:
            return 0
        self.items += new
        self.say("")
        self.busy, self.q = "read", queue.Queue()
        self.meta.configure(text=f"Reading {len(new)} comic{'s' if len(new) != 1 else ''}…")
        threading.Thread(target=_read_all, args=(self.q, new), daemon=True).start()
        self._idle()
        self._poll()
        return len(new)

    def clear(self):
        if self.busy:
            return
        self.items = []
        self.recompute()
        self.say("")

    # ------------------------------------------------------------------ planning
    def recompute(self):
        self._later_id = None
        if self.busy == "run":
            return
        ready = self.vars["ready"].get().strip()
        for it in self.items:
            if it.ci is None:
                it.ci = {}
        if ready:
            inbox = self.vars["inbox"].get().strip() or None
            ic.plan(self.items, ready, self.rename_settings(), self.options(), inbox)
        else:
            for it in self.items:
                it.dest, it.status, it.note, it.steps = None, "", "Choose a Ready folder to see the new names.", ""
                it.checked = False
        self._fill()

    def _fill(self):
        self.tree.delete(*self.tree.get_children())
        self.by_iid = {}
        ready = self.vars["ready"].get().strip()
        for it in self.items:
            it.iid = self.tree.insert("", "end", values=self._values(it, ready), tags=self._tags(it))
            self.by_iid[it.iid] = it
        self._summary()
        self._idle()

    def _values(self, it, ready):
        try:
            dest = str(it.dest.relative_to(ready)) if it.dest else ""
        except ValueError:
            dest = str(it.dest)
        return ("☑" if it.checked else "☐", it.src.name, dest, it.steps, it.status)

    def _tags(self, it):
        return ("bad",) if it.status in BAD else ("dim",) if it.status == ic.IN_PLACE else ()

    def _refresh(self, it):
        self.tree.item(it.iid, values=self._values(it, self.vars["ready"].get().strip()), tags=self._tags(it))

    def _summary(self):
        n = len(self.items)
        if not n:
            self.meta.configure(text="")
            return
        go = sum(1 for it in self.items if it.checked and it.status in ic.PROCESSABLE)
        flagged = sum(1 for it in self.items if it.status in BAD)
        text = f"{n} comic{'s' if n != 1 else ''} · {go} to add"
        if flagged:
            text += f" · {flagged} need a look"
        self.meta.configure(text=text)

    def _show_note(self):
        sel = self.tree.selection()
        it = self.by_iid.get(sel[0]) if sel else None
        self.note.configure(text=(it.note or "") if it else "")

    # ------------------------------------------------------------------ table
    def _click(self, e):
        if self.tree.identify_region(e.x, e.y) == "cell" and self.tree.identify_column(e.x) == "#1":
            it = self.by_iid.get(self.tree.identify_row(e.y))
            if it and not self.busy:
                it.checked, it.manual = not it.checked, True
                it.error = ""  # ticking a failed comic tries it again
                if it.status == ic.FAILED:
                    self.recompute()
                else:
                    self._refresh(it)
                    self._summary()
                    self._idle()
                return "break"
        return None

    def select_all(self, value):
        if self.busy:
            return
        for it in self.items:
            if it.status in ic.PROCESSABLE:
                it.checked, it.manual = value, True
        for it in self.items:
            self._refresh(it)
        self._summary()
        self._idle()

    # ------------------------------------------------------------------ running
    def apply(self):
        if self.busy:
            return
        if not self.vars["ready"].get().strip():
            self.say("Choose a Ready folder first.", err=True)
            return
        todo = [it for it in self.items if it.checked and it.status in ic.PROCESSABLE]
        if not todo:
            return
        o = self.options()
        how = {DELETE: "The original files will be deleted once each new comic has been checked.",
               MOVE: "The original files will be moved to an Archive folder.",
               KEEP: "The original files will be kept."}[o["original"]]
        dup = sum(1 for it in todo if it.status in (ic.DUPLICATE, ic.EXISTS))
        msg = f"Add {len(todo)} comic{'s' if len(todo) != 1 else ''} to {o['ready']}?\n\n{how}"
        if dup:
            msg += f"\n\n{dup} of them look like comics that are already there."
        if not messagebox.askyesno("Add to library", msg, icon="warning"):
            return
        self.busy, self.q = "run", queue.Queue()
        self.done = {"ok": 0, "fail": 0}
        self.progress.set(0)
        self.say("")
        self._idle()
        threading.Thread(target=_run, args=(self.q, todo, o), daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(60):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "ci":
                    msg[1].ci = msg[2]
                    self.progress.set(msg[3] / msg[4])
                elif kind == "read_done":
                    self.busy, self.q = None, None
                    self.progress.set(0)
                    self.recompute()
                    return
                elif kind == "start":
                    self.progress.set(msg[1] / msg[2])
                    self.say(f"{msg[1] + 1} of {msg[2]}")
                elif kind == "ok":
                    it, r = msg[1], msg[2]
                    it.status, it.note = ic.DONE, f"Saved as {r['dest'].name}"
                    self.done["ok"] += 1
                    inbox = self.vars["inbox"].get().strip()
                    if inbox and Path(inbox) in it.src.parents:
                        ic.prune_empty(it.src.parent, inbox)
                    self._refresh(it)
                elif kind == "fail":
                    it = msg[1]
                    it.error = msg[2]
                    it.status, it.note = ic.FAILED, msg[2]
                    self.done["fail"] += 1
                    self._refresh(it)
                else:  # finished
                    self._finish()
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish(self):
        self.busy, self.q = None, None
        ok, bad = self.done["ok"], self.done["fail"]
        self.items = [it for it in self.items if it.status != ic.DONE]
        self.progress.set(1)
        text = f"Added {ok} comic{'s' if ok != 1 else ''}"
        if bad:
            text += f" · {bad} failed (click a row to read why)"
        self.say(text, err=bool(bad))
        self.recompute()

    def open_ready(self):
        ready = self.vars["ready"].get().strip()
        if ready and Path(ready).exists():
            os.startfile(ready)  # Windows

    def apply_theme(self):
        apply_tree_theme(self.tree)

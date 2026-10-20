"""Add to library page: bring new comics in, checked, cleaned, named and filed. On the shared page shell in two columns with a
divider you can drag. Left: Inbox (drop comics or folders, or scan the inbox folder, and an optional watch of it) and Review
(every comic as a card with what it becomes; the ones that need a look come first, each with a one-line fix). Right, scrolling
on its own: Destination (the Ready folder and how it is filed) and Clean-up (what is done to each comic and what happens to the
original). The footer adds the ticked comics."""
import os
import queue
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk

import intake_core as ic
from archive_tools import DELETE, KEEP, MOVE, apply_metadata
from cardlist import CardList
from flow_kit import Advanced, ChoiceCards, SegmentPage, labelled, path_row
from rename_core import read_comicinfo
from ui_kit import BORDER, FONT, MUTED, TYPE_BODY, TYPE_HINT, DropZone, FlowRow, Toggle, entry, eta_text, flash_taskbar, switch_style, tool_button

BAD = (ic.DUPLICATE, ic.EXISTS, ic.NO_SERIES, ic.FAILED)
WATCH_MS = 3000
ORIGINAL = [(DELETE, DELETE, "Removed once the new comic has been checked."),
            (MOVE, MOVE, "Moved into an Archive folder, so you can still get it back."),
            (KEEP, KEEP, "Left where it is. The inbox keeps growing.")]


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def _read_all(q, items):
    for k, it in enumerate(items):
        try:
            ci = read_comicinfo(it.src)
        except Exception:  # noqa: BLE001 - a bad archive is reported when it is processed
            ci = {}
        q.put(("ci", it, ci, k + 1, len(items)))
    q.put(("read_done",))


def _run(q, todo, o, stop):
    for k, it in enumerate(todo):
        if stop.is_set():
            q.put(("stopped",))
            return
        q.put(("start", k, len(todo)))
        try:
            r = ic.add_comic(it.src, it.dest, o["junk"], o["patterns"], o["pages"], o["original"])
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            q.put(("fail", it, str(e) or type(e).__name__))
            continue
        if it.series:   # the series typed by hand goes into the comic's own ComicInfo.xml too
            try:
                apply_metadata(r["dest"], {"series": it.series}, False)
            except Exception as e:  # noqa: BLE001 - the comic is added; say that the tag was not written
                r["note"] = f"series not written to ComicInfo.xml ({e})"
        q.put(("ok", it, r))
    q.put(("finished",))


class IntakePage(SegmentPage):
    title = "Add to library"
    subtitle = "Bring new comics in, checked, cleaned, named and filed."
    defaults = {"inbox": "", "ready": "", "recursive": True, "watch": False, "rename": True, "folders": True, "junk": True,
                "patterns": "", "pages": False, "original": DELETE}
    choices = {"original": [DELETE, MOVE, KEEP]}
    split = True
    show_auto = False
    max_width = 1500

    def __init__(self, parent):
        super().__init__(parent)
        self.items, self.by_iid = [], {}
        self.q = None
        self.busy = None  # 'read' | 'run'
        self.stop_flag = threading.Event()
        self.rename_source = None  # callable giving the Renamer's settings; the app wires it up
        self.open_renamer = None   # callable that opens the Renamer; the app wires it up
        self._later_id = None
        self._watch_id = None
        self._settling = ic.Settling()
        self._seen = set()         # comics the watch has already listed, so one kept in the inbox is not listed again
        self._n = 0
        self._t0 = 0
        self.done = {"ok": 0, "fail": 0}
        self.stopped = False
        v, sw = self.vars, switch_style()

        # ---- Inbox
        self.make_panes(right_width=480, lo=380)
        self.s1 = self.add_block("Inbox", side="left")
        self.drop = DropZone(self.s1.body, "Drop comics or folders here", self.browse_files, self.browse_folder, self.browse_files,
                             compact=True)
        self.drop.pack(fill="x", padx=(0, 6))
        self.drop.add_extra("scan", "Scan inbox", self.scan_inbox, 110)
        row = labelled(self.s1.body, "Inbox folder")
        path_row(row.cell, v["inbox"], "Folder where new comics land").pack(fill="x", padx=(0, 6))
        row.pack(fill="x", pady=(8, 6))
        sub = ctk.CTkFrame(self.s1.body, fg_color="transparent")
        sub.pack(fill="x")
        Toggle(sub, text="Include subfolders", variable=v["recursive"], **sw).pack(side="left", padx=(0, 18))
        Toggle(sub, text="Watch this folder", variable=v["watch"], **sw).pack(side="left")
        self.lbl_watch = ctk.CTkLabel(self.s1.body, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=520)
        self.lbl_watch.pack(fill="x", pady=(4, 0))

        # ---- Review
        self.s2 = self.add_block("Review", side="left", grow=True)
        body = self.s2.body
        self.meta = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w")
        self.meta.pack(fill="x")
        bar = FlowRow(body)
        bar.pack(fill="x", pady=(2, 2))
        self.btn_all = tool_button(bar, "Select all", lambda: self.select_all(True), 90)
        self.btn_none = tool_button(bar, "Select none", lambda: self.select_all(False), 100)
        self.btn_clear = tool_button(bar, "Clear list", self.clear, 90)
        bar.add(self.btn_all)
        bar.add(self.btn_none)
        bar.add(self.btn_clear)
        self.note = ctk.CTkLabel(body, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=560)
        self.note.pack(side="bottom", fill="x", pady=(4, 0))
        self.status = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left", wraplength=560)
        self.progress = ctk.CTkProgressBar(body, height=14, corner_radius=0, border_width=3, border_color=BORDER, fg_color=BORDER, progress_color=("#FFD60A", "#FFD60A"))
        self.progress.set(0)
        self.cards = CardList(body, self._render, on_tick=self._tick, noun="comic", reorder=False, on_button=self._fix,
                              on_select=self._selected, empty="Drop comics here, or press Scan inbox.", busy=lambda: bool(self.busy),
                              card_h=58)
        self.cards.pack(fill="both", expand=True, padx=(0, 6), pady=(4, 0))
        body.bind("<Configure>", lambda e: [w.configure(wraplength=max(200, int(e.width / self._get_widget_scaling()) - 20))
                                            for w in (self.note, self.status)], add="+")

        # ---- Destination
        self.s3 = self.add_block("Destination")
        row = labelled(self.s3.body, "Ready folder")
        path_row(row.cell, v["ready"], "Folder for finished comics").pack(fill="x", padx=(0, 6))
        row.pack(fill="x", pady=(0, 8))
        Toggle(self.s3.body, text="File into series folders", variable=v["folders"], **sw).pack(anchor="w", pady=(0, 6))
        Toggle(self.s3.body, text="Name like the Renamer", variable=v["rename"], **sw).pack(anchor="w")
        self.lbl_names = ctk.CTkLabel(self.s3.body, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=420)
        self.lbl_names.pack(fill="x", pady=(6, 4))
        self.btn_naming = tool_button(self.s3.body, "Naming settings", self._open_renamer, 150)
        self.btn_naming.pack(anchor="w")
        self.fit_right(self.lbl_names)

        # ---- Clean-up
        self.s4 = self.add_block("Clean-up")
        ctk.CTkLabel(self.s4.body, text="Every comic is saved as a verified .cbz first; a .cbr is converted.", font=TYPE_HINT,
                     text_color=MUTED, anchor="w", justify="left", wraplength=420).pack(fill="x", pady=(0, 8))
        Toggle(self.s4.body, text="Remove junk files (Thumbs.db, .nfo…)", variable=v["junk"], **sw).pack(anchor="w", pady=(0, 6))
        Toggle(self.s4.body, text="Rename pages 001.jpg, 002.jpg…", variable=v["pages"], **sw).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(self.s4.body, text="The original comic", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w").pack(fill="x", pady=(0, 4))
        ChoiceCards(self.s4.body, v["original"], ORIGINAL, columns=1).pack(fill="x", padx=(0, 6))
        self.adv = Advanced(self.s4.body)
        self.adv.pack(fill="x", pady=(10, 0))
        row = labelled(self.adv.body, "Also remove files matching")
        entry(row.cell, v["patterns"], placeholder_text="zzz*, *.txt").pack(fill="x")
        row.pack(fill="x")
        self.adv.track(v, {"patterns": ""})

        self.watch("ready", "folders", "rename", "junk", "pages", "recursive", callback=self._later)
        self.watch("watch", "inbox", callback=self._watch_changed)
        self._redraw()

    # ------------------------------------------------------------------ settings and state
    def rename_settings(self):
        return ic.rename_settings(self.rename_source() if self.rename_source else None)

    def options(self):
        return {k: v.get() for k, v in self.vars.items()}

    def restore(self, saved):
        super().restore(saved)
        self._watch_changed()

    def on_show(self):
        """The Renamer's settings may have changed since this page was last open."""
        self.recompute()

    def _open_renamer(self):
        if self.open_renamer:
            self.open_renamer()

    def _later(self):
        if self._later_id is not None:
            self.after_cancel(self._later_id)
        self._later_id = self.after(350, self.recompute)

    # ------------------------------------------------------------------ the inbox: adding comics and watching it
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
        for it in new:
            self._n += 1
            it.iid = f"c{self._n}"
        self.items += new
        self.by_iid.update({it.iid: it for it in new})
        self.say("")
        self.busy, self.q = "read", queue.Queue()
        threading.Thread(target=_read_all, args=(self.q, new), daemon=True).start()
        self._redraw()
        self._poll()
        return len(new)

    def _watch_changed(self):
        on = self.vars["watch"].get() and Path(self.vars["inbox"].get().strip() or "?").is_dir()
        if on and self._watch_id is None:
            self._settling = ic.Settling()
            self._watch_id = self.after(WATCH_MS, self._watch_tick)
        elif not on and self._watch_id is not None:
            self.after_cancel(self._watch_id)
            self._watch_id = None
        self._draw_watch()

    def _draw_watch(self):
        on = self._watch_id is not None
        if self.vars["watch"].get() and not on:
            text = "Choose an Inbox folder to watch."
        elif on:
            text = "Watching the inbox while the app is open. New comics are listed here when they stop growing; nothing is added until you press the button."
        else:
            text = ""
        self.lbl_watch.configure(text=text)

    def _watch_tick(self):
        """Look at the inbox: a comic that is the same size as at the last look is listed for review (never added by itself)."""
        self._watch_id = self.after(WATCH_MS, self._watch_tick)
        inbox = self.vars["inbox"].get().strip()
        if self.busy or not Path(inbox).is_dir():
            return
        found = [p for p in ic.find_sources([Path(inbox)], self.vars["recursive"].get()) if str(p).lower() not in self._seen]
        ready = self._settling.stable(ic.sizes_of(found))
        if ready:
            self._seen.update(str(p).lower() for p in ready)
            n = self.add_paths(ready)
            if n:
                self.say(f"{_plural(n, 'new comic')} found in the inbox.")

    def clear(self):
        if self.busy:
            return
        self.items, self.by_iid = [], {}
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
        self._redraw()

    def _order(self):
        """Comics that need a look first (in their own order), then the rest."""
        bad = [it for it in self.items if it.status in BAD]
        return [it.iid for it in bad + [it for it in self.items if it.status not in BAD]]

    def _render(self, iid):
        it = self.by_iid.get(iid)
        if it is None:
            return {"title": str(iid)}
        ready = self.vars["ready"].get().strip()
        try:
            dest = str(it.dest.relative_to(ready)) if it.dest else ""
        except ValueError:
            dest = str(it.dest)
        tone = "bad" if it.status in BAD else "dim" if it.status in (ic.IN_PLACE, ic.DONE) else ""
        sub = ("→ " + dest + (f"   ({it.steps})" if it.steps else "")) if dest else it.note
        buttons = []
        if not self.busy:
            if it.status == ic.NO_SERIES:
                buttons.append(("series", "Set series…"))
            if it.status in (ic.DUPLICATE, ic.EXISTS) and not it.checked:
                buttons.append(("anyway", "Add anyway"))
            if it.status in BAD and it.checked:
                buttons.append(("skip", "Skip"))
        return {"num": None, "title": it.src.name, "sub": sub, "status": it.status, "tone": tone,
                "checked": it.checked if it.status in ic.PROCESSABLE else None, "buttons": buttons}

    def _selected(self):
        sel = self.cards.selected()
        it = self.by_iid.get(sel[0]) if len(sel) == 1 else None
        if not it:
            self.note.configure(text="")
            return
        text = it.note or ""
        if it.dest:
            text = (text + "   " if text else "") + f"Goes to {it.dest}"
        self.note.configure(text=text)

    # ------------------------------------------------------------------ cards
    def _tick(self, iid):
        if self.busy:
            return
        it = self.by_iid.get(iid)
        if it is None or it.status not in ic.PROCESSABLE + (ic.FAILED,):
            return
        sel = self.cards.selected()
        its = [self.by_iid[i] for i in sel if i in self.by_iid] if iid in sel and len(sel) > 1 else [it]
        value = not it.checked
        retry = False
        for x in its:
            x.checked, x.manual = value, True
            if x.status == ic.FAILED:
                x.error, retry = "", True   # ticking a failed comic tries it again
        if retry:
            self.recompute()
        else:
            self._after_change()

    def _fix(self, iid, key):
        """A button on a card: Add anyway, Set series… or Skip."""
        it = self.by_iid.get(iid)
        if it is None or self.busy:
            return
        if key == "series":
            sel = [self.by_iid[i] for i in self.cards.selected() if i in self.by_iid]
            its = sel if it in sel else [it]
            text = simpledialog.askstring("Set series", f"Series for {_plural(len(its), 'comic')}:", parent=self,
                                          initialvalue=it.series or it.fields.get("series") or "")
            if text and text.strip():
                for x in its:
                    x.series, x.manual = text.strip(), False
                self.recompute()
            return
        it.checked, it.manual = key == "anyway", True
        self._after_change()

    def select_all(self, value):
        if self.busy:
            return
        for it in self.items:
            if it.status in ic.PROCESSABLE:
                it.checked, it.manual = value, True
        self._after_change()

    def _after_change(self):
        self.cards.refresh()
        self._summary()
        self._footer()

    # ------------------------------------------------------------------ drawing
    def _redraw(self):
        order = self._order()
        self.cards.set_order(order)
        self.cards.refresh()
        self._summary()
        self._selected()
        self._draw_names()
        self._draw_watch()
        self._footer()
        for b in (self.btn_all, self.btn_none, self.btn_clear):
            b.configure(state="normal" if self.items and not self.busy else "disabled")

    def _draw_names(self):
        if not self.vars["rename"].get():
            text = "Comics keep their own file names."
        else:
            tpl = self.rename_settings()["folder_tpl"]
            where = f"series folders ({tpl})" if self.vars["folders"].get() else "the Ready folder itself"
            text = f"Named by the Renamer's rules and filed in {where}."
        self.lbl_names.configure(text=text)

    def _summary(self):
        n = len(self.items)
        if self.busy == "read":
            self.meta.configure(text="Reading the comics…")
        elif not n:
            self.meta.configure(text="")
        else:
            go = sum(1 for it in self.items if it.checked and it.status in ic.PROCESSABLE)
            flagged = sum(1 for it in self.items if it.status in BAD)
            text = f"{_plural(n, 'comic')} · {go} to add"
            if flagged:
                text += f" · {flagged} need a look"
            self.meta.configure(text=text)

    def _footer(self):
        n = len(self.items)
        go = sum(1 for it in self.items if it.checked and it.status in ic.PROCESSABLE)
        failed = [it for it in self.items if it.status == ic.FAILED]
        ready = self.vars["ready"].get().strip()
        side = []
        if ready and Path(ready).is_dir():
            side.append(("Open Ready folder", self.open_ready))
        if failed and not self.busy:
            side.append((f"Retry {len(failed)} failed", self.retry))
        for w in (self.progress, self.status):
            w.pack_forget()
        if self.busy == "run" or self.status.cget("text"):
            self.status.pack(fill="x", pady=(6, 0), before=self.cards)
        if self.busy:
            self.progress.pack(fill="x", pady=(6, 0), before=self.cards)
        if self.busy == "run":
            self.set_footer(self.status.cget("text") or "Adding…", "Stop", self.stop, secondary=side)
        elif self.busy:
            self.set_footer("Reading the comics…", "Add comics", self.apply, enabled=False, secondary=side)
        elif not n:
            self.set_footer("Drop comics or scan the inbox to begin.", "Add comics", self.apply, enabled=False, secondary=side)
        elif not ready:
            self.set_footer("Choose a Ready folder first.", "Add comics", self.apply, enabled=False, secondary=side)
        else:
            self.set_footer(f"{go} of {_plural(n, 'comic')} ticked.", f"Add {_plural(go, 'comic')}" if go else "Add comics",
                            self.apply, enabled=go > 0, secondary=side)

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
        msg = f"Add {_plural(len(todo), 'comic')} to {o['ready']}?\n\n{how}"
        if dup:
            msg += f"\n\n{dup} of them look like comics that are already there."
        if not messagebox.askyesno("Add to library", msg, icon="warning"):
            return
        self.busy, self.q = "run", queue.Queue()
        self.stop_flag.clear()
        self.stopped = False
        self.done = {"ok": 0, "fail": 0}
        self._t0 = time.time()
        self.progress.set(0)
        self.say("Starting…")
        self._redraw()
        threading.Thread(target=_run, args=(self.q, todo, o, self.stop_flag), daemon=True).start()
        self._poll()

    def stop(self):
        self.stop_flag.set()
        self.say("Stopping after this comic…")
        self._footer()

    def retry(self):
        for it in self.items:
            if it.status == ic.FAILED:
                it.error, it.checked, it.manual = "", True, True
        self.recompute()
        self.apply()

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
                    self.say(eta_text(msg[1], msg[2], self._t0) if msg[1] else f"1 of {msg[2]}")
                    self._footer()
                elif kind == "ok":
                    it, r = msg[1], msg[2]
                    it.status, it.note = ic.DONE, f"Saved as {r['dest'].name}" + (f"; {r['note']}" if r.get("note") else "")
                    self.done["ok"] += 1
                    inbox = self.vars["inbox"].get().strip()
                    if inbox and Path(inbox) in it.src.parents:
                        ic.prune_empty(it.src.parent, inbox)
                    self.cards.refresh()
                elif kind == "fail":
                    it = msg[1]
                    it.error = msg[2]
                    it.status, it.note = ic.FAILED, msg[2]
                    self.done["fail"] += 1
                    self.cards.refresh()
                else:  # finished or stopped
                    self.stopped = kind == "stopped"
                    self._finish()
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _finish(self):
        self.busy, self.q = None, None
        ok, bad = self.done["ok"], self.done["fail"]
        self.items = [it for it in self.items if it.status != ic.DONE]
        self.by_iid = {it.iid: it for it in self.items}
        self.progress.set(1)
        text = ("Stopped. " if self.stopped else "") + f"Added {_plural(ok, 'comic')}"
        if bad:
            text += f" · {bad} failed (click a card to read why)"
        self.say(text, err=bool(bad))
        if ok:
            flash_taskbar(self.winfo_toplevel())
        self.recompute()

    def open_ready(self):
        ready = self.vars["ready"].get().strip()
        if ready and Path(ready).exists():
            os.startfile(ready)  # Windows

    def apply_theme(self):
        super().apply_theme()
        self.cards.apply_theme()

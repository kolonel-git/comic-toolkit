"""Reading Order page: put issues in the order you want to read them, then record that order inside each CBZ's
ComicInfo.xml (and optionally in the filenames, or in a new folder of copies). On the shared page shell in two columns with a
divider you can drag. Left: Comics (adding issues) and Order (the list). Right, scrolling on its own: Stamp (how the order is
recorded) and Review (what will happen, then the run)."""
import itertools
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import reading_order as ro
from archive_tools import BACKUP, REPLACE
from comic_core import COMIC_EXT, find_comics, natural_key
from cardlist import CardList
from flow_kit import Advanced, SegmentPage, labelled
from reading_orders import ReadingOrders
from rename_core import read_comicinfo
from ui_kit import (BG, BORDER, HEAD, MUTED, PANEL, TEXT, TYPE_BODY, TYPE_HINT, DropZone, FlowRow, Toggle, button, divider,
                    entry, menu, popup_menu, switch_style, textbox, tool_button, tooltip)

ASK, ALWAYS, NEVER = "Ask me", "Always mark it", "Never"
MARKS = [ASK, ALWAYS, NEVER]
ADVANCED_DEFAULTS = {"prefix": ro.PREFIX_OFF, "drop_issue": False, "copy": False, "original": BACKUP, "mark_copies": ASK}


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


@dataclass
class Row:
    path: Path
    ci: dict
    why_not: str = None  # why the file can't be written, if it can't
    checked: bool = True
    plan: dict = None
    note: str = ""  # result of the last write ("Copied", ...), cleared when anything changes
    iid: str = ""
    view: dict = None  # what the card says: num, title, new, arc, status, sub, tone, checked


def _load(q, paths):
    for p in paths:
        why = ro.writable(p)
        q.put(("row", Row(p, {} if why else read_comicinfo(p), why)))
    q.put(("loaded",))


def _write(q, jobs, backup, dest_dir):
    for k, (row, writes, new_name) in enumerate(jobs):
        q.put(("start", k, len(jobs)))
        try:
            new = ro.apply_item(row.path, writes, new_name, backup, dest_dir)
            q.put(("ok", row, new, read_comicinfo(new) if dest_dir is None else None))
        except Exception as e:  # noqa: BLE001 - keep going, report at the end
            q.put(("fail", row, str(e)))
    q.put(("finished",))


class OrderPage(SegmentPage):
    title = "Reading order"
    subtitle = "Put issues in the order you want to read them and save it in each comic."
    defaults = {"store": ro.STORY, "numbering": ro.NUM_PLAIN, "prefix": ro.PREFIX_OFF, "copy": False,
                "original": BACKUP, "copy_parent": "", "drop_issue": False, "mark_copies": ASK}
    choices = {"store": ro.STORES, "numbering": ro.NUMBERINGS, "prefix": ro.PREFIXES, "original": [BACKUP, REPLACE],
               "mark_copies": MARKS}
    split = True
    show_auto = False
    max_width = 1500

    def __init__(self, parent):
        super().__init__(parent)
        self.rows, self.by_iid = [], {}
        self._ids = itertools.count(1)
        self.q = None
        self.busy = None  # 'load' | 'write'
        self.arc, self.group = ctk.StringVar(), ctk.StringVar()
        self._orders = ReadingOrders()   # the folders marked as reading orders (the app shares one list between tools)
        self.last_dest = None            # the folder the last run of copies went to
        self.on_marked = None            # the app is told when a folder was marked
        self.dest_dir = None

        # ---- Comics
        self.make_panes(right_width=460, lo=360)
        self.s1 = self.add_block("Comics", side="left")
        self.drop = DropZone(self.s1.body, "Drop comics or folders here", self.add_files, self.add_folder, self.add_files,
                             compact=True)
        self.drop.pack(fill="x", padx=(0, 6))
        self.btn_known = self.drop.add_extra("known", "Open a reading order ▾", self._show_known, 170)

        # ---- Order
        self.s2 = self.add_block("Order", side="left", grow=True)
        body = self.s2.body
        self.meta = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=TEXT, anchor="w")   # (kept up to date, not shown: the block's summary says it)
        bar = FlowRow(body)
        bar.pack(fill="x", pady=(0, 2))
        self.tools = {}
        groups = [[("suggest", "Suggest order ▾", 112, self._show_suggest)],
                  [("top", "Top", 44, lambda: self.to_edge(True)), ("up", "▲", 30, lambda: self.shift(-1)),
                   ("down", "▼", 30, lambda: self.shift(1)), ("bottom", "Bottom", 58, lambda: self.to_edge(False))],
                  [("undo", "Undo", 50, lambda: self.undo())],
                  [("remove", "Remove", 64, self.remove), ("clear", "Clear", 52, self.clear)]]
        for g, group in enumerate(groups):
            if g:
                bar.add(divider(bar), divider=True)
            for key, text, width, cmd in group:
                self.tools[key] = tool_button(bar, text, cmd, width)
                bar.add(self.tools[key])
        for key, tip in (("up", "Move the selected cards up (Alt+Up)"), ("down", "Move the selected cards down (Alt+Down)"),
                         ("undo", "Take back the last move (Ctrl+Z)")):
            tooltip(self.tools[key], tip)
        self.hint = ctk.CTkLabel(body, text="Hold a card and drag it. Ctrl or Shift selects several, or drag a box; they move together. "
                                 "Alt+Up / Alt+Down move them, Ctrl+Z undoes. Untick a card to skip it (it keeps its number).", font=TYPE_HINT,
                                 text_color=MUTED, anchor="w", justify="left", wraplength=560)
        self.hint.pack(side="bottom", fill="x", pady=(2, 0))
        self.status = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left", wraplength=560)
        self.cards = CardList(body, self._render, on_reorder=self._moved, on_tick=self._tick, noun="issue",
                              empty="Add a folder above, then put the issues in reading order.",
                              busy=lambda: bool(self.busy), on_stack=lambda _: self._buttons())
        self.cards.pack(fill="both", expand=True, padx=(0, 6))
        body.bind("<Configure>", lambda e: [w.configure(wraplength=max(200, int(e.width / self._get_widget_scaling()) - 20))
                                            for w in (self.hint, self.status)], add="+")

        # ---- Stamp
        v = self.vars
        sw = switch_style()
        self.s3 = self.add_block("Stamp")
        body = self.s3.body
        row = labelled(body, "Reading order name")
        entry(row.cell, self.arc).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        row = labelled(body, "Record the order as")
        menu(row.cell, v["store"], ro.STORES).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        row = labelled(body, "Arc numbers")
        menu(row.cell, v["numbering"], ro.NUMBERINGS).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        row = labelled(body, "Series group (optional)")
        entry(row.cell, self.group).pack(fill="x")
        self.group_hint = ctk.CTkLabel(row.cell, text="Labels every issue, e.g. the event or crossover name.", font=TYPE_HINT,
                                       text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.group_hint.pack(fill="x", pady=(4, 0))
        row.pack(fill="x", pady=(0, 10))
        self.adv = Advanced(body)
        self.adv.pack(fill="x", pady=(0, 4))
        row = labelled(self.adv.body, "Also number the filenames")
        menu(row.cell, v["prefix"], ro.PREFIXES).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        Toggle(self.adv.body, text="Remove issue numbers", variable=v["drop_issue"], **sw).pack(anchor="w")
        self.drop_hint = ctk.CTkLabel(self.adv.body, text="YACReader sorts by issue number before filename. Removing it makes "
                                      "YACReader use the filename, so pair it with a filename prefix.", font=TYPE_HINT,
                                      text_color=MUTED, anchor="w", justify="left", wraplength=420)
        self.drop_hint.pack(fill="x", pady=(4, 10))
        Toggle(self.adv.body, text="Copy to a new folder instead of changing the originals", variable=v["copy"],
               **sw).pack(anchor="w", pady=(0, 10))
        self.orig_row = labelled(self.adv.body, "Original file")
        menu(self.orig_row.cell, v["original"], [BACKUP, REPLACE]).pack(fill="x")
        self.orig_row.pack(fill="x", pady=(0, 10))
        self.mark_row = labelled(self.adv.body, "Mark the folder of copies as a reading order")
        menu(self.mark_row.cell, v["mark_copies"], MARKS).pack(fill="x")
        self.mark_hint = ctk.CTkLabel(self.mark_row.cell, text="A marked folder is left out of Library stats and the "
                                      "duplicate check.", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                                      wraplength=420)
        self.mark_hint.pack(fill="x", pady=(4, 0))
        self.adv.track(v, ADVANCED_DEFAULTS)

        # ---- Review
        self.s4 = self.add_block("Review")
        body = self.s4.body
        self.headline = ctk.CTkLabel(body, text="", font=(HEAD, 16), text_color=TEXT, anchor="w", justify="left", wraplength=440)
        self.headline.pack(fill="x")
        self.subline = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.subline.pack(fill="x", pady=(2, 6))
        self.yac = ctk.CTkLabel(body, text="YACReader shows this after you turn on ComicInfo import (Settings > General) "
                                "and update the library.", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left",
                                wraplength=440)
        self.yac.pack(fill="x", pady=(0, 8))
        self.btn_details = tool_button(body, "Details", self.preview, 90)
        self.btn_details.pack(anchor="w")
        self.progress = ctk.CTkProgressBar(body, height=14, corner_radius=0, border_width=3, border_color=BORDER,
                                           fg_color=BORDER, progress_color=("#FFD60A", "#FFD60A"))
        self.progress.set(0)

        self.fit_right(self.group_hint, self.drop_hint, self.mark_hint, self.headline, self.subline, self.yac)
        self._preview_win = None
        self.watch("store", "numbering", "prefix", "copy", "drop_issue", "original", callback=self._replan)
        self.arc.trace_add("write", lambda *_: self._replan())
        self.group.trace_add("write", lambda *_: self._replan())
        self.watch("copy", callback=self._toggle_rows)
        self._toggle_rows()
        self._replan()

    @property
    def btn_apply(self):
        return self.bar_btn

    @property
    def btn_preview(self):
        return self.side_row.winfo_children()[0]

    # --- the reading orders the user has marked ---
    @property
    def orders(self):
        return self._orders

    @orders.setter
    def orders(self, value):
        self._orders = value
        self._fill_known()

    def _fill_known(self):
        """(The menu reads the list when it is opened, so there is nothing to refresh.)"""

    def say(self, msg, err=False):
        """The status line takes room from the list, so it shows only while it has something to say."""
        super().say(msg, err)
        if msg:
            self.status.pack(side="bottom", fill="x", pady=(4, 0), after=self.hint)
        else:
            self.status.pack_forget()

    def _show_known(self):
        items = [(f"{Path(f).name}    {Path(f).parent}", lambda f=f: self.add_paths([Path(f)])) for f in self._orders.folders]
        popup_menu(self.btn_known, items or [("No reading orders marked yet", None)])

    # --- theme ---
    def apply_theme(self):
        super().apply_theme()
        self.cards.apply_theme()

    def _toggle_rows(self):
        copy = self.vars["copy"].get()
        if copy:
            self.orig_row.pack_forget()
            self.mark_row.pack(fill="x", pady=(0, 4))
        else:
            self.mark_row.pack_forget()
            self.orig_row.pack(fill="x", pady=(0, 10))

    # --- adding issues ---
    def add_files(self):
        files = filedialog.askopenfilenames(title="Choose comics", filetypes=[("Comic archives", "*.cbz *.cbr")])
        if files:
            self.add_paths([Path(f) for f in files])

    def add_folder(self):
        d = filedialog.askdirectory(title="Folder of comics")
        if d:
            self.add_paths([Path(d)])

    def add_paths(self, paths):
        """Add files, or every comic inside folders. Duplicates and non-comics are ignored."""
        if self.busy:
            return
        have = {str(r.path).lower() for r in self.rows}
        new = []
        for p in map(Path, paths):
            found = find_comics(p, True) if p.is_dir() else [p] if p.suffix.lower() in COMIC_EXT else []
            for f in sorted(found, key=natural_key) if p.is_dir() else found:
                if str(f).lower() not in have:
                    have.add(str(f).lower())
                    new.append(f)
        if not new:
            self.say("Nothing new to add.")
            return
        self.say("")
        self.busy, self.q = "load", queue.Queue()
        self.meta.configure(text=f"Reading {len(new)} file{'s' if len(new) != 1 else ''}…")
        threading.Thread(target=_load, args=(self.q, new), daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(100):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "row":
                    row = msg[1]
                    row.iid = f"r{next(self._ids)}"
                    row.view = {"num": "", "title": row.path.name, "new": "", "arc": "", "status": "", "sub": "", "tone": "",
                                "checked": None}
                    self.cards.append([row.iid])
                    self.rows.append(row)
                    self.by_iid[row.iid] = row
                elif kind == "loaded":
                    self.busy = self.q = None
                    self.cards.forget()
                    self._replan()
                    return
                elif kind == "start":
                    self.progress.set(msg[1] / msg[2])
                    self.say(f"Writing {msg[1] + 1} of {msg[2]}")
                elif kind == "ok":
                    self._wrote(msg)
                elif kind == "fail":
                    self.failed.append(f"{msg[1].path.name}: {msg[2]}")
                    msg[1].note = "Failed"
                else:  # finished
                    self._end_write()
                    return
        except queue.Empty:
            pass
        self.after(40, self._poll)

    # --- ordering ---
    def _sync(self):
        self.rows = [self.by_iid[i] for i in self.cards.order]

    SUGGESTIONS = [("series", "Series, volume, year, issue number"), ("date", "Publication date"),
                   ("issue", "Issue number"), ("name", "File name")]

    def _show_suggest(self):
        popup_menu(self.tools["suggest"], [(label, lambda k=key: self.suggest(k)) for key, label in self.SUGGESTIONS])

    def suggest(self, kind="series"):
        """Sort the list: by series, volume, year and issue number (the default), by publication date, by issue number or by
        file name. It can be undone."""
        if self.busy or not self.rows:
            return
        keys = {"series": lambda r: ro.suggest_key(r.path), "date": lambda r: ro.date_key(r.path, r.ci),
                "issue": lambda r: ro.issue_key(r.path), "name": lambda r: ro.name_key(r.path)}
        label = dict(self.SUGGESTIONS)[kind]
        done = self.cards.apply([r.iid for r in sorted(self.rows, key=keys[kind])], flash=[])
        self.say(f"Sorted by {label.lower()}." if done else f"Already in that order ({label.lower()}).")

    def _moved(self):
        """The cards were put in a new order (by dragging, the keys, the buttons or Undo): number them again."""
        self._sync()
        self._replan()

    def shift(self, delta):
        """Move every selected card one place up or down, together."""
        self.cards.move_selected(delta)

    def to_edge(self, top):
        """Send every selected card to the very top (or bottom), keeping their order."""
        self.cards.to_edge(top)

    def undo(self):
        if self.cards.undo():
            self.say("Took back the last move.")

    def _tick(self, iid):
        """A press on a tick box: every selected card follows the one clicked."""
        sel = self.cards.sel
        rows = [self.by_iid[i] for i in self.cards.selected()] if iid in sel and len(sel) > 1 else [self.by_iid[iid]]
        value = not self.by_iid[iid].checked
        for r in rows:
            r.checked = value
        self._replan()

    def _render(self, iid):
        row = self.by_iid.get(iid)
        return row.view if row and row.view else {"title": str(iid)}

    def _buttons(self):
        n = len(self.rows)
        busy = bool(self.busy)
        for key in ("clear", "remove", "up", "down", "top", "bottom", "suggest"):
            self.tools[key].configure(state="normal" if n and not busy else "disabled")
        self.tools["undo"].configure(state="normal" if self.cards.can_undo and not busy else "disabled")

    def remove(self):
        sel = self.cards.selected()
        if self.busy or not sel:
            return
        i = min(self.cards.order.index(x) for x in sel)
        for x in sel:
            self.by_iid.pop(x, None)
        self.cards.remove(sel)
        self._sync()
        if self.cards.order:
            self.cards.select([self.cards.order[min(i, len(self.cards.order) - 1)]])
        self._replan()

    def clear(self):
        if self.busy:
            return
        self.cards.clear()
        self.rows, self.by_iid = [], {}
        self.say("")
        self._replan()

    # --- plan and table ---
    def _plan_options(self):
        return {"name": self.arc.get().strip(), "store": self.vars["store"].get(),
                "numbering": self.vars["numbering"].get(), "group": self.group.get().strip(),
                "prefix": self.vars["prefix"].get(), "drop_issue": self.vars["drop_issue"].get()}

    def _replan(self, keep_notes=False):
        o, total = self._plan_options(), len(self.rows)
        for k, row in enumerate(self.rows, 1):
            if not keep_notes:
                row.note = ""
            row.plan = ro.plan_item(row.path, row.ci, k, total, o, row.why_not) if o["name"] or row.why_not else None
            old = ro.current_arc(row.ci, o["store"])[0] or ""
            if row.plan:
                status = row.note or ("Skipped" if not row.checked and not row.plan["blocked"] else row.plan["status"])
                new_name = row.plan["new_name"] if row.plan["new_name"] != row.path.name else ""
            else:
                status, new_name = row.note or "", ""
            blocked = bool(row.why_not)
            tone = "bad" if blocked or row.note == "Failed" else "dim" if status in ("No change", "Skipped") else ""
            sub = "  ·  ".join(x for x in ((f"→ {new_name}" if new_name else ""), (f"now in “{old}”" if old else "")) if x)
            row.view = {"num": ro.number_text(k, total, o["numbering"]), "title": row.path.name, "new": new_name, "arc": old,
                        "status": status, "sub": sub, "tone": tone, "checked": bool(row.checked and not blocked)}
        self.cards.refresh()
        ready = self._todo()
        n = len(self.rows)
        self.meta.configure(text=(f"{_plural(n, 'issue')} · {len(ready)} to write" if o["name"] else
                                  f"{_plural(n, 'issue')} · enter a reading order name") if n
                            else "Add issues to begin")
        self._buttons()
        self._sync_view(o, ready)

    def _sync_view(self, o, ready):
        """The block summaries, the review on the right and the footer."""
        n = len(self.rows)
        folders = len({r.path.parent for r in self.rows})
        self.s1.set_summary(f"{_plural(n, 'issue')} from {_plural(folders, 'folder')}" if n else "")
        custom = [r.path for r in self.rows] != sorted((r.path for r in self.rows), key=ro.suggest_key)
        todo = f" · {len(ready)} to write" if o["name"] else " · enter a name"
        self.s2.set_summary(f"{_plural(n, 'issue')} · {'custom order' if custom else 'suggested order'}{todo}" if n else "")
        self.s3.set_summary(f"{o['store']} · numbers {o['numbering']}" if o["name"] else "")
        self.s1.set_state("done" if n else "active")
        self.s2.set_state("active" if n else "locked")
        self.s3.set_state("active" if n else "locked")
        self.s4.set_state("active" if n and o["name"] else "locked")
        skipped = sum(1 for r in self.rows if not r.checked and not r.why_not)
        blocked = sum(1 for r in self.rows if r.why_not)
        same = sum(1 for r in self.rows if r.checked and r.plan and not r.plan["blocked"] and r not in ready)
        copy = self.vars["copy"].get()
        if not n:
            head, sub = "Add issues first.", ""
        elif not o["name"]:
            head, sub = "Enter a reading order name.", ""
        else:
            head = f"Will stamp {_plural(len(ready), 'comic')}"
            for count, word in ((same, "already correct"), (skipped, "unticked"), (blocked, "can't be stamped")):
                if count:
                    head += f"  ·  {count} {word}"
            renames = sum(1 for r in ready if r.plan["new_name"] != r.path.name)
            if copy:
                sub = (f"Copies go into a new folder named “{ro.folder_name(o['name'])}” inside a folder you choose; "
                       "the originals are not changed.")
            else:
                sub = "Originals are kept in an Archive folder as .bak." if self.vars["original"].get() == BACKUP \
                    else "Files are replaced in place."
                if renames:
                    sub += f" {_plural(renames, 'file')} will also be renamed."
        self.headline.configure(text=head)
        self.subline.configure(text=sub)
        if self.busy == "write":
            self.progress.pack(fill="x", pady=(10, 0))
        else:
            self.progress.pack_forget()
        if self.busy == "write":
            text, label, enabled = self.status.cget("text") or "Stamping…", "Stamping…", False
        elif self.busy:
            text, label, enabled = "Reading the comics…", f"Stamp {_plural(len(ready), 'comic')}" if ready else "Stamp comics", False
        elif not n:
            text, label, enabled = "Add some issues to begin.", "Stamp comics", False
        elif not o["name"]:
            text, label, enabled = "Enter a reading order name to stamp.", "Stamp comics", False
        else:
            text, label, enabled = f"{_plural(len(ready), 'comic')} to stamp.", f"Stamp {_plural(len(ready), 'comic')}" if ready \
                else "Nothing to stamp", bool(ready)
        self.set_footer(text, label, self.apply, enabled=enabled,
                        secondary=[("Preview changes", self.preview), ("Mark as reading order", self.mark_clicked)])
        self.btn_preview.configure(state="normal" if n and o["name"] and not self.busy else "disabled")

    def _todo(self):
        o = self._plan_options()
        if not o["name"]:
            return []
        return [r for r in self.rows if r.checked and r.plan and not r.plan["blocked"]
                and (r.plan["writes"] or r.plan["new_name"] != r.path.name)]

    # --- preview ---
    def preview_text(self):
        """What a write would do, as plain text. Nothing is changed."""
        o = self._plan_options()
        todo = {r.iid for r in self._todo()}
        copy = self.vars["copy"].get()
        total = len(self.rows)
        blocked = sum(1 for r in self.rows if r.why_not)
        skipped = sum(1 for r in self.rows if not r.checked and not r.why_not)
        same = sum(1 for r in self.rows if r.checked and r.plan and not r.plan["blocked"] and r.iid not in todo)
        head = [f"Reading order “{o['name']}”: {total} issue{'s' if total != 1 else ''}",
                f"  {len(todo)} would be written, {same} already correct, {skipped} unticked, {blocked} can't be written",
                f"  Recorded as: {o['store']} · numbers {o['numbering']}" + (f" · series group {o['group']}" if o["group"] else "")]
        if o["drop_issue"]:
            head.append("  Issue numbers would be removed, so YACReader sorts by filename"
                        + ("" if o["prefix"] != ro.PREFIX_OFF else " (no filename prefix is on, so that is the old name order)"))
        renames = sum(1 for r in self.rows if r.iid in todo and r.plan["new_name"] != r.path.name)
        if copy:
            parent = self.vars["copy_parent"].get()
            folder = ro.folder_name(o["name"])
            where = (f"{parent}\\{folder}" if parent else
                     f"a folder named “{folder}” inside a folder you choose when writing")
            head.append(f"  Copies would be saved in {where}; the originals are not changed")
        else:
            head.append("  Originals would be " + ("kept in an Archive folder as .bak" if self.vars["original"].get() == BACKUP
                                                   else "replaced in place"))
            if renames:
                head.append(f"  {renames} file{'s' if renames != 1 else ''} would be renamed")
        body = []
        for k, r in enumerate(self.rows, 1):
            if not r.checked and not r.why_not:
                lines = [r.path.name, "    unticked: left alone"]
            else:
                lines = ro.describe_item(r.path, r.ci, r.plan, o["store"]) if r.plan else [r.path.name]
            body.append(f"{ro.number_text(k, total, o['numbering']):>4}.  " + lines[0])
            body += ["        " + ln for ln in lines[1:]]
        return "\n".join(head + ["", *body])

    def preview(self):
        if not self.rows:
            return
        if not self._plan_options()["name"]:
            self.say("Enter a reading order name first.", err=True)
            return
        if self._preview_win is not None and self._preview_win.winfo_exists():
            self._preview_win.destroy()
        win = self._preview_win = ctk.CTkToplevel(self)
        win.title("Preview: nothing has been changed")
        win.geometry("820x600")
        win.configure(fg_color=BG)
        box = textbox(win, font=("Consolas", 12), fg_color=PANEL, text_color=TEXT, border_color=BORDER,
                             border_width=3, corner_radius=0, wrap="none")
        box.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        box.insert("1.0", self.preview_text())
        box.configure(state="disabled")
        button(win, "Close", win.destroy).pack(pady=(0, 16))
        win.after(150, win.lift)

    # --- writing ---
    def apply(self):
        if self.busy:
            return
        o = self._plan_options()
        todo = self._todo()
        if not o["name"]:
            self.say("Enter a reading order name first.", err=True)
            return
        if not todo:
            return
        copy = self.vars["copy"].get()
        dest_dir = None
        if copy:
            parent = filedialog.askdirectory(title="Where should the new folder go?",
                                             initialdir=self.vars["copy_parent"].get() or None)
            if not parent:
                return
            self.vars["copy_parent"].set(parent)
            dest_dir = Path(parent) / ro.folder_name(o["name"])
        self.dest_dir = dest_dir
        backup = self.vars["original"].get() == BACKUP
        renames = sum(1 for r in todo if r.plan["new_name"] != r.path.name)
        msg = f"Write the reading order “{o['name']}” to {len(todo)} issue{'s' if len(todo) != 1 else ''}?\n\n"
        if copy:
            msg += f"Copies are saved in:\n{dest_dir}\n\nThe originals are not changed."
        else:
            msg += "Originals are kept in an Archive folder." if backup else "Files are replaced in place."
            if renames:
                msg += f"\n{renames} file{'s' if renames != 1 else ''} will also be renamed."
        if not messagebox.askyesno("Write reading order", msg, icon="warning"):
            return
        self.applied, self.failed, self.copied = 0, [], copy
        self.busy, self.q = "write", queue.Queue()
        self.btn_apply.configure(state="disabled")
        jobs = [(r, r.plan["writes"], r.plan["new_name"]) for r in todo]
        threading.Thread(target=_write, args=(self.q, jobs, backup, dest_dir), daemon=True).start()
        self._poll()

    def _wrote(self, msg):
        _, row, new, ci = msg
        self.applied += 1
        if ci is not None:  # written in place: follow the file and its new metadata
            row.path, row.ci = new, ci
        row.note = "Copied" if self.copied else "Written"

    def _end_write(self):
        self.busy = self.q = None
        self.progress.set(0)
        self._replan(keep_notes=True)
        text = f"{'Copied' if self.copied else 'Wrote'} {self.applied} issue{'s' if self.applied != 1 else ''}"
        if self.failed:
            text += f" · {len(self.failed)} failed ({self.failed[0]})"
        self.say(text, err=bool(self.failed))
        if self.copied and self.applied and self.dest_dir is not None:
            self.last_dest = self.dest_dir
            self._offer_mark(self.dest_dir)
        self._replan(keep_notes=True)

    # --- marking the folder as a reading order (so Library stats and the duplicate check leave it out) ---
    def _mark_candidate(self):
        """The folder Mark as reading order would mark: where the last copies went, else the one folder all the
        listed issues sit in (an existing reading order opened here)."""
        if self.last_dest is not None and Path(self.last_dest).is_dir():
            return Path(self.last_dest)
        parents = {r.path.parent for r in self.rows}
        return next(iter(parents)) if len(parents) == 1 else None

    def mark_clicked(self):
        folder = self._mark_candidate()
        if folder is None:
            self.say("Nothing to mark yet: stamp copies into a new folder, or open one folder that is already a reading order.",
                     err=True)
            return
        if self._orders.covers(folder):
            self.say(f"“{folder.name}” is already marked as a reading order.")
            return
        if not messagebox.askyesno("Mark as reading order", f"Mark this folder as a reading order?\n\n{folder}\n\n"
                                   "Library stats and the duplicate check will leave its comics out.", icon="question"):
            return
        self._mark(folder)

    def _mark(self, folder):
        if self._orders.add(folder):
            self.say(f"Marked “{Path(folder).name}” as a reading order.")
            if self.on_marked:
                self.on_marked(folder)
        self._fill_known()

    def _offer_mark(self, folder):
        """Copies were made in `folder`: mark it as a reading order, ask, or leave it, as the setting says."""
        if self._orders.covers(folder):
            return
        mode = self.vars["mark_copies"].get()
        if mode == NEVER:
            return
        if mode == ALWAYS:
            self._mark(folder)
            return
        answer = self._ask_mark(folder)
        if answer in ("once", "always"):
            self._mark(folder)
        if answer == "always":
            self.vars["mark_copies"].set(ALWAYS)

    def _ask_mark(self, folder):
        """A small window: Mark it, Always mark new ones, or Not now. Returns "once", "always" or None."""
        win = ctk.CTkToplevel(self)
        win.title("Mark as reading order")
        win.geometry("460x230")
        win.transient(self.winfo_toplevel())
        result = {"v": None}
        ctk.CTkLabel(win, text="Mark this folder as a reading order?", font=(HEAD, 15), anchor="w").pack(fill="x", padx=20, pady=(18, 4))
        ctk.CTkLabel(win, text=f"{folder}\n\nA marked folder stays out of Library stats and the duplicate check, so these "
                     "copies are not counted twice.", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                     wraplength=420).pack(fill="x", padx=20)
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(side="bottom", fill="x", padx=20, pady=16)

        def close(v):
            result["v"] = v
            win.destroy()
        button(row, "Mark it", lambda: close("once"), primary=True, width=110).pack(side="right")
        button(row, "Always mark new ones", lambda: close("always"), width=170).pack(side="right", padx=(0, 8))
        button(row, "Not now", lambda: close(None), width=90).pack(side="right", padx=(0, 8))
        win.protocol("WM_DELETE_WINDOW", lambda: close(None))
        win.after(150, lambda: (win.lift(), win.focus_force()))
        win.grab_set()
        self.wait_window(win)
        return result["v"]

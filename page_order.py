"""Reading Order page: put issues in the order you want to read them, then record that order inside each
CBZ's ComicInfo.xml (and optionally in the filenames, or in a new folder of copies)."""
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import reading_order as ro
from archive_tools import BACKUP, REPLACE
from comic_core import COMIC_EXT, find_comics, natural_key
from rename_core import read_comicinfo
from ui_kit import (ACCENT, BG, BORDER, FONT, MUTED, PANEL, TEXT, DropZone, Form, Page, apply_tree_theme, build_tree,
                    button, entry, menu, switch_style, title_block, toolbar)


@dataclass
class Row:
    path: Path
    ci: dict
    why_not: str = None  # why the file can't be written, if it can't
    checked: bool = True
    plan: dict = None
    note: str = ""  # result of the last write ("Copied", ...), cleared when anything changes
    iid: str = ""


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


class OrderPage(Page):
    defaults = {"store": ro.STORY, "numbering": ro.NUM_PLAIN, "prefix": ro.PREFIX_OFF, "copy": False,
                "original": BACKUP, "copy_parent": "", "drop_issue": False}
    choices = {"store": ro.STORES, "numbering": ro.NUMBERINGS, "prefix": ro.PREFIXES, "original": [BACKUP, REPLACE]}

    def __init__(self, parent):
        super().__init__(parent)
        self.rows, self.by_iid = [], {}
        self.q = None
        self.busy = None  # 'load' | 'write'
        self._drag, self._moved = None, False
        self.arc, self.group = ctk.StringVar(), ctk.StringVar()

        title_block(self.main, "Reading order",
                    "Arrange issues in the order you want to read them, then record it in each comic.")
        self.drop = DropZone(self.main, "Drop comics or folders here, or add them below", self.add_files,
                             self.add_folder, self.add_files)
        self.drop.pack(fill="x")
        self.meta = ctk.CTkLabel(self.main, text="", font=(FONT, 13), text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(14, 6))
        bar = ctk.CTkFrame(self.main, fg_color=BG)
        bar.pack(fill="x", pady=(0, 8))
        self.tools = toolbar(
            bar, [("suggest", "Suggest order", 104, self.suggest)],
            [("top", "Top", 48, lambda: self.to_edge(True)), ("up", "▲", 34, lambda: self.shift(-1)),
             ("down", "▼", 34, lambda: self.shift(1)), ("bottom", "Bottom", 64, lambda: self.to_edge(False))],
            [("remove", "Remove", 72, self.remove), ("clear", "Clear", 60, self.clear)])
        self.progress = ctk.CTkProgressBar(self.main, height=3, corner_radius=2, fg_color=BORDER,
                                           progress_color=ACCENT)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 8))
        wrap, self.tree = build_tree(self.main, [
            ("sel", "", 38, False), ("num", "#", 52, False), ("file", "File", 220, True),
            ("new", "New name", 200, True), ("current", "Current arc", 120, False), ("status", "Status", 200, False)], selectmode="extended")
        wrap.pack(fill="both", expand=True)
        self.tree.bind("<Button-1>", self._press)
        self.tree.bind("<B1-Motion>", self._motion)
        self.tree.bind("<ButtonRelease-1>", self._release)
        ctk.CTkLabel(self.main, text="Select several rows (Ctrl or Shift) and drag them, or use ▲ ▼, to move them together. "
                     "Untick a row to leave it alone (it keeps its place in the numbering).", font=(FONT, 12), text_color=MUTED, anchor="w",
                     justify="left", wraplength=620).pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(self.main, text="YACReader shows this after you turn on ComicInfo import (Settings > General) "
                     "and update the library.", font=(FONT, 12), text_color=MUTED, anchor="w", justify="left",
                     wraplength=620).pack(fill="x", pady=(2, 0))

        v = self.vars
        sw = switch_style()
        self.form.heading("Reading order")
        box = self.form.add("Name")
        entry(box, self.arc).pack(fill="x")
        menu(self.form.add("Record the order as"), v["store"], ro.STORES).pack(fill="x")
        menu(self.form.add("Arc numbers"), v["numbering"], ro.NUMBERINGS).pack(fill="x")
        box = self.form.add("Series group (optional)")
        entry(box, self.group).pack(fill="x")
        ctk.CTkLabel(box, text="Labels every issue, e.g. the event or crossover name.", font=(FONT, 11),
                     text_color=MUTED, anchor="w", justify="left", wraplength=260).pack(fill="x", pady=(4, 0))
        self.form.heading("Filenames and sorting")
        menu(self.form.add("Also number the filenames"), v["prefix"], ro.PREFIXES).pack(fill="x")
        box = self.form.add("Sorting in YACReader")
        ctk.CTkSwitch(box, text="Remove issue numbers", variable=v["drop_issue"], **sw).pack(anchor="w")
        ctk.CTkLabel(box, text="YACReader sorts by issue number before filename. Removing it makes YACReader use "
                     "the filename, so pair it with a filename prefix.", font=(FONT, 11), text_color=MUTED,
                     anchor="w", justify="left", wraplength=260).pack(fill="x", pady=(4, 0))
        self.form.heading("Output")
        box = self.form.add("Originals")
        ctk.CTkSwitch(box, text="Copy to a new folder instead", variable=v["copy"], **sw).pack(anchor="w")
        self.orig_row = self.form.add("Original file")
        menu(self.orig_row, v["original"], [BACKUP, REPLACE]).pack(fill="x")

        self.btn_apply = button(self.footer, "Write reading order", self.apply, primary=True)
        self.btn_apply.pack(pady=(0, 8))
        self.btn_preview = button(self.footer, "Preview changes", self.preview)
        self.btn_preview.pack()
        self._preview_win = None
        self.watch("store", "numbering", "prefix", "copy", "drop_issue", callback=self._replan)
        self.arc.trace_add("write", lambda *_: self._replan())
        self.group.trace_add("write", lambda *_: self._replan())
        self.watch("copy", callback=self._toggle_rows)
        self._toggle_rows()
        self._replan()

    # --- theme ---
    def apply_theme(self):
        apply_tree_theme(self.tree)

    def _toggle_rows(self):
        Form.show(self.orig_row, not self.vars["copy"].get())

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
                    row.iid = self.tree.insert("", "end", values=("", "", row.path.name, "", "", ""))
                    self.rows.append(row)
                    self.by_iid[row.iid] = row
                elif kind == "loaded":
                    self.busy = self.q = None
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
        self.rows = [self.by_iid[i] for i in self.tree.get_children()]

    def suggest(self):
        if self.busy or not self.rows:
            return
        for row in sorted(self.rows, key=lambda r: ro.suggest_key(r.path)):
            self.tree.move(row.iid, "", "end")
        self._sync()
        self._replan()
        self.say("Sorted by series, volume, year and issue number.")

    def _reorder(self, order):
        """Put the table rows in `order` (a list of iids) and refresh numbers."""
        for i, iid in enumerate(order):
            self.tree.move(iid, "", i)
        self._sync()
        self._replan()

    def shift(self, delta):
        """Move every selected row one place up or down, together."""
        sel = self.tree.selection()
        if self.busy or not sel:
            return
        order = list(self.tree.get_children())
        new = ro.move_block(order, sel, delta)
        if new != order:
            self._reorder(new)
        self.tree.see(sel[0] if delta < 0 else sel[-1])

    def to_edge(self, top):
        """Send every selected row to the very top (or bottom), keeping their order."""
        sel = self.tree.selection()
        if self.busy or not sel:
            return
        order = list(self.tree.get_children())
        new = ro.send_to_edge(order, sel, top)
        if new != order:
            self._reorder(new)
        self.tree.see(sel[0] if top else sel[-1])

    def remove(self):
        sel = self.tree.selection()
        if self.busy or not sel:
            return
        i = min(self.tree.index(s) for s in sel)
        for s in sel:
            self.by_iid.pop(s, None)
        self.tree.delete(*sel)
        self._sync()
        kids = self.tree.get_children()
        if kids:
            self.tree.selection_set(kids[min(i, len(kids) - 1)])
        self._replan()

    def clear(self):
        if self.busy:
            return
        self.tree.delete(*self.tree.get_children())
        self.rows, self.by_iid = [], {}
        self.say("")
        self._replan()

    # mouse: tick box in column 1; elsewhere click / Ctrl+click / Shift+click select, and dragging moves
    # the whole selection as a block
    def _press(self, e):
        self._drag, self._moved = None, False
        iid = self.tree.identify_row(e.y)
        if self.tree.identify_region(e.x, e.y) != "cell" or not iid:
            return None
        if self.tree.identify_column(e.x) == "#1":
            sel = self.tree.selection()
            rows = [self.by_iid[i] for i in sel] if iid in sel and len(sel) > 1 else [self.by_iid[iid]]
            value = not self.by_iid[iid].checked  # every ticked row follows the one clicked
            for r in rows:
                r.checked = value
            self._replan()
            return "break"
        if e.state & 0x5:  # Shift or Ctrl: normal selection, no drag
            return None
        self._drag = iid
        if iid in self.tree.selection() and len(self.tree.selection()) > 1:
            return "break"  # keep the multi-selection so it can be dragged
        return None

    def _motion(self, e):
        if not self._drag or self.busy:
            return
        target = self.tree.identify_row(e.y)
        if not target:
            return
        sel = self.tree.selection()
        sel = sel if self._drag in sel else (self._drag,)
        order = list(self.tree.get_children())
        new = ro.drop_block(order, sel, target)
        if new != order:
            self._moved = True
            for i, iid in enumerate(new):
                self.tree.move(iid, "", i)

    def _release(self, _):
        if not self._drag:
            return
        drag, self._drag = self._drag, None
        if self._moved:
            self._sync()
            self._replan()
        elif len(self.tree.selection()) > 1 and drag in self.tree.selection():
            self.tree.selection_set(drag)  # a plain click on one of several selected rows selects just it

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
            self.tree.item(row.iid, values=(
                "☑" if row.checked and not blocked else "☐", ro.number_text(k, total, o["numbering"]),
                row.path.name, new_name, old, status),
                tags=("bad",) if blocked or row.note == "Failed" else ("dim",) if status in ("No change", "Skipped") else ())
        ready = self._todo()
        n = len(self.rows)
        self.meta.configure(text=(f"{n} issue{'s' if n != 1 else ''} · {len(ready)} to write" if o["name"] else
                                  f"{n} issue{'s' if n != 1 else ''} · enter a reading order name") if n
                            else "Add issues to begin")
        can = bool(ready) and not self.busy
        self.btn_apply.configure(state="normal" if can else "disabled")
        self.btn_preview.configure(state="normal" if n and o["name"] and not self.busy else "disabled")
        for key in ("clear", "remove", "up", "down", "top", "bottom", "suggest"):
            self.tools[key].configure(state="normal" if n and not self.busy else "disabled")

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
        box = ctk.CTkTextbox(win, font=("Consolas", 12), fg_color=PANEL, text_color=TEXT, border_color=BORDER,
                             border_width=1, corner_radius=8, wrap="none")
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

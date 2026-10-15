"""Bulk folder page: covers from every CBZ/CBR in a folder. Three steps, each showing everything it decides:
1 the comics found, 2 the settings beside a live preview of what you will get, 3 a review and the run."""
import os
import queue
import threading
import time
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from comic_core import (COMIC_EXT, CONFLICTS, FORMATS, HEIGHTS, NAMES, ORG_FLAT, ORG_SERIES, ORGS,
                        WHERE_BESIDE, WHERE_CUSTOM, WHERE_SUB, WHERES, Comic, export_cover,
                        common_root, find_comics, picked_files, plan_dest, sanitize, series_name)
from flow_kit import (ChoiceCards, Disclosure, StepPage, facts, labelled, mini_table, path_row, section)
from ui_kit import (BORDER, DANGER, EDGE, FONT, HEAD, MUTED, PANEL, TEXT, Toggle, DropZone, entry, eta_text,
                    flash_taskbar, menu, switch_style, textbox, tool_button)

TABLE_CAP = 2000  # rows shown in the comics table (every comic is still processed)


def _worker(q, files, root, o, stop):
    used = set()
    for k, src in enumerate(files):
        if stop.is_set():
            q.put(("stopped",))
            return
        q.put(("start", k, len(files)))
        comic = None
        try:
            comic = Comic(src)
            status, dest = export_cover(comic, root, o, used)
            q.put((status, src, dest))
        except Exception as e:  # noqa: BLE001 - one bad file must not stop the batch
            q.put(("failed", src, str(e)))
        finally:
            if comic:
                comic.close()
    q.put(("done",))


# what each "where do the covers go" card sets
RECIPES = [
    ("folder", "In one Covers folder", {"where": WHERE_SUB, "organize": ORG_FLAT}),
    ("series", "A folder for each series", {"where": WHERE_SUB, "organize": ORG_SERIES}),
    ("beside", "Next to each comic", {"where": WHERE_BESIDE}),
    ("choose", "A folder I choose", {"where": WHERE_CUSTOM, "organize": ORG_FLAT}),
]
EXT = {"JPG": ".jpg", "PNG": ".png", "WebP": ".webp"}
IF_EXISTS = {"Overwrite": "replaced", "Skip": "left alone, no new cover", "Keep both": "kept, the new cover gets a number"}


def _size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


class BulkPage(StepPage):
    title = "Bulk folder"
    subtitle = "Save the cover of every comic in a folder."
    defaults = {"recursive": True, "where": WHERE_SUB, "subfolder": "Covers", "custom": "",
                "organize": ORG_FLAT, "format": "Original", "quality": 90, "height": "Original size",
                "name": NAMES[0], "conflict": "Overwrite"}
    choices = {"where": WHERES, "organize": ORGS, "format": FORMATS, "height": list(HEIGHTS),
               "name": NAMES, "conflict": CONFLICTS}

    def __init__(self, parent):
        super().__init__(parent)
        self.folder = None
        self.picked = None  # comics chosen one by one instead of a folder
        self.files = []
        self.q = None
        self.stop = threading.Event()
        self.out_dir = None
        self.result = None  # counts of the last finished run
        self._t0 = 0
        self._syncing = False
        self.plan = []
        v = self.vars

        # ---- 1 the comics
        self.s1 = self.add_step("Choose your comics")
        top = ctk.CTkFrame(self.s1.body, fg_color="transparent")
        top.pack(fill="x")
        top.grid_columnconfigure((0, 1), weight=1, uniform="half")
        self.drop = DropZone(top, "Drop a folder here, or add a folder or comics", self.browse, self.browse,
                             self.browse_files)
        self.drop.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        found = ctk.CTkFrame(top, fg_color="transparent")
        found.grid(row=0, column=1, sticky="nsew")
        section(found, "What was found").pack(fill="x", pady=(0, 8))
        self.found = facts(found, ["Comics", "Series", "Size on disk", "File types", "From"])
        self.found["_grid"].pack(fill="x")
        self.meta = ctk.CTkLabel(self.s1.body, text="", font=(FONT, 14, "bold"), text_color=TEXT, anchor="w")
        self.meta.pack(fill="x", pady=(14, 6))
        Toggle(self.s1.body, text="Include comics in subfolders", variable=v["recursive"],
               **switch_style()).pack(anchor="w", pady=(0, 10))
        self.table_box, self.table = mini_table(self.s1.body, [
            ("name", "Comic", 300, True), ("series", "Series", 170, True), ("where", "Folder", 220, True),
            ("type", "Type", 56, False), ("size", "Size", 84, False)], rows=6,
            empty="No comics yet. Add a folder or pick some comics above.")
        self.table_box.pack(fill="x", padx=(0, 6))

        # ---- 2 the settings and the preview, side by side
        self.s2 = self.add_step("Set up the covers")
        cols = ctk.CTkFrame(self.s2.body, fg_color="transparent")
        cols.pack(fill="x")
        cols.grid_columnconfigure(0, weight=3, uniform="cols")
        cols.grid_columnconfigure(1, weight=2, uniform="cols")
        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 22))
        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")

        section(left, "Where do the covers go?").pack(fill="x", pady=(0, 10))
        self.recipe = ctk.StringVar(value="folder")
        self.cards = ChoiceCards(left, self.recipe, [(k, t, "") for k, t, _ in RECIPES], columns=2)
        self.cards.pack(fill="x")
        self.choose_row = path_row(left, v["custom"], "Save covers to")
        self.custom_note = ctk.CTkLabel(left, text="You chose your own layout under Advanced.", font=(FONT, 12),
                                        text_color=MUTED, anchor="w")
        self.picture_head = section(left, "What do they look like?")
        self.picture_head.pack(fill="x", pady=(14, 0))
        self.picture = ctk.CTkFrame(left, fg_color="transparent")
        self.picture.pack(fill="x")
        self.refresh_quality = self.image_options(self.picture)
        section(left, "What are they called?").pack(fill="x", pady=(4, 6))
        for text, key, values in (("Name of each cover file", "name", NAMES), ("If a cover with that name already exists", "conflict", CONFLICTS)):
            row = labelled(left, text)
            menu(row.cell, v[key], values).pack(fill="x")
            row.pack(fill="x", pady=(0, 10))
        self.adv = Disclosure(left, "Advanced: folder name and layout")
        self.adv.pack(fill="x", pady=(4, 0))
        self.sub_row = labelled(self.adv.body, "Name of the covers folder")
        entry(self.sub_row.cell, v["subfolder"]).pack(fill="x")
        self.sub_row.pack(fill="x", pady=(0, 10))
        self.where_row = None
        for text, key, values in (("Where", "where", WHERES), ("Folder layout", "organize", ORGS)):
            row = labelled(self.adv.body, text)
            menu(row.cell, v[key], values).pack(fill="x")
            row.pack(fill="x", pady=(0, 10))
            if self.where_row is None:
                self.where_row = row  # the covers-folder name row is shown just above this one
        self.recipe.trace_add("write", lambda *_: self._recipe_picked())

        section(right, "Preview: where each cover will go").pack(fill="x", pady=(0, 8))
        self.preview_box, self.preview = mini_table(right, [("src", "Comic", 140, True), ("dest", "Cover file", 190, True),
                                                          ("state", "Status", 70, False)],
                                                    rows=9, empty="Choose comics to see where each cover will go.")
        self.preview_box.pack(fill="x", padx=(0, 6))
        self.plan_facts = facts(right, ["Covers", "Saved in", "Already there"], wrap=280)
        self.plan_facts["_grid"].pack(fill="x", pady=(12, 0))

        # ---- 3 review and run
        self.s3 = self.add_step("Extract")
        self.ready = ctk.CTkFrame(self.s3.body, fg_color=PANEL, border_color=BORDER, border_width=EDGE, corner_radius=0)
        self.checks = []
        for _ in range(4):
            self.checks.append(ctk.CTkLabel(self.ready, text="", font=(FONT, 14), text_color=TEXT, anchor="w",
                                            justify="left", wraplength=900))
        self.progress = ctk.CTkProgressBar(self.s3.body, height=14, corner_radius=0, border_width=3, border_color=BORDER,
                                           fg_color=BORDER, progress_color=("#FFD60A", "#FFD60A"))
        self.progress.set(0)
        self.status = ctk.CTkLabel(self.s3.body, text="", font=(FONT, 12), text_color=MUTED, anchor="w")
        self.result_box = ctk.CTkFrame(self.s3.body, fg_color=PANEL, border_color=BORDER, border_width=EDGE, corner_radius=0)
        self.result_title = ctk.CTkLabel(self.result_box, text="", font=(HEAD, 18), text_color=TEXT, anchor="w")
        self.result_title.pack(fill="x", padx=16, pady=(14, 0))
        self.result_sub = ctk.CTkLabel(self.result_box, text="", font=(FONT, 13), text_color=MUTED, anchor="w", justify="left",
                                       wraplength=760)
        self.result_sub.pack(fill="x", padx=16, pady=(2, 10))
        row = ctk.CTkFrame(self.result_box, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 14))
        tool_button(row, "Do another folder", self.reset, 150).pack(side="left", padx=(0, 12))
        tool_button(row, "Extract again", self.again, 120).pack(side="left")
        self.log_label = ctk.CTkLabel(self.s3.body, text="Every file", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w")
        self.log = textbox(self.s3.body, font=("Consolas", 12), height=150, wrap="none")
        self.log.configure(state="disabled")

        self.watch("recursive", callback=self.rescan)
        self.watch("where", "organize", callback=self._vars_changed)
        self.watch("subfolder", "custom", "format", "name", "conflict", callback=self.refresh)
        self._vars_changed()
        self.refresh()

    # --- choosing comics ---
    def browse(self):
        d = filedialog.askdirectory(title="Folder of CBZ / CBR files")
        if d:
            self.set_folder(d)

    def browse_files(self):
        files = filedialog.askopenfilenames(title="Choose comics", filetypes=[
            ("Comic archives", "*.cbz *.cbr"), ("All", "*.*")])
        if files:
            self.set_files(files)

    def set_files(self, paths):
        """Take the covers of these comics only, instead of a whole folder."""
        files = picked_files(paths, COMIC_EXT)
        if not files:
            self.say("None of those files are .cbz or .cbr comics.", err=True)
            return
        self.picked = files
        self.folder = common_root(files)
        self.drop.set(f"{len(files)} comic{'s' if len(files) != 1 else ''} chosen from {self.folder}")
        self.say("")
        self._new_comics()

    def set_folder(self, folder):
        self.folder = Path(folder)
        self.picked = None
        self.drop.set(str(self.folder))
        self._new_comics()

    def _new_comics(self):
        self.result = None
        self.rescan()
        self.update_idletasks()
        self.reveal(self.s2)

    def reveal(self, card):
        """Scroll so the step you should look at next is in view."""
        canvas = self.scroll._parent_canvas
        total = max(1, self.col.winfo_height())
        canvas.yview_moveto(0.0 if card is self.steps[0] else max(0.0, min(1.0, (card.winfo_y() - 16) / total)))

    def rescan(self):
        if self.picked is not None:
            self.files = [p for p in self.picked if p.exists()]
        else:
            self.files = find_comics(self.folder, self.vars["recursive"].get()) if self.folder else []
        self._fill_table()
        self.refresh()

    def reset(self):
        """Start over with another folder."""
        if self.q:
            return
        self.folder = self.picked = None
        self.files = []
        self.result = None
        self.drop.set(None)
        self._log(None)
        self.say("")
        self._fill_table()
        self.refresh()
        self.reveal(self.s1)

    def again(self):
        """Run the same job again."""
        self.result = None
        self.refresh()

    def _fill_table(self):
        self.table.delete(*self.table.get_children())
        for p in self.files[:TABLE_CAP]:
            try:
                size = _size(p.stat().st_size)
            except OSError:
                size = "?"
            try:
                where = str(p.parent.relative_to(self.folder)) if self.folder else str(p.parent)
            except ValueError:
                where = str(p.parent)
            self.table.insert("", "end", values=(p.name, series_name(p.stem), where,
                                                 p.suffix.lower().lstrip("."), size))

    # --- the recipe cards and the settings behind them ---
    def options(self):
        return self.state()

    def _recipe_of_vars(self):
        v = self.vars
        where, org = v["where"].get(), v["organize"].get()
        for key, _t, want in RECIPES:
            if where == want["where"] and (want.get("organize") in (None, org)):
                return key
        return ""  # a layout only the advanced menus can make

    def _vars_changed(self):
        """The advanced menus changed where or how the covers go: move the card selection along."""
        if not self._syncing:
            self._syncing = True
            self.recipe.set(self._recipe_of_vars())
            self._syncing = False
        self.refresh()

    def _recipe_picked(self):
        if self._syncing:
            return
        want = {k: w for k, _t, w in RECIPES}.get(self.recipe.get())
        if want:
            self._syncing = True
            for name, value in want.items():
                self.vars[name].set(value)
            if self.vars["where"].get() == WHERE_SUB and not self.vars["subfolder"].get().strip():
                self.vars["subfolder"].set("Covers")
            self._syncing = False
        self.refresh()

    def _planned(self, key=None):
        """[(comic, cover path)] for the current settings, or under another card's settings."""
        o = dict(self.options())
        if key:
            o.update(next(w for k, _t, w in RECIPES if k == key))
        if o["where"] == WHERE_SUB and not o["subfolder"].strip():
            o["subfolder"] = "Covers"
        if o["where"] == WHERE_CUSTOM and not o["custom"].strip():
            return None
        ext = EXT.get(o["format"], ".jpg")
        return [(p, plan_dest(p, self.folder, o, ext)) for p in self.files[:TABLE_CAP]]

    def _short(self, path, width=46):
        try:
            path = Path(path).relative_to(self.folder)
        except ValueError:
            pass
        text = str(path)
        return text if len(text) <= width else "…" + text[-(width - 1):]

    def _destination(self):
        o = self.options()
        if o["where"] == WHERE_BESIDE:
            return "Next to each comic"
        if o["where"] == WHERE_CUSTOM:
            return o["custom"].strip() or "The folder you choose"
        sub = sanitize(o["subfolder"] or "Covers")
        return str(self.folder / sub) if self.folder else f"A “{sub}” folder"

    def _sentence(self):
        o, n = self.options(), len(self.files)
        what = {"Original": "original-format", "JPG": "JPG", "PNG": "PNG", "WebP": "WebP"}.get(o["format"], o["format"])
        return f"{n} comic{'s' if n != 1 else ''}  →  {what} covers"

    # --- keep the screen in step ---
    def refresh(self):
        v = self.vars
        n = len(self.files)
        self.refresh_quality()
        # step 1: what was found
        if not self.folder:
            self.meta.configure(text="", text_color=MUTED)
            for k in ("Comics", "Series", "Size on disk", "File types", "From"):
                self.found[k].configure(text="None yet" if k == "Comics" else "–")
        else:
            self.meta.configure(text=f"{n} comic{'s' if n != 1 else ''} {'chosen' if self.picked is not None else 'found'}"
                                     + ("" if n else ": try a different folder or turn on subfolders"),
                                text_color=TEXT if n else MUTED)
            total, kinds = 0, {}
            for p in self.files:
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
                kinds[p.suffix.lower()] = kinds.get(p.suffix.lower(), 0) + 1
            self.found["Comics"].configure(text=str(n))
            self.found["Series"].configure(text=str(len({series_name(p.stem) for p in self.files})))
            self.found["Size on disk"].configure(text=_size(total))
            self.found["File types"].configure(text=", ".join(f"{c} {k}" for k, c in sorted(kinds.items())) or "–")
            self.found["From"].configure(text=str(self.folder) if self.picked is None else f"{self.folder} (comics you picked)")
        # step 2: cards, rows, preview
        for key, _t, _w in RECIPES:
            plan = self._planned(key) if n else None
            self.cards.describe(key, ("e.g. " + self._short(plan[0][1], 40)) if plan else
                                {"folder": "All covers together", "series": "Sorted by series", "beside": "Beside its comic",
                                 "choose": "In a folder you pick"}[key])
        if self.recipe.get() == "choose":
            self.choose_row.pack(fill="x", pady=(0, 6), after=self.cards)
        else:
            self.choose_row.pack_forget()
        if self.recipe.get() == "":
            self.custom_note.pack(fill="x", pady=(0, 6), after=self.cards)
        else:
            self.custom_note.pack_forget()
        if v["where"].get() == WHERE_SUB:
            self.sub_row.pack(fill="x", pady=(0, 10), before=self.where_row)
        else:
            self.sub_row.pack_forget()
        self.plan = self._planned() or []
        o = self.options()
        verdict = {"Overwrite": "Replaces", "Skip": "Skipped", "Keep both": "Numbered"}[o["conflict"]]
        self.preview.delete(*self.preview.get_children())
        for src, dest in self.plan[:9]:
            self.preview.insert("", "end", values=(src.stem, self._short(dest, 27), verdict if dest.exists() else "New"))
        exists = sum(1 for _s, d in self.plan if d.exists())
        self.plan_facts["Covers"].configure(text=f"{len(self.plan)}" + (" (the first 9 are shown)" if len(self.plan) > 9 else ""))
        self.plan_facts["Saved in"].configure(text=self._destination())
        self.plan_facts["Already there"].configure(
            text="None" if not exists else f"{exists} of {len(self.plan)}: {IF_EXISTS[o['conflict']]}")
        # step 3: the checks before the run (what is about to happen, and anything to look at first)
        what = {"Original": "in the format they already have", "JPG": f"as JPG (quality {int(o['quality'])})",
                "PNG": "as PNG", "WebP": f"as WebP (quality {int(o['quality'])})"}[o["format"]]
        lines = [f"✓  {n} cover{'s' if n != 1 else ''} will be saved {what}.",
                 f"✓  They go to: {self._destination()}",
                 "✓  Your comics are never changed. Only new cover images are written."]
        if exists:
            lines.insert(2, f"⚠  {exists} of {len(self.plan)} covers already exist and will be {IF_EXISTS[o['conflict']]}.")
        for label, text in zip(self.checks, lines + [""] * 4):
            label.pack_forget()
            label.configure(text=text, text_color=(DANGER if text.startswith("⚠") else TEXT))
            if text:
                label.pack(fill="x", padx=16, pady=(10, 0) if label is self.checks[0] else (4, 0))
        self.checks[len(lines) - 1].pack_configure(pady=(4, 10))
        self._sync_steps()

    def _sync_steps(self):
        n, running, done = len(self.files), bool(self.q), self.result is not None
        s1, s2, s3 = self.s1, self.s2, self.s3
        s1.set_hint("Add a folder or pick some comics. Everything that was found is listed here.")
        s2.set_hint("Choose where the covers go and how they look. The preview on the right changes as you do.")
        if not n:
            s1.set_state("active", "Start here")
            s1.set_summary("")
            s2.set_state("locked")
            s2.set_summary("Waiting for your comics")
            s3.set_state("locked")
            s3.set_summary("")
        else:
            s1.set_state("done")
            s1.set_summary(f"{n} comic{'s' if n != 1 else ''}")
            recipe = next((t for k, t, _w in RECIPES if k == self.recipe.get()), "Your own layout")
            s2.set_summary(f"{self.vars['format'].get()} · {recipe}")
            if running or done:
                s2.set_state("done")
                s3.set_state("active", "Working" if running else "Finished")
                s3.set_hint("Working. You can stop at any time with the button below." if running else
                            "Finished. Open the folder, or run it again, with the buttons below.")
            else:
                s2.set_state("active", "You are here")
                s3.set_state("idle", "Next")
                s3.set_hint("Nothing happens until you press the yellow button in the bar below.")
        # step 3 shows the checks before a run, progress during it, the result and the file list after it
        for w in (self.ready, self.progress, self.status, self.result_box, self.log_label, self.log):
            w.pack_forget()
        if not running and not done:
            self.ready.pack(fill="x", padx=(0, 6))
        if running:
            self.progress.pack(fill="x", pady=(2, 0))
        if running or self.status.cget("text"):
            self.status.pack(fill="x", pady=(6, 0))
        if done:
            self.result_box.pack(fill="x", padx=(0, 6))
        if running or done:
            self.log_label.pack(fill="x", pady=(14, 4))
            self.log.pack(fill="x", padx=(0, 6))
        # the pinned bar: which step you are on, and the one thing to press
        if running:
            self.set_bar("Step 3 of 3  ·  " + (self.status.cget("text") or "Working…"), "Stop", self.start)
        elif done:
            r = self.result
            word = "Stopped" if r["stopped"] else "Done"
            self.set_bar(f"{word}  ·  {r['saved']} cover{'s' if r['saved'] != 1 else ''} saved"
                         + (f", {r['failed']} failed" if r["failed"] else ""), "Open the covers folder", self.open_out,
                         enabled=bool(self.out_dir and self.out_dir.exists()), alt=("Extract again", self.again))
        elif not n:
            self.set_bar("Step 1 of 3  ·  Choose some comics to begin.", "Choose comics first", self.start, enabled=False)
        else:
            self.set_bar("Step 2 of 3  ·  Check the preview, then extract.",
                         f"Extract {n} cover{'s' if n != 1 else ''}", self.start)

    # --- run ---
    def stop_action(self):
        if self.q:
            self.stop.set()

    def start(self):
        if self.q:  # running: this button is "Stop"
            self.stop.set()
            self.bar_btn.configure(state="disabled", text="Stopping…")
            return
        o = self.options()
        if not self.folder or not self.files:
            self.say("Pick a folder that contains .cbz or .cbr files.", err=True)
            return
        if o["where"] == WHERE_CUSTOM and not o["custom"].strip():
            self.say("Choose a folder to save covers to.", err=True)
            self.s2.set_open(True)
            self.update_idletasks()
            self.reveal(self.s2)
            return
        self.out_dir = {WHERE_SUB: self.folder / sanitize(o["subfolder"]),
                        WHERE_CUSTOM: Path(o["custom"]), WHERE_BESIDE: self.folder}[o["where"]]
        self.counts = {"saved": 0, "skipped": 0, "failed": 0}
        self.failed = []
        self.stop.clear()
        self.q = queue.Queue()
        self.result = None
        self._t0 = time.time()
        self._log(None)
        self.say("")
        self.progress.set(0)
        self.refresh()
        self.s3.set_open(True)
        self.update_idletasks()
        self.reveal(self.s3)
        threading.Thread(target=_worker, args=(self.q, list(self.files), self.folder, o, self.stop),
                         daemon=True).start()
        self._poll()

    def _poll(self):
        try:
            for _ in range(50):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "start":
                    self.progress.set(msg[1] / msg[2])
                    c = self.counts
                    self.say(eta_text(msg[1], msg[2], self._t0) + f"  ·  {c['saved']} saved"
                             + (f", {c['skipped']} skipped" if c["skipped"] else "")
                             + (f", {c['failed']} failed" if c["failed"] else ""))
                    self.bar_text.configure(text=self.status.cget("text"))
                    if not self.status.winfo_ismapped():
                        self.refresh()
                elif kind in ("saved", "skipped"):
                    self.counts[kind] += 1
                    mark = "✓" if kind == "saved" else "↷"
                    self._log(f"{mark}  {msg[1].name}  →  {self._shorten(msg[2])}")
                elif kind == "failed":
                    self.counts["failed"] += 1
                    self.failed.append(f"{msg[1].name}: {msg[2]}")
                    self._log(f"✗  {msg[1].name}  {msg[2]}")
                else:
                    self._finish(kind == "stopped")
                    return
        except queue.Empty:
            pass
        self.after(60, self._poll)

    def _shorten(self, p):
        try:
            return str(p.relative_to(self.folder))
        except ValueError:
            return str(p)

    def _finish(self, stopped):
        self.q = None
        c = self.counts
        self.result = dict(c, stopped=stopped)
        self.progress.set(0 if stopped else 1)
        if time.time() - self._t0 > 5:
            flash_taskbar(self.winfo_toplevel())
        saved = c["saved"]
        self.result_title.configure(text=("Stopped. " if stopped else "Done. ") + f"{saved} cover{'s' if saved != 1 else ''} saved")
        parts = []
        if c["skipped"]:
            parts.append(f"{c['skipped']} skipped because the file already existed")
        if c["failed"]:
            parts.append(f"{c['failed']} could not be read")
        sub = ". ".join(parts) if parts else "Nothing went wrong."
        if c["failed"]:
            sub += "\n" + "\n".join(self.failed[:3]) + ("\n…" if len(self.failed) > 3 else "")
        self.result_sub.configure(text=sub)
        self.say("")
        self.refresh()

    def _log(self, line):
        self.log.configure(state="normal")
        if line is None:
            self.log.delete("1.0", "end")
        else:
            self.log.insert("end", line + "\n")
            self.log.see("end")
        self.log.configure(state="disabled")

    def open_out(self):
        if self.out_dir and self.out_dir.exists():
            os.startfile(self.out_dir)  # Windows

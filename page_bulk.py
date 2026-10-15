"""Bulk folder page: covers from every CBZ/CBR in a folder, on the shared page shell. Three segments:
Comics (what was found), Covers (where they go and how they look) and Review (what will happen, then the run)."""
import io
import os
import queue
import shutil
import threading
import time
import zipfile
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from comic_core import (COMIC_EXT, CONFLICTS, FORMATS, HEIGHTS, NAMES, ORG_FLAT, ORG_SERIES, ORGS,
                        WHERE_BESIDE, WHERE_CUSTOM, WHERE_SUB, WHERES, Comic, export_cover, find_extractor, is_page,
                        common_root, find_comics, natural_key, picked_files, plan_dest, sanitize, series_name)
from flow_kit import (Advanced, ChoiceCards, LazyTable, SegmentPage, labelled, path_row, section)
from ui_kit import (BORDER, DANGER, EDGE, FONT, HEAD, MUTED, PANEL, TEXT, TYPE_BODY, TYPE_HINT, DropZone, Toggle, entry,
                    eta_text, flash_taskbar, menu, switch_style, textbox, tool_button)


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


def _check(files, gen, q):
    """Look at every comic without extracting it: can it be opened, and how big is its first page? Posts
    ("bad", path, reason), ("size", bytes), ("progress", done, total) and finally ("checked", gen)."""
    have_rar = find_extractor() is not None
    for i, p in enumerate(files):
        try:
            if zipfile.is_zipfile(p):
                with zipfile.ZipFile(p) as z:
                    pages = sorted((n for n in z.namelist() if is_page(n)), key=natural_key)
                    if not pages:
                        q.put(("bad", p, "No images inside"))
                    elif i < 20:
                        q.put(("size", z.getinfo(pages[0]).file_size))
            elif not have_rar:
                q.put(("bad", p, "Needs a RAR extractor (7-Zip or unrar)"))
        except (OSError, zipfile.BadZipFile) as e:
            q.put(("bad", p, str(e) or "Cannot be opened"))
        if i % 25 == 0:
            q.put(("progress", i, len(files)))
    q.put(("checked", gen))


def _thumb(path):
    """A small picture of a comic's first page, for the table."""
    comic = Comic(path)
    try:
        img = Image.open(io.BytesIO(comic.read(comic.pages[0])))
        img.thumbnail((40, 56))
        return img.convert("RGB")
    finally:
        comic.close()


# what each "where do the covers go" card sets
RECIPES = [
    ("beside", "Next to each comic", {"where": WHERE_BESIDE}),
    ("folder", "One covers folder", {"where": WHERE_SUB, "organize": ORG_FLAT}),
    ("series", "A folder for each series", {"where": WHERE_SUB, "organize": ORG_SERIES}),
    ("choose", "Somewhere else", {"where": WHERE_CUSTOM, "organize": ORG_FLAT}),
]
EXT = {"JPG": ".jpg", "PNG": ".png", "WebP": ".webp"}
IF_EXISTS = {"Overwrite": "replaced", "Skip": "left alone, no new cover", "Keep both": "kept, the new cover gets a number"}
WOULD = {"Overwrite": "Would replace", "Skip": "Would skip", "Keep both": "Would number"}
CONFLICT_WORD = {"Overwrite": "replace existing", "Skip": "skip existing", "Keep both": "keep both"}
ADVANCED_DEFAULTS = {"format": "Original", "quality": 90, "height": "Original size", "name": NAMES[0], "subfolder": "Covers"}


def _size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


class BulkPage(SegmentPage):
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
        self.failed = []    # [(path, reason)] of the last run
        self.reviewed = False
        self.dry = False
        self.memory = {}    # settings last used with each folder
        self._t0 = 0
        self._syncing = False
        self._loading = False
        self.bad = {}       # path -> why it cannot be read
        self.sizes = []     # byte sizes of the first pages of a sample of comics
        self.checking = None
        self.check_q = None
        self._gen = 0
        self._last_refresh = 0
        self._pending_refresh = False
        v = self.vars

        # ---- Comics
        self.s1 = self.add_segment("Comics")
        self.drop = DropZone(self.s1.body, "Drop a folder here, or add a folder or comics", self.browse, self.browse,
                             self.browse_files)
        self.drop.pack(fill="x", padx=(0, 6), pady=(0, 12))
        Toggle(self.s1.body, text="Include comics in subfolders", variable=v["recursive"],
               **switch_style()).pack(anchor="w", pady=(0, 10))
        self.comics = LazyTable(self.s1.body, [
            ("name", "Comic", 300, True), ("series", "Series", 170, True), ("where", "Folder", 220, True),
            ("type", "Type", 56, False), ("size", "Size", 84, False)], rows=8,
            empty="No comics yet. Add a folder or pick some comics above.")
        self.comics.pack(fill="x")

        # ---- Covers
        self.s2 = self.add_segment("Covers")
        body = self.s2.body
        section(body, "Save covers").pack(fill="x", pady=(0, 10))
        self.recipe = ctk.StringVar(value="folder")
        self.cards = ChoiceCards(body, self.recipe, [(k, t, "") for k, t, _ in RECIPES], columns=2)
        self.cards.pack(fill="x")
        self.choose_row = path_row(body, v["custom"], "Save covers to")
        self.custom_note = ctk.CTkLabel(body, text="You chose your own layout under Advanced options.", font=TYPE_HINT,
                                        text_color=MUTED, anchor="w")
        section(body, "If a cover already exists").pack(fill="x", pady=(8, 10))
        ChoiceCards(body, v["conflict"], [
            ("Skip", "Skip", "Leave the old cover alone"),
            ("Overwrite", "Replace", "Write the new cover over it"),
            ("Keep both", "Keep both", "Give the new cover a number")], columns=3).pack(fill="x")
        self.adv = Advanced(body)
        self.adv.pack(fill="x", pady=(8, 12))
        self.refresh_quality = self.image_options(self.adv.body)
        row = labelled(self.adv.body, "Name of each cover file")
        menu(row.cell, v["name"], NAMES).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
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
        self.adv.track(v, ADVANCED_DEFAULTS)
        tool_button(body, "Review the covers", self.go_review, 170).pack(anchor="e")
        self.recipe.trace_add("write", lambda *_: self._recipe_picked())

        # ---- Review
        self.s3 = self.add_segment("Review")
        self.headline = ctk.CTkLabel(self.s3.body, text="", font=(HEAD, 16), text_color=TEXT, anchor="w", justify="left",
                                     wraplength=900)
        self.headline.pack(fill="x")
        self.subline = ctk.CTkLabel(self.s3.body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                                    wraplength=900)
        self.subline.pack(fill="x", pady=(2, 8))
        self.problems = ctk.CTkFrame(self.s3.body, fg_color="transparent", height=0)  # (an empty frame is 200 px tall otherwise)
        self.problems.pack(fill="x")
        self.tools = ctk.CTkFrame(self.s3.body, fg_color="transparent")
        self.tools.pack(fill="x", pady=(4, 8))
        self.exist_label = ctk.CTkLabel(self.tools, text="", font=TYPE_BODY, text_color=TEXT, anchor="w")
        self.exist_label.pack(side="left")
        self.details_btn = tool_button(self.tools, "Details", self.show_existing, 80)
        self.covers_on = ctk.BooleanVar(value=False)
        Toggle(self.tools, text="Show covers", variable=self.covers_on, **switch_style()).pack(side="right")
        self.covers_on.trace_add("write", lambda *_: self._covers_toggled())
        self.review = LazyTable(self.s3.body, [("src", "Comic", 300, True), ("dest", "Cover file", 300, True),
                                                ("state", "Status", 120, False)], rows=9,
                                empty="Choose comics to see where each cover will go.")
        self.review.pack(fill="x")
        self.progress = ctk.CTkProgressBar(self.s3.body, height=14, corner_radius=0, border_width=3, border_color=BORDER,
                                           fg_color=BORDER, progress_color=("#FFD60A", "#FFD60A"))
        self.progress.set(0)
        self.status = ctk.CTkLabel(self.s3.body, text="", font=(FONT, 12), text_color=MUTED, anchor="w")
        self.result_box = ctk.CTkFrame(self.s3.body, fg_color=PANEL, border_color=BORDER, border_width=EDGE, corner_radius=0)
        self.result_title = ctk.CTkLabel(self.result_box, text="", font=(HEAD, 18), text_color=TEXT, anchor="w")
        self.result_title.pack(fill="x", padx=16, pady=(14, 0))
        self.result_sub = ctk.CTkLabel(self.result_box, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                                       wraplength=760)
        self.result_sub.pack(fill="x", padx=16, pady=(2, 14))
        self.log_label = ctk.CTkLabel(self.s3.body, text="Every file", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w")
        self.log = textbox(self.s3.body, font=("Consolas", 12), height=150, wrap="none")
        self.log.configure(state="disabled")

        self.watch("recursive", callback=self.rescan)
        self.watch("where", "organize", callback=self._vars_changed)
        self.watch("subfolder", "custom", "format", "quality", "height", "name", "conflict", callback=self._settings_changed)
        self._vars_changed()
        self.refresh()
        self._poll_check()

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
        self.drop.set(f"{_plural(len(files), 'comic')} chosen from {self.folder}")
        self.say("")
        self._new_comics()

    def set_folder(self, folder):
        self.folder = Path(folder)
        self.picked = None
        self.drop.set(str(self.folder))
        self._recall()
        self._new_comics()

    def _new_comics(self):
        self.result = None
        self.reviewed = False
        self.dry = False
        self.rescan()
        if self.files:
            self.advance(self.s1)

    def go_review(self):
        """The Covers settings are done: fold them and open the review."""
        self.reviewed = True
        self.refresh()
        self.advance(self.s2)

    def rescan(self):
        if self.picked is not None:
            self.files = [p for p in self.picked if p.exists()]
        else:
            self.files = find_comics(self.folder, self.vars["recursive"].get()) if self.folder else []
        self._fill_comics()
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
        self.drop.set(None)
        self._log(None)
        self.say("")
        self._fill_comics()
        self._start_check()
        self.refresh()
        for seg in self.segments:
            seg.set_open(True)
        self.update_idletasks()
        self.reveal(self.s1)

    def again(self):
        """Run the same job again."""
        self.result = None
        self.dry = False
        self.refresh()

    def _fill_comics(self):
        rows = []
        for p in self.files:
            try:
                size = _size(p.stat().st_size)
            except OSError:
                size = "?"
            try:
                where = str(p.parent.relative_to(self.folder)) if self.folder else str(p.parent)
            except ValueError:
                where = str(p.parent)
            rows.append((p.name, series_name(p.stem), where, p.suffix.lower().lstrip("."), size))
        self.comics.set_rows(rows)

    # --- looking at the comics in the background ---
    def _start_check(self):
        self._gen += 1
        self.bad, self.sizes = {}, []
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
                elif msg[0] == "size":
                    self.sizes.append(msg[1])
                elif msg[0] == "progress":
                    self.checking = (msg[1], msg[2])
                elif msg[0] == "checked" and msg[1] == self._gen:
                    self.checking = None
                    self._last_refresh = 0  # the last answer arrived: draw it now
                changed = True
        except queue.Empty:
            pass
        if changed and (time.time() - self._last_refresh > 0.8):  # a long check must not redraw the table every tick
            self._last_refresh = time.time()
            self.refresh()
        elif changed:
            self._pending_refresh = True
        elif self._pending_refresh and time.time() - self._last_refresh > 0.8:
            self._pending_refresh = False
            self._last_refresh = time.time()
            self.refresh()
        try:
            self.after(150, self._poll_check)
        except Exception:  # noqa: BLE001 - the page is gone
            pass

    # --- the cards and the settings behind them ---
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
        self._settings_changed()

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
        self._settings_changed()

    def _settings_changed(self):
        if self.folder and not self._loading:
            self.memory[str(self.folder)] = {k: self.vars[k].get() for k in self.defaults if k != "recursive"}
            while len(self.memory) > 30:
                self.memory.pop(next(iter(self.memory)))
        self.refresh()

    def _recall(self):
        """Use the settings last used with this folder, if there are any."""
        saved = self.memory.get(str(self.folder))
        if not saved:
            return
        self._loading = True
        for k, val in saved.items():
            if k in self.vars and (k not in self.choices or val in self.choices[k]):
                try:
                    self.vars[k].set(val)
                except (ValueError, TypeError):
                    pass
        self._loading = False

    def state(self):
        out = super().state()
        out["_by_folder"] = dict(self.memory)
        return out

    def restore(self, saved):
        super().restore(saved)
        mem = (saved or {}).get("_by_folder")
        if isinstance(mem, dict):
            self.memory = {str(k): v for k, v in mem.items() if isinstance(v, dict)}

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
        return [(p, plan_dest(p, self.folder, o, ext)) for p in self.files]

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

    def _free_note(self, estimate):
        """A warning when the drive that will hold the covers looks too small, else ''."""
        if not estimate or not self.folder:
            return ""
        place = Path(self.out_dir) if self.out_dir else (self.folder / sanitize(self.vars["subfolder"].get() or "Covers"))
        if self.vars["where"].get() == WHERE_BESIDE:
            place = self.folder
        elif self.vars["where"].get() == WHERE_CUSTOM:
            place = Path(self.vars["custom"].get() or self.folder)
        while not place.exists() and place != place.parent:
            place = place.parent
        try:
            free = shutil.disk_usage(place).free
        except OSError:
            return ""
        return f"Only {_size(free)} free on that drive." if estimate > free else ""

    # --- keep the screen in step ---
    def review_rows(self):
        """The Review table: [(values, path, tag)] plus the counts that go with it."""
        o = self.options()
        plan = self._planned() or []
        seen, rows = set(), []
        c = {"new": 0, "exists": 0, "bad": 0, "taken": 0}
        for src, dest in plan:
            key = str(dest).lower()
            if src in self.bad:
                state, tag = "Unreadable", "bad"
                c["bad"] += 1
            elif key in seen:
                state, tag = "Name taken", "dim"
                c["taken"] += 1
            elif dest.exists():
                state, tag = "Exists", "dim"
                c["exists"] += 1
            else:
                state, tag = "New", ""
                c["new"] += 1
            seen.add(key)
            if self.dry and tag != "bad":
                state = WOULD[o["conflict"]] if state == "Exists" else "Would number" if state == "Name taken" else "Would save"
            elif self.dry:
                state = "Would fail"
            rows.append(((src.stem, self._short(dest, 60), state), src, (tag,) if tag else ()))
        return rows, c, plan

    def refresh(self):
        v = self.vars
        n = len(self.files)
        o = self.options()
        self.refresh_quality()
        # Comics: the summary
        series = len({series_name(p.stem) for p in self.files})
        if n:
            where = str(self.folder) if self.picked is None else f"{self.folder} (comics you picked)"
            self.s1.set_summary(f"{_plural(n, 'comic')} · {series} series · {where}")
        else:
            self.s1.set_summary("")
        # Covers: the cards, the rows, the summary
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
        recipe = next((t for k, t, _w in RECIPES if k == self.recipe.get()), "Your own layout")
        self.s2.set_summary(f"{recipe} · {o['format']} · {CONFLICT_WORD[o['conflict']]}")
        # Review: the counts, the problems, the table
        rows, c, plan = self.review_rows()
        will = c["new"] + c["taken"] + (0 if o["conflict"] == "Skip" else c["exists"])
        head = _plural(will, "cover")
        if o["conflict"] == "Skip" and c["exists"]:
            line = f"Will save {head}  ·  {c['exists']} already exist and stay as they are"
        else:
            line = f"Will save {head}" + (f"  ·  {c['exists']} already exist" if c["exists"] else "")
        if c["bad"]:
            line += f"  ·  {c['bad']} unreadable"
        if self.checking:
            line += f"  ·  checking comics {self.checking[0]} of {self.checking[1]}…"
        self.headline.configure(text=("Dry run, nothing is written.  " if self.dry else "") + line if n else
                                "Choose some comics first.")
        est = (sum(self.sizes) / len(self.sizes) * will) if self.sizes and will else 0
        sub = f"Saved in: {self._destination()}" + (f"  ·  about {_size(est)}" if est else "")
        warn = self._free_note(est)
        self.subline.configure(text=sub + (f"\n{warn}" if warn else "") if n else "",
                               text_color=DANGER if warn else MUTED)
        for w in self.problems.winfo_children():
            w.destroy()
        notes = [f"✗  {p.name}: {self.bad[p]}" for p in list(self.bad)[:3]]
        if len(self.bad) > 3:
            notes.append(f"…and {len(self.bad) - 3} more that cannot be read")
        if c["taken"]:
            notes.append(f"⚠  {_plural(c['taken'], 'comic')} would write a name another comic already uses; they get a number.")
        for text in notes:
            ctk.CTkLabel(self.problems, text=text, font=TYPE_BODY, text_color=DANGER, anchor="w", justify="left",
                         wraplength=900).pack(fill="x", pady=1)
        self.exist_label.configure(text=f"Existing covers: {c['exists']}" if c["exists"] else "")
        if c["exists"]:
            self.details_btn.pack(side="left", padx=(10, 0))
        else:
            self.details_btn.pack_forget()
        self.review.set_rows([r[0] for r in rows], keys=[r[1] for r in rows], tags=[r[2] for r in rows])
        self._counts = c
        self._sync_segments()

    def _covers_toggled(self):
        self.review.show_pictures(_thumb, self.covers_on.get())

    def show_existing(self):
        """A window listing the covers that already exist and what will happen to each."""
        o = self.options()
        top = ctk.CTkToplevel(self)
        top.title("Existing covers")
        top.geometry("720x460")
        top.transient(self.winfo_toplevel())
        ctk.CTkLabel(top, text=f"If a cover already exists: {CONFLICT_WORD[o['conflict']]}", font=(FONT, 14, "bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(14, 8))
        table = LazyTable(top, [("src", "Comic", 260, True), ("dest", "Cover file", 300, True), ("what", "What happens", 130, False)],
                          rows=14, filterable=True)
        table.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        what = {"Overwrite": "Replaced", "Skip": "Left alone", "Keep both": "Gets a number"}[o["conflict"]]
        table.set_rows([(src.stem, self._short(dest, 60), what) for src, dest in (self._planned() or [])
                        if dest.exists() and src not in self.bad])
        top.focus_force()

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
            s3.set_summary(self.result_text() if done else f"{_plural(c['new'] + c['exists'], 'cover')} to write")
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
            r = self.result
            word = "Stopped" if r["stopped"] else "Done"
            self.set_footer(f"{word}  ·  {self.result_text()}", "Open the covers folder", self.open_out,
                            enabled=bool(self.out_dir and self.out_dir.exists()),
                            secondary=[("Extract again", self.again), ("Do another folder", self.reset)] + retry)
        elif not n:
            self.set_footer("Choose some comics to begin.", "Choose comics first", self.start, enabled=False)
        else:
            dry = [("Back to normal", self.leave_dry)] if self.dry else [("Dry run", self.dry_run)]
            self.set_footer("Dry run: nothing is written." if self.dry else f"{_plural(n, 'comic')} ready.",
                            f"Extract {_plural(n, 'cover')}", self.start, secondary=dry)

    def result_text(self):
        r = self.result
        text = _plural(r["saved"], "cover") + " saved"
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
        self.s3.set_open(True)
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
        files = list(only) if only else list(self.files)
        if not self.folder or not files:
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
        self.s3.set_open(True)
        self.update_idletasks()
        self.reveal(self.s3)
        threading.Thread(target=_worker, args=(self.q, files, self.folder, o, self.stop), daemon=True).start()
        self.after(60, self._poll)  # (not at once: a fast run would be over before the page showed Stop)

    def retry(self):
        """Run again on just the comics that failed."""
        self.start(only=[p for p, _why in self.failed])

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
                    self.failed.append((msg[1], msg[2]))
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
        self.result_title.configure(text=("Stopped. " if stopped else "Done. ") + _plural(c["saved"], "cover") + " saved")
        parts = []
        if c["skipped"]:
            parts.append(f"{c['skipped']} skipped because the file already existed")
        if c["failed"]:
            parts.append(f"{c['failed']} could not be read")
        sub = ". ".join(parts) if parts else "Nothing went wrong."
        if c["failed"]:
            sub += "\n" + "\n".join(f"{p.name}: {why}" for p, why in self.failed[:3]) + ("\n…" if len(self.failed) > 3 else "")
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

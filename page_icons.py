"""Folder icons page: show a comic's cover as the Explorer icon of its folder, on the shared page shell in two columns with a
divider you can drag. Left: Folders, a table of the series folders with a picture of the icon each would get (it is the dry
run: nothing is written until the footer button is pressed). Right, scrolling on its own: Icon style (the three styles
drawn with your own first cover, the choice of first or last issue, and Advanced options) and Review (what will happen, then
the run)."""
import io
import os
import queue
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import aceo_core as ac
import folder_icons as fi
from comic_core import COMIC_EXT, Comic, common_root, picked_files
from flow_kit import Advanced, ChoiceCards, LazyTable, SegmentPage, labelled, section
from ui_kit import (BORDER, DANGER, EDGE, FONT, HEAD, MUTED, PANEL, TEXT, TYPE_BODY, TYPE_HINT, DropZone, FlowRow, Toggle, eta_text, flash_taskbar, menu, switch_style, textbox, tool_button)

WHICH = ["First issue", "Last issue"]
EXISTING = ["Replace", "Skip"]
IMAGE_TYPES = [("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.gif"), ("All", "*.*")]
ADVANCED_DEFAULTS = {"color": "Manila", "size": "Medium", "badge": False, "ico": True, "jpg": True, "existing": EXISTING[0]}
PREVIEW = 168


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def _cover(comic):
    """The first page of a comic, as image bytes."""
    c = Comic(comic)
    try:
        return c.read(c.pages[0])
    finally:
        c.close()


def _worker(q, jobs, o, stop):
    for k, (folder, comic, custom) in enumerate(jobs):
        if stop.is_set():
            q.put(("stopped",))
            return
        q.put(("start", k, len(jobs)))
        try:
            ico = o["ico"] and not (o["existing"] == "Skip" and fi.has_icon(folder))
            jpg = o["jpg"] and not (o["existing"] == "Skip" and (folder / fi.JPG).exists())
            if not (ico or jpg):
                q.put(("skipped", folder, "already has one"))
                continue
            data = custom if custom is not None else _cover(comic)
            fi.write_icon(folder, data, ico_on=ico, save_jpg=jpg, replace=o["existing"] == "Replace", style=o["style"],
                          color=o["color"], size=o["size"], badge=folder.name if o["badge"] else "")
            q.put(("ok", folder, comic.name if comic else "your image"))
        except Exception as e:  # noqa: BLE001 - one bad folder must not stop the rest
            q.put(("failed", folder, str(e) or type(e).__name__))
    q.put(("done",))


class IconsPage(SegmentPage):
    title = "Folder icons"
    subtitle = "Make each series folder show its cover in Explorer."
    defaults = {"recursive": True, "which": WHICH[0], "style": fi.STYLES[0], "color": "Manila", "size": "Medium", "badge": False,
                "ico": True, "jpg": True, "existing": EXISTING[0]}
    choices = {"which": WHICH, "style": fi.STYLES, "color": list(fi.FOLDER_COLORS), "size": list(fi.COVER_SIZES),
               "existing": EXISTING}
    split = True
    show_auto = False
    max_width = 1500

    def __init__(self, parent):
        super().__init__(parent)
        self.folder = None
        self.picked = None        # comics chosen one by one instead of a folder
        self.plan = []            # [(folder, comic)] for the series folders found
        self.images = {}          # folder -> image bytes chosen by hand (a folder with no comics may have one too)
        self.q = None
        self.stop = threading.Event()
        self.result = None
        self.failed = []
        self.made = set()
        self.example = 0
        self._cover_cache = {}
        self._t0 = 0
        self._pics_after = None
        self._photo = None
        v = self.vars

        # ---- Folders
        self.make_panes(right_width=500, lo=380)
        self.s1 = self.add_block("Folders", side="left", grow=True)
        self.drop = DropZone(self.s1.body, "Drop a folder of series folders here", self.browse, self.browse, self.browse_files,
                             compact=True)
        self.drop.pack(fill="x", padx=(0, 6))
        Toggle(self.s1.body, text="Include subfolders", variable=v["recursive"], **switch_style()).pack(anchor="w", pady=(2, 8))
        bar = FlowRow(self.s1.body)
        bar.pack(fill="x", pady=(0, 2))
        self.btn_image = tool_button(bar, "Use a different image…", self.custom_image, 170)
        self.btn_again = tool_button(bar, "Use the cover again", self.use_cover_again, 160)
        bar.add(self.btn_image)
        bar.add(self.btn_again)
        self.table = LazyTable(self.s1.body, [("folder", "Folder", 220, True), ("issue", "Cover from", 170, True),
                                              ("status", "Status", 130, False)], rows=8, grow=True,
                               empty="No folders yet. Drop a folder of series folders, or pick some comics.")
        self.table.pack(fill="both", expand=True)
        self.table.show_pictures(self._thumb, True, width=76, height=52)
        self.hint = ctk.CTkLabel(self.s1.body, text="The picture on each row is the icon the folder would get. Nothing is written until "
                                 "you press Make icons.", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=560)
        self.hint.pack(fill="x", pady=(4, 0))

        # ---- Icon style
        self.s2 = self.add_block("Icon style")
        body = self.s2.body
        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))
        self.preview = ctk.CTkLabel(top, text="", width=PREVIEW, height=PREVIEW, fg_color=("#FFFFFF", "#1E1E1E"))
        self.preview.pack(side="left")
        side = ctk.CTkFrame(top, fg_color="transparent")
        side.pack(side="left", fill="x", expand=True, padx=(14, 0))
        self.example_name = ctk.CTkLabel(side, text="", font=(FONT, 13, "bold"), text_color=TEXT, anchor="w", justify="left",
                                         wraplength=260)
        self.example_name.pack(fill="x")
        self.example_note = ctk.CTkLabel(side, text="", font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=260)
        self.example_note.pack(fill="x", pady=(2, 8))
        tool_button(side, "Try another folder", self.next_example, 160).pack(anchor="w")
        section(body, "How the icon looks").pack(fill="x", pady=(0, 8))
        self.style_cards = ChoiceCards(body, v["style"], [(s, s, "") for s in fi.STYLES], columns=3, picture=(96, 96))
        self.style_cards.pack(fill="x")
        section(body, "Cover from").pack(fill="x", pady=(8, 8))
        ChoiceCards(body, v["which"], [(WHICH[0], "First issue", "The first comic in each folder"),
                                       (WHICH[1], "Last issue", "The last comic in each folder")], columns=2).pack(fill="x")
        self.adv = Advanced(body)
        self.adv.pack(fill="x", pady=(10, 0))
        sw = switch_style()
        row = labelled(self.adv.body, "Folder colour")
        menu(row.cell, v["color"], list(fi.FOLDER_COLORS)).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        row = labelled(self.adv.body, "Cover size on the folder")
        menu(row.cell, v["size"], list(fi.COVER_SIZES)).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        Toggle(self.adv.body, text="Print the series name on the folder", variable=v["badge"], **sw).pack(anchor="w", pady=(0, 10))
        Toggle(self.adv.body, text="Folder icon (folder.ico + desktop.ini)", variable=v["ico"], **sw).pack(anchor="w", pady=(0, 10))
        Toggle(self.adv.body, text="Also save the cover as folder.jpg", variable=v["jpg"], **sw).pack(anchor="w", pady=(0, 10))
        row = labelled(self.adv.body, "If a folder already has one")
        menu(row.cell, v["existing"], EXISTING).pack(fill="x")
        row.pack(fill="x")
        self.adv.track(v, ADVANCED_DEFAULTS)

        # ---- Review
        self.s3 = self.add_block("Review")
        body = self.s3.body
        self.headline = ctk.CTkLabel(body, text="", font=(HEAD, 16), text_color=TEXT, anchor="w", justify="left", wraplength=440)
        self.headline.pack(fill="x")
        self.subline = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.subline.pack(fill="x", pady=(2, 6))
        self.progress = ctk.CTkProgressBar(body, height=14, corner_radius=0, border_width=3, border_color=BORDER, fg_color=BORDER,
                                           progress_color=("#FFD60A", "#FFD60A"))
        self.progress.set(0)
        self.status = ctk.CTkLabel(body, text="", font=(FONT, 12), text_color=MUTED, anchor="w", justify="left", wraplength=440)
        self.result_box = ctk.CTkFrame(body, fg_color=PANEL, border_color=BORDER, border_width=EDGE, corner_radius=0)
        self.result_title = ctk.CTkLabel(self.result_box, text="", font=(HEAD, 18), text_color=TEXT, anchor="w")
        self.result_title.pack(fill="x", padx=16, pady=(14, 0))
        self.result_sub = ctk.CTkLabel(self.result_box, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left",
                                       wraplength=400)
        self.result_sub.pack(fill="x", padx=16, pady=(2, 14))
        self.log_label = ctk.CTkLabel(body, text="Every folder", font=(FONT, 12, "bold"), text_color=MUTED, anchor="w")
        self.log = textbox(body, font=("Consolas", 12), height=140, wrap="none")
        self.log.configure(state="disabled")

        self.fit_right(self.example_name, self.example_note, self.headline, self.subline, self.status, self.result_sub)
        self.watch("recursive", "which", callback=self.rescan)
        self.watch("style", "color", "size", "badge", "ico", "jpg", "existing", callback=self._options_changed)
        self.refresh()
        self._pictures_soon()

    def say(self, msg, err=False):
        super().say(msg, err)
        if msg and not self.q:
            self.status.pack(fill="x", pady=(6, 0))
        elif not msg and not self.q:
            self.status.pack_forget()

    # --- choosing folders ---
    def browse(self):
        d = filedialog.askdirectory(title="Folder of series folders")
        if d:
            self.set_folder(d)

    def browse_files(self):
        files = filedialog.askopenfilenames(title="Choose comics", filetypes=[("Comic archives", "*.cbz *.cbr"), ("All", "*.*")])
        if files:
            self.set_files(files)

    def set_files(self, paths):
        """One icon for each folder the chosen comics are in (the first or last of those comics gives the cover)."""
        files = picked_files(paths, COMIC_EXT)
        if not files:
            self.say("None of those files are .cbz or .cbr comics.", err=True)
            return
        self.picked = files
        self.folder = common_root(files)
        self.drop.set(f"{_plural(len(files), 'comic')} chosen from {self.folder}")
        self.say("")
        self._new()

    def set_folder(self, folder):
        self.folder = Path(folder)
        self.picked = None
        self.drop.set(str(self.folder))
        self._new()

    def add_paths(self, paths):
        paths = [Path(p) for p in paths]
        if len(paths) == 1 and paths[0].is_dir():
            self.set_folder(paths[0])
        else:
            self.set_files(paths)

    def _new(self):
        self.result = None
        self.made = set()
        self.example = 0
        self.rescan()

    def rescan(self):
        if self.picked is not None:
            which = -1 if self.vars["which"].get() == WHICH[1] else 0
            by = {}
            for p in self.picked:
                if p.exists():
                    by.setdefault(p.parent, []).append(p)
            self.plan = [(f, sorted(c, key=lambda p: p.name.lower())[which]) for f, c in sorted(by.items(), key=lambda kv: str(kv[0]).lower())]
        elif self.folder:
            self.plan = fi.plan_folders(self.folder, self.vars["which"].get(), self.vars["recursive"].get())
        else:
            self.plan = []
        self.refresh()
        self._pictures_soon()

    def reset(self):
        """Start over with another folder."""
        if self.q:
            return
        self.folder = self.picked = None
        self.plan, self.images, self.made = [], {}, set()
        self.result = None
        self.drop.set(None)
        self._log(None)
        self.say("")
        self.refresh()

    def again(self):
        self.result = None
        self.made = set()
        self.refresh()

    # --- the rows ---
    def rows(self):
        """[(folder, comic or None)]: the series folders found, then the folders given an image by hand."""
        have = {f for f, _ in self.plan}
        return list(self.plan) + [(f, None) for f in self.images if f not in have]

    def _status(self, folder, o):
        if folder in self.made:
            return "Made"
        has = fi.has_icon(folder) if fi.supported() else False
        if o["ico"] and has:
            return "Has one: kept" if o["existing"] == "Skip" else "Has one: replaced"
        if not o["ico"] and o["jpg"] and (folder / fi.JPG).exists():
            return "Has one: kept" if o["existing"] == "Skip" else "Has one: replaced"
        return "Custom image" if folder in self.images else "New"

    def _sig(self, o):
        return (o["style"], o["color"], o["size"], bool(o["badge"]))

    def _row_values(self, o):
        out, keys = [], []
        sig = self._sig(o)
        for folder, comic in self.rows():
            try:
                shown = str(folder.relative_to(self.folder)) if self.folder and folder != self.folder else folder.name
            except ValueError:
                shown = str(folder)
            used = "Your image" if folder in self.images else (comic.name if comic else "")
            out.append((shown or folder.name, used, self._status(folder, o)))
            keys.append((str(folder), str(comic) if comic else "", folder in self.images, sig, folder.name))
        return out, keys

    # --- pictures ---
    def _thumb(self, key):
        """The finished icon of one folder, small (called off the screen's thread)."""
        folder, comic, custom, sig, name = key
        data = self.images.get(Path(folder)) if custom else None
        if data is None:
            data = self._cover_bytes(Path(comic))
        return fi.render_icon(data, sig[0], sig[1], sig[2], name if sig[3] else "", side=42)

    def _cover_bytes(self, comic):
        data = self._cover_cache.get(comic)
        if data is None:
            data = _cover(comic)
            if len(self._cover_cache) > 300:
                self._cover_cache.clear()
            self._cover_cache[comic] = data
        return data

    def next_example(self):
        n = len(self.rows())
        if n:
            self.example = (self.example + 1) % n
            self._pictures_soon()

    def _options_changed(self):
        self.refresh()
        self._pictures_soon()

    def _pictures_soon(self):
        if self._pics_after:
            self.after_cancel(self._pics_after)
        self._pics_after = self.after(80, self._pictures)

    def _example_bytes(self):
        rows = self.rows()
        if not rows:
            buf = io.BytesIO()
            ac.sample_cover().save(buf, "PNG")
            return buf.getvalue(), None
        folder, comic = rows[min(self.example, len(rows) - 1)]
        try:
            return (self.images[folder] if folder in self.images else self._cover_bytes(comic)), folder
        except Exception:  # noqa: BLE001 - an unreadable comic shows the made-up cover instead
            buf = io.BytesIO()
            ac.sample_cover().save(buf, "PNG")
            return buf.getvalue(), folder

    def _pictures(self):
        """The big preview and the pictures on the three style cards, drawn from the example folder's cover."""
        self._pics_after = None
        o = self.state()
        data, folder = self._example_bytes()
        name = folder.name if folder else "Series name"
        badge = name if o["badge"] else ""
        try:
            big = fi.render_icon(data, o["style"], o["color"], o["size"], badge, side=PREVIEW * 2)
        except Exception:  # noqa: BLE001 - a cover that is not a picture: the made-up one is shown instead
            buf = io.BytesIO()
            ac.sample_cover().save(buf, "PNG")
            data = buf.getvalue()
            big = fi.render_icon(data, o["style"], o["color"], o["size"], badge, side=PREVIEW * 2)
        self._photo = ctk.CTkImage(light_image=big, dark_image=big, size=(PREVIEW, PREVIEW))
        self.preview.configure(image=self._photo)
        self.example_name.configure(text=name if folder else "No folder yet: this is a made-up cover")
        n = len(self.rows())
        self.example_note.configure(text=f"Example {min(self.example, n - 1) + 1} of {n}" if n else "")
        for s in fi.STYLES:
            self.style_cards.set_picture(s, fi.render_icon(data, s, o["color"], o["size"], badge, side=192))

    # --- keep the screen in step ---
    def options(self):
        return self.state()

    def refresh(self):
        o = self.options()
        rows = self.rows()
        values, keys = self._row_values(o)
        tags = [("dim",) if v[2].startswith("Has one: kept") else () for v in values]
        chosen = self.table.selected()     # (a changed row rebuilds the table, which would forget the selection)
        self.table.set_rows(values, keys=keys, tags=tags)
        self.table.select(chosen)
        self.table.refresh_pictures(keys)
        n = len(rows)
        have = sum(1 for v in values if v[2].startswith("Has one"))
        self.s1.set_summary(f"{_plural(len(self.plan), 'series folder')} · {have} already have icons" if self.plan else
                            (f"{_plural(n, 'folder')} with your own image" if n else ""))
        self.s2.set_summary(f"{o['style']} · {o['which'].lower()}")
        kept = sum(1 for v in values if v[2] == "Has one: kept")
        will = n - kept - sum(1 for v in values if v[2] == "Made")
        if not fi.supported():
            head, sub, bad = "Folder icons only work on Windows.", "", True
        elif not n:
            head, sub, bad = "Choose some folders first.", "", False
        elif not (o["ico"] or o["jpg"]):
            head, sub, bad = "Turn on a folder icon or folder.jpg under Advanced options.", "", True
        else:
            head = f"Will make {_plural(will, 'icon')}"
            if have - kept:
                head += f"  ·  {have - kept} replace an icon"
            if kept:
                head += f"  ·  {kept} kept"
            parts = ([fi.ICO + " and " + fi.INI] if o["ico"] else []) + ([fi.JPG] if o["jpg"] else [])
            sub, bad = "Written in each folder: " + ", ".join(parts) + ". Explorer may take a moment to show them; Refresh Explorer helps.", False
        self.headline.configure(text=head, text_color=DANGER if bad else TEXT)
        self.subline.configure(text=sub)
        self.btn_image.configure(state="normal" if not self.q else "disabled")
        self.btn_again.configure(state="normal" if self.images and not self.q else "disabled")
        self._sync(n, o, will, bad)

    def _sync(self, n, o, will, bad):
        running, done = bool(self.q), self.result is not None
        self.s1.set_state("active" if not n else "done")
        self.s2.set_state("active" if n else "locked")
        self.s3.set_state("active" if running else "done" if done else "idle" if n else "locked")
        self.s3.set_summary(self.result_text() if done else f"{_plural(max(will, 0), 'icon')} to make" if n else "")
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
        retry = [(f"Retry {len(self.failed)} failed", self.retry)] if done and self.failed else []
        extra = [("Remove icons", self.remove_icons), ("Refresh Explorer", self.refresh_explorer)]
        if running:
            self.set_footer(self.status.cget("text") or "Working…", "Stop", self.start)
        elif done:
            word = "Stopped" if self.result["stopped"] else "Done"
            self.set_footer(f"{word}  ·  {self.result_text()}", "Refresh Explorer", self.refresh_explorer,
                            secondary=[("Make them again", self.again), ("Do another folder", self.reset), ("Remove icons", self.remove_icons)] + retry)
        elif not n:
            self.set_footer("Choose some folders to begin.", "Make icons", self.start, enabled=False, secondary=extra)
        else:
            self.set_footer(f"{_plural(n, 'folder')} ready.", f"Make {_plural(max(will, 0), 'icon')}", self.start,
                            enabled=will > 0 and not bad, secondary=extra)

    def result_text(self):
        r = self.result
        text = f"{_plural(r['ok'], 'icon')} made"
        if r["skipped"]:
            text += f", {r['skipped']} kept"
        if r["failed"]:
            text += f", {r['failed']} failed"
        return text

    # --- a picture of your own ---
    def custom_image(self):
        """An image of your own for the selected rows (or, with nothing selected, for any folder you choose: one with no
        comics of its own, such as DC or Marvel)."""
        rows = self.rows()
        sel = [rows[i][0] for i in self.table.selected() if i < len(rows)]
        if not sel:
            start = str(self.folder) if self.folder else None
            folder = filedialog.askdirectory(title="Folder to give an image to", initialdir=start)
            if not folder:
                return
            sel = [Path(folder)]
        image = filedialog.askopenfilename(title="Image to use as the icon", filetypes=IMAGE_TYPES)
        if not image:
            return
        try:
            data = Path(image).read_bytes()
            fi.render_icon(data, fi.STYLE_FLAT, side=16)
        except (OSError, ValueError) as e:
            self.say(f"Couldn't use that image: {e}", err=True)
            return
        for f in sel:
            self.images[f] = data
        self.say(f"{_plural(len(sel), 'folder')} will use {Path(image).name}.")
        self.refresh()
        self._pictures_soon()

    def use_cover_again(self):
        rows = self.rows()
        for i in self.table.selected():
            if i < len(rows):
                self.images.pop(rows[i][0], None)
        if not self.table.selected():
            self.images.clear()
        self.refresh()
        self._pictures_soon()

    # --- the run ---
    def stop_action(self):
        if self.q:
            self.stop.set()

    def _jobs(self, only=None):
        o = self.options()
        jobs = []
        for folder, comic in self.rows():
            if only is not None and folder not in only:
                continue
            if self._status(folder, o) == "Has one: kept":
                continue
            jobs.append((folder, comic, self.images.get(folder)))
        return jobs

    def start(self, only=None):
        if self.q:  # running: this button is "Stop"
            self.stop.set()
            self.bar_btn.configure(state="disabled", text="Stopping…")
            return
        o = self.options()
        if not fi.supported():
            self.say("Folder icons only work on Windows.", err=True)
            return
        if not (o["ico"] or o["jpg"]):
            self.say("Turn on a folder icon or folder.jpg under Advanced options.", err=True)
            return
        jobs = self._jobs(only)
        if not jobs:
            self.say("Nothing to make: every folder already has one.")
            return
        self.counts = {"ok": 0, "skipped": 0, "failed": 0}
        self.failed = []
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
        threading.Thread(target=_worker, args=(self.q, jobs, o, self.stop), daemon=True).start()
        self.after(60, self._poll)

    def retry(self):
        self.start(only={f for f, _ in self.failed})

    def _poll(self):
        try:
            for _ in range(50):
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "start":
                    self.progress.set(msg[1] / msg[2])
                    self.say(eta_text(msg[1], msg[2], self._t0) + f"  ·  {self.counts['ok']} made")
                    self.bar_text.configure(text=self.status.cget("text"))
                elif kind == "ok":
                    self.counts["ok"] += 1
                    self.made.add(msg[1])
                    self._log(f"✓  {msg[1].name}  ←  {msg[2]}")
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
        self.result_title.configure(text=("Stopped. " if stopped else "Done. ") + f"{_plural(c['ok'], 'icon')} made")
        parts = []
        if c["skipped"]:
            parts.append(f"{c['skipped']} kept as they were")
        if c["failed"]:
            parts.append(f"{c['failed']} could not be made")
        sub = ". ".join(parts) if parts else "Nothing went wrong."
        if c["failed"]:
            sub += "\n" + "\n".join(f"{f.name}: {why}" for f, why in self.failed[:3])
        self.result_sub.configure(text=sub + "\nExplorer may take a moment to show the new icons.")
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

    # --- taking icons away, and a nudge to Explorer ---
    def remove_icons(self):
        """Give the folders in the list their ordinary look again (folder.jpg stays)."""
        if self.q:
            return
        folders = [f for f, _ in self.rows() if fi.supported() and fi.has_icon(f)]
        if not folders:
            self.say("None of these folders has an icon from this tool.")
            return
        if not messagebox.askyesno("Remove icons", f"Take the icon away from {_plural(len(folders), 'folder')}?\n\n"
                                   "folder.ico and the icon line of desktop.ini are removed; folder.jpg is kept.", icon="warning"):
            return
        gone, bad = 0, []
        for f in folders:
            try:
                fi.remove_icon(f)
                gone += 1
                self.made.discard(f)
            except (OSError, RuntimeError) as e:
                bad.append(f"{f.name}: {e}")
        self.say(f"Removed {_plural(gone, 'icon')}" + (f"; {len(bad)} failed ({bad[0]})" if bad else "") + ".", err=bool(bad))
        self.refresh()

    def refresh_explorer(self):
        if fi.refresh_explorer():
            self.say("Asked Windows to redraw its icons. If a folder still shows the old picture, give it a moment.")
        else:
            self.say("Couldn't ask Windows to redraw its icons.", err=True)

    def open_folder(self):
        if self.folder and self.folder.exists():
            os.startfile(self.folder)  # Windows

"""Single issue page: save the cover of one comic, or pick pages from it, on the shared page shell in two columns with a
divider you can drag. Left: Comic (the drop box) and Pages (the first 3 and last 2 pages, with a tile that browses all of
them). Right, scrolling on its own: Save (format, quality, size, and the file that will be written; the destination, file
name and conflict handling under Advanced options). The footer says Save cover until pages are picked, then Extract N pages."""
import io
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
import os

import customtkinter as ctk
from PIL import Image

import picker_core as pc
from comic_core import (CONFLICTS, FORMATS, HEIGHTS, NAMES, ORG_FLAT, WHERE_BESIDE, WHERE_CUSTOM, Comic, export_cover,
                        plan_dest, sanitize, unique)
from flow_kit import Advanced, SegmentPage, labelled, path_row
from picker_window import PickerWindow
from ui_kit import (ACCENT_TEXT, BORDER, EDGE, FONT, HOVER, MUTED, RAISED, TEXT, TYPE_BODY, TYPE_HINT, DropZone,
                    ensure_hover, menu)

FIRST, LAST = 3, 2     # pages shown from each end
THUMB_W, THUMB_H = 120, 165
CELL = THUMB_W + 14
EXT = {"JPG": ".jpg", "PNG": ".png", "WebP": ".webp"}
ADVANCED_DEFAULTS = {"where": WHERE_BESIDE, "name": NAMES[1], "conflict": "Keep both"}


def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


class SinglePage(SegmentPage):
    title = "Single issue"
    subtitle = "Save the cover of one comic, or pick pages from it."
    defaults = {"format": "Original", "quality": 90, "height": "Original size",
                "where": WHERE_BESIDE, "custom": "", "name": NAMES[1], "conflict": "Keep both"}
    choices = {"format": FORMATS, "height": list(HEIGHTS), "where": [WHERE_BESIDE, WHERE_CUSTOM],
               "name": NAMES, "conflict": CONFLICTS}
    split = True
    show_auto = False
    max_width = 1500

    def __init__(self, parent):
        super().__init__(parent)
        self.comic = None
        self.picked = []          # picked page indexes, in the order they will be numbered
        self.saved_dir = None     # where the last save went, for Open folder
        self._thumbs = []
        self._cells = []          # the widgets in the Pages strip, in order
        self._caps = {}           # page index -> its caption label
        self._picker = None
        v = self.vars

        # ---- Comic
        self.make_panes(right_width=480, lo=360)
        self.s1 = self.add_block("Comic", side="left")
        self.drop = DropZone(self.s1.body, "Drop a .cbz or .cbr here, or choose one below", self.browse,
                             self.browse_folder, self.browse, folder_text="Open folder in Bulk…",
                             files_text="Choose comic…", files_first=True)
        self.drop.pack(fill="x", padx=(0, 6))

        # ---- Pages
        self.s2 = self.add_block("Pages", side="left")
        self.empty = ctk.CTkLabel(self.s2.body, text="Choose a comic to see its cover, first pages and last pages here.",
                                  font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left", wraplength=360)
        self.empty.pack(fill="x")
        self.strip = ctk.CTkFrame(self.s2.body, fg_color="transparent")
        self.strip.bind("<Configure>", lambda e: self._layout_strip(e.width))
        self.hint = ctk.CTkLabel(self.s2.body, text="Click a page to view it and pick it. Browse all pages to pick any others.",
                                 font=TYPE_HINT, text_color=MUTED, anchor="w", justify="left", wraplength=360)

        # ---- Save
        self.s3 = self.add_block("Save")
        body = self.s3.body
        self.refresh_quality = self.image_options(body)
        self.target = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=TEXT, anchor="w", justify="left", wraplength=400)
        self.target.pack(fill="x", pady=(0, 6))
        self.status = ctk.CTkLabel(body, text="", font=TYPE_BODY, text_color=MUTED, anchor="w", justify="left", wraplength=400)
        self.status.pack(fill="x", pady=(0, 8))
        self.adv = Advanced(body)
        self.adv.pack(fill="x", pady=(0, 4))
        row = labelled(self.adv.body, "Save to")
        menu(row.cell, v["where"], [WHERE_BESIDE, WHERE_CUSTOM]).pack(fill="x")
        row.pack(fill="x", pady=(0, 10))
        self.custom_row = labelled(self.adv.body, "Folder")
        path_row(self.custom_row.cell, v["custom"], "Save covers to").pack(fill="x")
        self.name_row = labelled(self.adv.body, "File name")
        menu(self.name_row.cell, v["name"], NAMES).pack(fill="x")
        self.name_row.pack(fill="x", pady=(0, 10))
        row = labelled(self.adv.body, "If the file exists")
        menu(row.cell, v["conflict"], CONFLICTS).pack(fill="x")
        row.pack(fill="x", pady=(0, 4))
        self.adv.track(v, ADVANCED_DEFAULTS)

        self.fit_right(self.target, self.status)
        self.watch("format", "quality", "height", "where", "custom", "name", "conflict", callback=self._sync)
        self._sync()

    # --- choosing a comic ---
    def browse(self):
        p = filedialog.askopenfilename(filetypes=[("Comic archives", "*.cbz *.cbr"), ("All", "*.*")])
        if p:
            self.load(p)

    def browse_folder(self):
        """One issue at a time lives here, so a folder is handed to Bulk folder (as when it is dropped)."""
        d = filedialog.askdirectory(title="Folder of comics (opens in Bulk folder)")
        if d:
            app = self.winfo_toplevel()
            if hasattr(app, "pages") and "bulk" in app.pages:
                app.show("bulk")
                app.pages["bulk"].set_folder(d)

    def load(self, path):
        self._close_picker()
        if self.comic:
            self.comic.close()
            self.comic = None
        self.picked = []
        self.saved_dir = None
        self._clear_strip()
        self.say("Reading…")
        self.update_idletasks()
        try:
            self.comic = Comic(path)
        except (RuntimeError, OSError) as e:
            self.say(str(e), err=True)
            self._sync()
            return
        except Exception as e:  # noqa: BLE001 - corrupt archives raise all sorts of things
            self.say(f"Can't read this file: {e}", err=True)
            self._sync()
            return
        self.drop.set(self.comic.path.name)
        self._build_strip()
        self.say("")
        self._sync()
        self.advance(self.s1)

    # --- the strip of pages ---
    def _clear_strip(self):
        for w in self._cells:
            w.destroy()
        self._cells, self._caps = [], {}
        self._thumbs.clear()
        self.strip.pack_forget()
        self.hint.pack_forget()
        self.empty.pack(fill="x")

    def _build_strip(self):
        n = len(self.comic.pages)
        first = list(range(min(n, FIRST)))
        last = list(range(max(FIRST, n - LAST), n))
        for i in first + last:
            cell = self._page_cell(i)
            if cell is not None:
                self._cells.append(cell)
        self._cells.append(self._tile(n))
        self.empty.pack_forget()
        self.strip.pack(fill="x", pady=(0, 8))
        self.hint.pack(fill="x")
        self._layout_strip(max(self.strip.winfo_width(), CELL))
        self._mark()

    def _page_cell(self, i):
        try:
            img = Image.open(io.BytesIO(self.comic.read(self.comic.pages[i])))
            img.thumbnail((THUMB_W * 2, THUMB_H * 2))
            img = img.convert("RGB")
        except (OSError, ValueError):
            return None
        s = min(THUMB_W / img.width, THUMB_H / img.height)
        thumb = ctk.CTkImage(img, size=(max(1, round(img.width * s)), max(1, round(img.height * s))))
        self._thumbs.append(thumb)  # keep reference
        cell = ctk.CTkFrame(self.strip, fg_color="transparent")
        pic = ctk.CTkLabel(cell, image=thumb, text="", cursor="hand2")
        pic.pack()
        cap = ctk.CTkLabel(cell, text="", font=TYPE_HINT, text_color=MUTED, cursor="hand2")
        cap.pack(pady=(4, 0))
        self._caps[i] = cap
        for w in (pic, cap):
            w.bind("<Button-1>", lambda _, i=i: self.open_page(i))
        return cell

    def _tile(self, n):
        """The big tile at the end of the strip: opens the window with every page."""
        card = ctk.CTkFrame(self.strip, fg_color=RAISED, border_color=BORDER, border_width=EDGE, corner_radius=0,
                            width=THUMB_W, height=THUMB_H, cursor="hand2")
        card.pack_propagate(False)
        lab = ctk.CTkLabel(card, text=f"Browse all\n{n} pages…", font=(FONT, 13, "bold"), text_color=TEXT, justify="center")
        lab.pack(expand=True)
        for w in (card, lab):
            w.bind("<Button-1>", lambda _: self.pick_pages())
        card.__dict__["_hover_hooks"] = (lambda: card.configure(fg_color=HOVER), lambda: card.configure(fg_color=RAISED))
        tk.Frame.configure(card, takefocus=1)
        tk.Frame.bind(card, "<Return>", lambda _: self.pick_pages(), "+")
        tk.Frame.bind(card, "<space>", lambda _: self.pick_pages(), "+")
        ensure_hover(card)
        return card

    def _layout_strip(self, width):
        """Put the cells in rows as wide as the column is."""
        scale = self._get_widget_scaling()
        cols = max(1, int(width / scale) // CELL)
        for k, cell in enumerate(self._cells):
            cell.grid(row=k // cols, column=k % cols, padx=(0, 14), pady=(0, 10), sticky="n")

    def _mark(self):
        """Caption each page of the strip with its name, and a tick and its number when it is picked."""
        for i, cap in self._caps.items():
            name = "Cover" if i == 0 else f"Page {i + 1}"
            if i in self.picked:
                cap.configure(text=f"✓ {name}  #{self.picked.index(i) + 1}", text_color=ACCENT_TEXT)
            else:
                cap.configure(text=name, text_color=MUTED)

    # --- the page picker (the picks are shared with it) ---
    def _open_picker(self):
        if self._picker is not None and self._picker.winfo_exists():
            self._picker.lift()
        else:
            self._picker = PickerWindow(self, self.comic, order=self.picked, on_change=self.set_picked)
        return self._picker

    def pick_pages(self):
        """Open the thumbnail grid to pick any pages (the covers inside a TPB, say)."""
        if self.comic is not None:
            self._open_picker()

    def open_page(self, i):
        """A page of the strip: show it full size, where it can be picked."""
        if self.comic is not None:
            self._open_picker().open_full(i)

    def _close_picker(self):
        if self._picker is not None and self._picker.winfo_exists():
            self._picker.close()
        self._picker = None

    def set_picked(self, order):
        """The picks changed (in the picker window): follow them."""
        self.picked = list(order)
        self._mark()
        self._sync()

    def clear_picks(self):
        self.picked = []
        if self._picker is not None and self._picker.winfo_exists():
            self._picker.set_order([])
        self._mark()
        self._sync()

    # --- keep the screen in step ---
    def _dest_folder(self):
        o = self.state()
        if o["where"] == WHERE_CUSTOM and o["custom"].strip():
            return Path(o["custom"])
        return self.comic.path.parent if self.comic else None

    def _cover_path(self):
        """The file Save cover would write, and a note about it, or (None, why not)."""
        o = self._opts()
        if o["where"] == WHERE_CUSTOM and not o["custom"].strip():
            return None, "Choose a folder under Advanced options."
        page = self.comic.pages[0]
        ext = EXT.get(o["format"]) or Path(page).suffix.lower()
        dest = plan_dest(self.comic.path, self.comic.path.parent, o, ext)
        note = ""
        if dest.exists():
            note = {"Skip": "  (it exists, so it is skipped)", "Overwrite": "  (it exists and is replaced)",
                    "Keep both": "  (it exists, so a number is added)"}[o["conflict"]]
        return dest, note

    def _sync(self):
        self.refresh_quality()
        v = self.vars
        if v["where"].get() == WHERE_CUSTOM:
            self.custom_row.pack(fill="x", pady=(0, 10), before=self.name_row)
        else:
            self.custom_row.pack_forget()
        c = self.comic
        retry = [("Open folder", self.open_saved)] if self.saved_dir else []
        if c is None:
            self.s1.set_state("active")
            self.s2.set_state("locked")
            self.s3.set_state("locked")
            for s in (self.s1, self.s2, self.s3):
                s.set_summary("")
            self.target.configure(text="")
            self.set_footer("Choose a comic to begin.", "Save cover", self.save_cover, enabled=False)
            return
        n = len(c.pages)
        k = len(self.picked)
        self.s1.set_state("done")
        self.s2.set_state("active")
        self.s3.set_state("active")
        self.s1.set_summary(f"{c.path.stem} · {_plural(n, 'page')} · {c.path.suffix.lstrip('.').upper()}")
        self.s2.set_summary(f"{_plural(k, 'page')} picked" if k else "Cover")
        where = "beside the comic" if v["where"].get() == WHERE_BESIDE else "in the folder you chose"
        self.s3.set_summary(f"{v['format'].get()} · {where}")
        zip_btn = ("Save all pages as ZIP", self.convert)
        if k:
            self.target.configure(
                text=f"Will save {_plural(k, 'page')} as JPG files named “{sanitize(c.path.stem)} 1.jpg”, 2, 3…, in a folder you choose.")
            self.set_footer(f"{_plural(k, 'page')} picked.", f"Extract {_plural(k, 'page')}", self.extract,
                            secondary=[("Clear picks", self.clear_picks), zip_btn] + retry)
        else:
            dest, note = self._cover_path()
            self.target.configure(text=(f"Will save: {dest}{note}" if dest else note),
                                  text_color=TEXT if dest else MUTED)
            self.set_footer(f"{c.path.name}  ·  {_plural(n, 'page')}", "Save cover", self.save_cover,
                            secondary=[zip_btn] + retry)

    def _opts(self):
        return {**self.state(), "subfolder": "", "organize": ORG_FLAT}

    # --- saving ---
    def save_cover(self):
        if self.comic is None:
            return
        o = self._opts()
        if o["where"] == WHERE_CUSTOM and not o["custom"].strip():
            self.say("Choose a folder to save to.", err=True)
            self.adv.set_open(True)
            return
        try:
            status, dest = export_cover(self.comic, self.comic.path.parent, o, set())
        except Exception as e:  # noqa: BLE001
            self.say(str(e), err=True)
            return
        if status == "skipped":
            self.say(f"Skipped, {dest.name} already exists.")
        else:
            self.saved_dir = dest.parent
            self.say(f"Saved {dest}")
            self.show_next([("Do the whole folder", self.link("bulk", folder=self.comic.path.parent)),
                            ("Put this cover on a sheet", self.link("aceo", paths=[self.comic.path]))])
        self._sync()

    def extract(self):
        if self.comic is None or not self.picked:
            return
        folder = filedialog.askdirectory(title="Save the picked pages to", initialdir=str(self._dest_folder()))
        if not folder:
            return
        try:
            saved = pc.extract_pages(self.comic, self.picked, folder)
        except Exception as e:  # noqa: BLE001
            self.say(str(e), err=True)
            return
        self.saved_dir = Path(folder)
        self.say(f"Saved {_plural(len(saved), 'JPG')} to {folder}")
        self._sync()

    def convert(self):
        """Every page in a ZIP: a shortcut for the pages, not a conversion of the comic."""
        if self.comic is None:
            return
        folder = self._dest_folder()
        out = unique(folder / f"{sanitize(self.comic.path.stem)}.zip")
        try:
            self.say("Saving…")
            self.update_idletasks()
            out.parent.mkdir(parents=True, exist_ok=True)
            self.comic.to_zip(out)
        except Exception as e:  # noqa: BLE001
            self.say(str(e), err=True)
            return
        self.saved_dir = out.parent
        self.say(f"Saved {out}")
        self._sync()

    def open_saved(self):
        if self.saved_dir and Path(self.saved_dir).exists():
            os.startfile(self.saved_dir)  # Windows

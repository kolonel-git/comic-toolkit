"""Single issue page: preview first/last pages, save the cover, convert to ZIP."""
import io
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from comic_core import (CONFLICTS, FORMATS, HEIGHTS, NAMES, ORG_FLAT, WHERE_BESIDE, WHERE_CUSTOM,
                        Comic, export_cover, sanitize, unique)
from ui_kit import BG, FONT, MUTED, DropZone, Form, Page, button, menu, title_block

EDGE = 3  # pages previewed from each end
THUMB_W, THUMB_H = 120, 165


class SinglePage(Page):
    defaults = {"format": "Original", "quality": 90, "height": "Original size",
                "where": WHERE_BESIDE, "custom": "", "name": NAMES[1], "conflict": "Keep both"}
    choices = {"format": FORMATS, "height": list(HEIGHTS), "where": [WHERE_BESIDE, WHERE_CUSTOM],
               "name": NAMES, "conflict": CONFLICTS}

    def __init__(self, parent):
        super().__init__(parent)
        self.comic = None
        self._thumbs = []

        title_block(self.main, "Single issue", "Preview an issue, save its cover, or convert it to ZIP.")
        self.drop = DropZone(self.main, "Drop a .cbz or .cbr here, or click to browse", self.browse)
        self.drop.pack(fill="x")
        self.meta = ctk.CTkLabel(self.main, text="", font=(FONT, 13), text_color=MUTED, anchor="w")
        self.meta.pack(fill="x", pady=(16, 4))
        self.preview = ctk.CTkFrame(self.main, fg_color=BG)
        self.preview.pack(fill="both", expand=True)

        v = self.vars
        self.add_image_rows()
        self.where_menu = menu(self.form.add("Save to"), v["where"], [WHERE_BESIDE, WHERE_CUSTOM])
        self.where_menu.pack(fill="x")
        self.custom_row = self.form.add("Folder")
        self.path_row(self.custom_row, v["custom"], "Save covers to")
        menu(self.form.add("File name"), v["name"], NAMES).pack(fill="x")
        menu(self.form.add("If the file exists"), v["conflict"], CONFLICTS).pack(fill="x")

        self.btn_cover = button(self.footer, "Save cover", self.save_cover, primary=True)
        self.btn_cover.pack(pady=(0, 8))
        self.btn_zip = button(self.footer, "Convert to ZIP", self.convert)
        self.btn_zip.pack()
        self._enable(False)
        self.watch("format", "where", callback=self._refresh)
        self._refresh()

    def _refresh(self):
        self.refresh_quality()
        Form.show(self.custom_row, self.vars["where"].get() == WHERE_CUSTOM)

    def _enable(self, on):
        for b in (self.btn_cover, self.btn_zip):
            b.configure(state="normal" if on else "disabled")

    def browse(self):
        p = filedialog.askopenfilename(filetypes=[("Comic archives", "*.cbz *.cbr"), ("All", "*.*")])
        if p:
            self.load(p)

    def load(self, path):
        if self.comic:
            self.comic.close()
            self.comic = None
        for w in self.preview.winfo_children():
            w.destroy()
        self._thumbs.clear()
        self._enable(False)
        self.say("Reading…")
        self.update_idletasks()
        try:
            self.comic = Comic(path)
        except (RuntimeError, OSError) as e:
            self.meta.configure(text="")
            self.say(str(e), err=True)
            return
        except Exception as e:  # noqa: BLE001 - corrupt archives raise all sorts of things
            self.meta.configure(text="")
            self.say(f"Can't read this file: {e}", err=True)
            return
        n = len(self.comic.pages)
        self.drop.set(self.comic.path.name)
        self.meta.configure(text=f"{n} page{'s' if n != 1 else ''}")
        first = list(range(min(n, EDGE)))
        last = list(range(max(EDGE, n - EDGE), n))
        self._row("Cover and first pages" if last else "Pages", first)
        if last:
            self._row("Last pages", last)
        self._enable(True)
        self.say("")

    def _row(self, title, idxs):
        ctk.CTkLabel(self.preview, text=title, font=(FONT, 12), text_color=MUTED,
                     anchor="w").pack(fill="x", pady=(10, 4))
        row = ctk.CTkFrame(self.preview, fg_color=BG)
        row.pack(fill="x")
        for i in idxs:
            try:
                img = Image.open(io.BytesIO(self.comic.read(self.comic.pages[i])))
                img.thumbnail((THUMB_W * 2, THUMB_H * 2))
                img = img.convert("RGB")
            except (OSError, ValueError):
                continue
            s = min(THUMB_W / img.width, THUMB_H / img.height)
            thumb = ctk.CTkImage(img, size=(max(1, round(img.width * s)), max(1, round(img.height * s))))
            self._thumbs.append(thumb)  # keep reference
            cell = ctk.CTkFrame(row, fg_color=BG)
            cell.pack(side="left", padx=(0, 14))
            ctk.CTkLabel(cell, image=thumb, text="").pack()
            ctk.CTkLabel(cell, text="Cover" if i == 0 else f"Page {i + 1}", font=(FONT, 12),
                         text_color=MUTED).pack(pady=(4, 0))

    def _opts(self):
        return {**self.state(), "subfolder": "", "organize": ORG_FLAT}

    def save_cover(self):
        o = self._opts()
        if o["where"] == WHERE_CUSTOM and not o["custom"].strip():
            self.say("Choose a folder to save to.", err=True)
            return
        try:
            status, dest = export_cover(self.comic, self.comic.path.parent, o, set())
        except Exception as e:  # noqa: BLE001
            self.say(str(e), err=True)
            return
        self.say(f"Skipped, {dest.name} already exists." if status == "skipped" else f"Saved {dest}")

    def convert(self):
        o = self.state()
        folder = Path(o["custom"]) if o["where"] == WHERE_CUSTOM and o["custom"].strip() \
            else self.comic.path.parent
        out = unique(folder / f"{sanitize(self.comic.path.stem)}.zip")
        try:
            self.say("Converting…")
            self.update_idletasks()
            out.parent.mkdir(parents=True, exist_ok=True)
            self.comic.to_zip(out)
            self.say(f"Saved {out}")
        except Exception as e:  # noqa: BLE001
            self.say(str(e), err=True)

"""Folder icons page: use a comic's cover as the Explorer icon of its folder."""
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from batch_page import BatchPage
from comic_core import Comic
from folder_icons import has_icon, plan_folders, supported, write_icon
from ui_kit import button, menu, switch_style

WHICH = ["First issue", "Last issue"]
EXISTING = ["Replace", "Skip"]
IMAGE_TYPES = [("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.gif"), ("All", "*.*")]


class IconsPage(BatchPage):
    title = "Folder icons"
    subtitle = "Show each series' cover as its folder icon in Explorer."
    noun = "folder"
    run_label = "Set folder icons"
    defaults = {"which": WHICH[0], "ico": True, "jpg": True, "existing": EXISTING[0]}
    choices = {"which": WHICH, "existing": EXISTING}

    def __init__(self, parent):
        super().__init__(parent)
        v = self.vars
        sw = switch_style()
        self.form.heading("Cover")
        menu(self.form.add("Cover from"), v["which"], WHICH).pack(fill="x")
        self.form.heading("Output")
        box = self.form.add("Write")
        ctk.CTkSwitch(box, text="Folder icon (folder.ico + desktop.ini)", variable=v["ico"], **sw).pack(anchor="w")
        ctk.CTkSwitch(box, text="Cover image (folder.jpg)", variable=v["jpg"], **sw).pack(anchor="w", pady=(8, 0))
        menu(self.form.add("If a folder already has one"), v["existing"], EXISTING).pack(fill="x")
        self.btn_custom = button(self.footer, "Custom image for a folder…", self.custom)
        self.btn_custom.pack(pady=(8, 0), before=self.btn_open)
        self.watch("which", callback=self.rescan)

    def found_text(self, n):
        return f"{n} folder{'s' if n != 1 else ''} with comics found"

    def scan(self, folder, o):
        return plan_folders(folder, o["which"])

    def pick_items(self, files, o):
        """One icon per folder: the first (or last) of the chosen comics in it supplies the cover."""
        by_folder = {}
        for p in files:
            by_folder.setdefault(p.parent, []).append(p)
        pick = -1 if o["which"] == WHICH[1] else 0
        return [(folder, comics[pick]) for folder, comics in sorted(by_folder.items(), key=lambda kv: str(kv[0]).lower())]

    def label(self, item):
        return self.rel(item[0])

    def validate(self, o):
        if not supported():
            return "Folder icons only work on Windows."
        if not (o["ico"] or o["jpg"]):
            return "Turn on at least one of: folder icon, folder.jpg."
        return None

    def work(self, item, o, dry):
        folder, comic = item
        ico = o["ico"] and not (o["existing"] == "Skip" and has_icon(folder))
        jpg = o["jpg"] and not (o["existing"] == "Skip" and (folder / "folder.jpg").exists())
        if not (ico or jpg):
            return "skip", f"{self.rel(folder)}  already has one"
        text = f"{self.rel(folder)}  ←  {comic.name}"
        if not dry:
            c = Comic(comic)
            try:
                data = c.read(c.pages[0])
            finally:
                c.close()
            write_icon(folder, data, ico_on=ico, save_jpg=jpg, replace=o["existing"] == "Replace")
        return "ok", text

    def custom(self):
        """Pick any folder and any image: for folders with no comics of their own (DC, Marvel…)."""
        o = self.state()
        err = self.validate(o)
        if err:
            self.say(err, err=True)
            return
        start = str(self.folder) if self.folder else None
        folder = filedialog.askdirectory(title="Folder to give an icon", initialdir=start)
        if not folder:
            return
        image = filedialog.askopenfilename(title="Image to use as the icon", filetypes=IMAGE_TYPES)
        if not image:
            return
        try:
            write_icon(Path(folder), Path(image).read_bytes(), ico_on=o["ico"], save_jpg=o["jpg"],
                       replace=o["existing"] == "Replace")
        except (OSError, RuntimeError, ValueError) as e:
            self.say(f"Couldn't set icon: {e}", err=True)
            return
        self.say(f"Icon set for {Path(folder).name}")

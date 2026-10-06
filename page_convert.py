"""CBR to CBZ page: repack RAR comics as ZIP, verified, in bulk."""
import customtkinter as ctk

from archive_tools import DELETE, KEEP, MOVE, convert_to_cbz, dispose_original
from batch_page import BatchPage
from comic_core import in_archive, natural_key, unique
from ui_kit import menu, switch_style

EXISTS = ["Skip", "Keep both", "Overwrite"]


class ConvertPage(BatchPage):
    title = "CBR to CBZ"
    subtitle = "Repack RAR comics as ZIP so every reader opens them. Each result is verified."
    noun = ".cbr file"
    run_label = "Convert files"
    defaults = {"recursive": True, "original": MOVE, "exists": EXISTS[0]}
    choices = {"original": [MOVE, KEEP, DELETE], "exists": EXISTS}

    def __init__(self, parent):
        super().__init__(parent)
        v = self.vars
        ctk.CTkSwitch(self.form.add("Folders"), text="Include subfolders", variable=v["recursive"],
                      **switch_style()).pack(anchor="w")
        menu(self.form.add("After converting, the .cbr"), v["original"], [MOVE, KEEP, DELETE]).pack(fill="x")
        menu(self.form.add("If the .cbz already exists"), v["exists"], EXISTS).pack(fill="x")
        self.watch("recursive", callback=self.rescan)

    def scan(self, folder, o):
        it = folder.rglob("*") if o["recursive"] else folder.iterdir()
        files = [p for p in it if p.is_file() and p.suffix.lower() == ".cbr" and not in_archive(p, folder)]
        return sorted(files, key=lambda p: natural_key(p.relative_to(folder)))

    def label(self, item):
        return self.rel(item)

    def work(self, item, o, dry):
        dest = item.with_suffix(".cbz")
        if dest.exists():
            if o["exists"] == "Skip":
                return "skip", f"{self.rel(item)}  {dest.name} already exists"
            if o["exists"] == "Keep both":
                dest = unique(dest)
        if dry:
            return "ok", f"{self.rel(item)}  →  {dest.name}"
        pages = convert_to_cbz(item, dest)
        dispose_original(item, o["original"])
        return "ok", f"{self.rel(item)}  →  {dest.name}  ({pages} pages)"

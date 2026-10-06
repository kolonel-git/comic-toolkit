"""Clean-up page: remove junk files and normalise page names inside CBZ archives."""
import customtkinter as ctk

from archive_tools import BACKUP, KEEP_NAMES, REPLACE, SEQUENTIAL, apply_cleanup, describe_cleanup, plan_cleanup
from batch_page import BatchPage
from comic_core import in_archive, natural_key
from ui_kit import FONT, MUTED, entry, menu, switch_style


class CleanupPage(BatchPage):
    title = "Clean-up"
    subtitle = "Strip junk files and tidy page names inside your CBZ files."
    noun = ".cbz file"
    run_label = "Clean archives"
    defaults = {"recursive": True, "junk": True, "patterns": "", "names": SEQUENTIAL, "original": BACKUP}
    choices = {"names": [KEEP_NAMES, SEQUENTIAL], "original": [BACKUP, REPLACE]}

    def __init__(self, parent):
        super().__init__(parent)
        v = self.vars
        sw = switch_style()
        box = self.form.add("What to clean")
        ctk.CTkSwitch(box, text="Include subfolders", variable=v["recursive"], **sw).pack(anchor="w")
        ctk.CTkSwitch(box, text="Remove non-image files", variable=v["junk"], **sw).pack(anchor="w", pady=(8, 0))
        ctk.CTkLabel(box, text="Thumbs.db, .nfo, __MACOSX and the like. ComicInfo.xml is always kept.",
                     font=(FONT, 11), text_color=MUTED, anchor="w", justify="left",
                     wraplength=260).pack(fill="x", pady=(4, 0))
        row = self.form.add("Also remove files matching")
        entry(row, v["patterns"]).pack(fill="x")
        ctk.CTkLabel(row, text="Comma-separated, e.g. zzz*, *credits*", font=(FONT, 11), text_color=MUTED,
                     anchor="w").pack(fill="x", pady=(4, 0))
        names = self.form.add("Page names")
        menu(names, v["names"], [KEEP_NAMES, SEQUENTIAL]).pack(fill="x")
        ctk.CTkLabel(names, text="Sequential also flattens folders inside the archive.", font=(FONT, 11),
                     text_color=MUTED, anchor="w").pack(fill="x", pady=(4, 0))
        menu(self.form.add("Original file"), v["original"], [BACKUP, REPLACE]).pack(fill="x")
        self.watch("recursive", callback=self.rescan)

    def scan(self, folder, o):
        it = folder.rglob("*") if o["recursive"] else folder.iterdir()
        files = [p for p in it if p.is_file() and p.suffix.lower() == ".cbz" and not in_archive(p, folder)]
        return sorted(files, key=lambda p: natural_key(p.relative_to(folder)))

    def label(self, item):
        return self.rel(item)

    def work(self, item, o, dry):
        plan = plan_cleanup(item, o["junk"], o["patterns"], o["names"])
        if not plan["changed"]:
            return "skip", f"{self.rel(item)}  already clean"
        text = f"{self.rel(item)}  {describe_cleanup(plan)}"
        if not dry:
            apply_cleanup(item, plan, o["original"] == BACKUP)
        return "ok", text
